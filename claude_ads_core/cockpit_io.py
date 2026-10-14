"""Contained, bounded descriptor IO for the optional local cockpit.

Directory descriptors and no-follow opens prevent path-component substitution.
A persistent advisory lock is recoverable: the OS releases it on process exit.
No client body or system path is included in an error.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

MAX_BYTES = 8 * 1024 * 1024


class CockpitError(ValueError):
    """Safe public diagnostics for local cockpit operations."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def decode(data: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise CockpitError('JSON contains duplicate keys')
            result[key] = value
        return result
    def constant(_):
        raise CockpitError('JSON contains a nonfinite value')
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
        if not isinstance(value, dict):
            raise CockpitError('JSON document must be an object')
        return value
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise CockpitError('Invalid or oversized JSON structure') from exc


def require_safe_io():
    """Fail closed with one explicit diagnostic where descriptor IO is unavailable."""
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        raise CockpitError('Unsupported platform: safe descriptor IO needs POSIX with O_NOFOLLOW, so client runs cannot be processed on this host')


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class Directory:
    """One pinned root. Reads register exact bytes for final re-verification."""
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.reads: dict[str, tuple | None] = {}
        self.listings: dict[str, tuple[str, ...]] = {}
        self.lock_fds: set[int] = set()
        self.fd = -1
        require_safe_io()
        if '\x00' in str(self.root):
            raise CockpitError('Root contains an unsafe component')
        current = os.open(self.root.anchor, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in self.root.parts[1:]:
                if part in {'.', '..'}:
                    raise CockpitError('Root contains an unsafe component')
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
                os.close(current)
                current = nxt
            self.fd = current
        except (OSError, ValueError) as exc:
            os.close(current)
            # Every component is opened without following links, so a symlink in
            # any ancestor (for example /home -> var/home, or macOS /tmp) is
            # refused. This is deliberate; the caller supplies the real path.
            raise CockpitError('Root is missing or contains a symlink or unsafe component; pass the fully resolved path (for example from realpath)') from exc

    def __enter__(self):
        return self

    def __exit__(self, *args):
        os.close(self.fd)

    @contextmanager
    def parent(self, relative, *, create=False):
        parts = relative.split('/')
        if not parts or len(parts) > 18 or any(not p or p in {'.', '..'} or '\\' in p or ':' in p or '\x00' in p for p in parts):
            raise CockpitError('Unsafe relative path')
        current = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                if create:
                    try:
                        os.mkdir(part, mode=0o700, dir_fd=current)
                    except FileExistsError:
                        pass
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
                os.close(current)
                current = nxt
            yield current, parts[-1]
        except OSError as exc:
            raise CockpitError('Contained file operation failed or encountered an unsafe path') from exc
        finally:
            os.close(current)

    def _read(self, relative, *, missing=False):
        with self.parent(relative) as (parent, name):
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
            except FileNotFoundError:
                if missing:
                    return None, None
                raise CockpitError('Required registered file is missing')
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES or before.st_nlink != 1:
                    raise CockpitError('Registered file must be a bounded regular file with one link')
                data = bytearray()
                while len(data) <= MAX_BYTES:
                    chunk = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                after = os.fstat(fd)
                linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if len(data) > MAX_BYTES or _stamp(before) != _stamp(after) or _stamp(after) != _stamp(linked):
                    raise CockpitError('Registered file changed during read')
                return bytes(data), (_stamp(after), digest(data))
            finally:
                os.close(fd)

    def read(self, relative, *, missing=False):
        data, stamp = self._read(relative, missing=missing)
        self.reads[relative] = stamp
        return data

    def list_files(self, relative, *, limit=1000, record=True):
        """List only an explicitly designated directory through pinned descriptors."""
        parts = relative.split('/')
        if any(not p or p in {'.', '..'} or '\\' in p or ':' in p or '\x00' in p for p in parts):
            raise CockpitError('Unsafe history directory')
        current = os.dup(self.fd)
        try:
            for part in parts:
                try:
                    nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
                except FileNotFoundError:
                    names = ()
                    break
                os.close(current)
                current = nxt
            else:
                names = []
                with os.scandir(current) as entries:
                    for entry in entries:
                        if len(names) >= limit:
                            raise CockpitError('Generated history exceeds directory limit; archive older receipts and reports outside the run')
                        names.append(entry.name)
                names = tuple(sorted(names))
            if record:
                self.listings[relative] = names
            return names
        except OSError as exc:
            raise CockpitError('Generated history directory is unsafe or unavailable') from exc
        finally:
            os.close(current)

    def verify(self):
        # Reopening the absolute root also detects root rename/substitution.
        with Directory(self.root) as root:
            if _stamp(os.fstat(root.fd))[:2] != _stamp(os.fstat(self.fd))[:2]:
                raise CockpitError('Selected root changed during operation')
        for relative, expected in self.reads.items():
            _, actual = self._read(relative, missing=expected is None)
            if actual != expected:
                raise CockpitError('Registered state changed during operation; refresh and retry')
        for relative, expected in self.listings.items():
            if self.list_files(relative, record=False) != expected:
                raise CockpitError('Generated history changed during operation; refresh and retry')

    def write(self, relative, data, *, replace=False):
        if len(data) > MAX_BYTES:
            raise CockpitError('Generated artifact exceeds size limit')
        with self.parent(relative, create=True) as (parent, name):
            temporary = '.cockpit-tmp-' + uuid.uuid4().hex
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            try:
                with os.fdopen(fd, 'wb') as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                if replace:
                    try:
                        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                            raise CockpitError('Unsafe publication destination')
                    os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                else:
                    # Link commits only when the final name does not exist.
                    os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                os.fsync(parent)
            except FileExistsError as exc:
                raise CockpitError('Generated artifact already exists; refusing overwrite') from exc
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    # A successful replace consumed the temporary name.
                    pass

    @contextmanager
    def lock(self, *, exclusive=False):
        import fcntl
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        if exclusive:
            flags |= os.O_CREAT
        try:
            fd = os.open('.cockpit.lock', flags, 0o600, dir_fd=self.fd)
        except FileNotFoundError:
            yield
            return
        except OSError as exc:
            raise CockpitError('Action lock is unsafe or unavailable') from exc
        try:
            self.lock_fds.add(fd)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise CockpitError('Action lock must be a regular file')
            try:
                fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise CockpitError('Run is busy; refresh and retry after the current action') from exc
            yield
        finally:
            self.lock_fds.discard(fd)
            os.close(fd)
