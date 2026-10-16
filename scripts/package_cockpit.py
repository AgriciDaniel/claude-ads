#!/usr/bin/env python3
"""Build or verify the separately selected public Cockpit companion archive.

This helper does not install, load, enable, or package the Claude Ads core.
Archive input is a fixed file allowlist, never a recursive directory snapshot.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

NAME = "ads-cockpit"
VERSION = "0.1.0"
COMPANION_ROOT = "mods/claude-ads-cockpit"
RUNTIME_FILES = (
    ".claude-plugin/plugin.json",
    "LICENSE",
    "README.md",
    "hooks/band.mjs",
    "hooks/controller.mjs",
    "hooks/hooks.json",
    "hooks/kit.mjs",
    "hooks/launcher.mjs",
    "hooks/lexicon.mjs",
    "hooks/model.mjs",
    "hooks/pack.mjs",
    "hooks/register.mjs",
    "hooks/screens/chooser.mjs",
    "hooks/screens/compare.mjs",
    "hooks/screens/findings.mjs",
    "hooks/screens/inputs.mjs",
    "hooks/screens/overview.mjs",
    "hooks/screens/reports.mjs",
    "hooks/svg.mjs",
    "hooks/theme.mjs",
    "hooks/views.mjs",
    "hooks/wire.mjs",
    "types/index.d.ts",
)
MAX_FILE_BYTES = 2 * 1024 * 1024
DEFAULT_SOURCE_DATE_EPOCH = 315532800  # ZIP's earliest representable UTC date.
RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
            *(f"lpt{i}" for i in range(1, 10))}
PRIVATE_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])(?:/var)?/home/[A-Za-z0-9._-]+/"),
    re.compile(r"(?<![A-Za-z0-9])/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"(?i)\b[A-Z]:\\Users\\[A-Za-z0-9._-]+\\"),
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|(?:AKIA|ASIA)[A-Z0-9]{16})\b"),
    re.compile(r"(?i)(?<![A-Za-z0-9])~/(?:Desktop|Documents|Downloads|Dropbox|OneDrive|Pictures|Videos)/"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b(?:AIza[A-Za-z0-9_-]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,})\b"),
)


class PackageError(ValueError):
    """Bounded, path-free public packaging diagnostic."""


def _portable(relative: str) -> None:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise PackageError("unsafe archive path")
    parts = relative.split("/")
    if PurePosixPath(relative).is_absolute() or any(
        part in {"", ".", ".."} or part.endswith((" ", "."))
        or part.split(".", 1)[0].casefold() in RESERVED
        or re.search(r'[<>:"|?*\x00-\x1f\x7f]', part)
        for part in parts
    ):
        raise PackageError("unsafe archive path")


def _check_path(path: Path, *, directory: bool = False, missing: bool = False) -> None:
    """Reject link/reparse ancestors before any read or output creation."""
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise PackageError("required package path is missing") from None
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise PackageError("package path contains a symlink or reparse point")
        expected_directory = part != path or directory
        if expected_directory and not stat.S_ISDIR(info.st_mode):
            raise PackageError("package ancestor is not a directory")
        if not expected_directory and not stat.S_ISREG(info.st_mode):
            raise PackageError("package input is not a regular file")


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read(path: Path, *, max_bytes: int = MAX_FILE_BYTES) -> bytes:
    _check_path(path)
    before = path.lstat()
    if before.st_size > max_bytes:
        raise PackageError("package input exceeds the file size limit")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                         | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(before):
            raise PackageError("package input changed before reading")
        data = stream.read(max_bytes + 1)
        after = os.fstat(stream.fileno())
    _check_path(path)
    if len(data) > max_bytes or _identity(after) != _identity(before) \
            or _identity(path.lstat()) != _identity(before):
        raise PackageError("package input changed while reading")
    return data


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _epoch(value: int | None) -> int:
    if value is None:
        try:
            value = int(os.environ.get("SOURCE_DATE_EPOCH", DEFAULT_SOURCE_DATE_EPOCH))
        except ValueError:
            raise PackageError("SOURCE_DATE_EPOCH must be an integer") from None
    if isinstance(value, bool) or not isinstance(value, int) \
            or not DEFAULT_SOURCE_DATE_EPOCH <= value <= 4354819199:
        raise PackageError("source date must be within ZIP's 1980-2107 UTC range")
    return value - value % 2  # ZIP has two-second timestamp precision.


def _collect(root: Path) -> dict[str, bytes]:
    _check_path(root, directory=True)
    payload: dict[str, bytes] = {}
    if len({item.casefold() for item in RUNTIME_FILES}) != len(RUNTIME_FILES):
        raise PackageError("duplicate archive allowlist entry")
    for relative in sorted(RUNTIME_FILES):
        _portable(relative)
        data = _read(root / COMPANION_ROOT / relative)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise PackageError("package input is not UTF-8 text") from None
        if "\x00" in text or any(pattern.search(text) for pattern in PRIVATE_PATTERNS):
            raise PackageError("package input contains restricted material")
        payload[relative] = data
    try:
        plugin = json.loads(payload[".claude-plugin/plugin.json"])
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PackageError("invalid companion plugin manifest") from None
    if not isinstance(plugin, dict) or plugin.get("name") != NAME \
            or plugin.get("version") != VERSION or plugin.get("license") != "MIT":
        raise PackageError("companion manifest identity or license mismatch")
    if plugin.get("types") != "./types/index.d.ts":
        raise PackageError("companion manifest type entry is outside the curated surface")
    try:
        hooks = json.loads(payload["hooks/hooks.json"])
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PackageError("invalid companion hooks manifest") from None
    if not isinstance(hooks, dict) or hooks.get("modules") != ["./register.mjs"]:
        raise PackageError("companion hook entry is outside the curated surface")
    if payload["LICENSE"] != _read(root / "LICENSE"):
        raise PackageError("companion license must match the reviewed root license")
    return payload


def _artifacts(root: Path, source_date_epoch: int) -> dict[str, bytes]:
    payload = _collect(root)
    timestamp = datetime.fromtimestamp(source_date_epoch, timezone.utc).timetuple()[:6]
    buffer = io.BytesIO()
    # Stored entries avoid zlib-version drift across machines. These text files
    # are small; reproducibility is more useful here than compression savings.
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for relative, data in sorted(payload.items()):
            info = zipfile.ZipInfo(f"{NAME}/{relative}", timestamp)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data)
    archive_name = f"{NAME}-{VERSION}.zip"
    manifest_name = f"{NAME}-{VERSION}.manifest.json"
    manifest = _json({
        "schema_version": "1.0.0", "artifact_type": "cockpit-companion-package",
        "name": NAME, "version": VERSION, "core_required": True,
        "source_date_epoch": source_date_epoch,
        "archive": {"path": archive_name, "sha256": _sha(buffer.getvalue())},
        "files": [{"path": f"{NAME}/{relative}", "sha256": _sha(data),
                   "size": len(data), "mode": "0644"}
                  for relative, data in sorted(payload.items())],
    })
    outputs = {archive_name: buffer.getvalue(), manifest_name: manifest}
    outputs[f"{NAME}-{VERSION}.sha256"] = "".join(
        f"{_sha(data)}  {filename}\n" for filename, data in sorted(outputs.items())
    ).encode()
    return outputs


def build_companion(root: Path, output_dir: Path, *, source_date_epoch: int | None = None
                    ) -> dict[str, Path]:
    """Capture only allowed public source bytes and create new output files."""
    outputs = _artifacts(Path(root).absolute(), _epoch(source_date_epoch))
    output_dir = Path(output_dir).absolute()
    _check_path(output_dir, directory=True, missing=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    _check_path(output_dir, directory=True)
    if any((output_dir / name).exists() or (output_dir / name).is_symlink()
           for name in outputs):
        raise PackageError("package output already exists; choose a fresh output directory")
    created: list[Path] = []
    try:
        for name, data in outputs.items():
            destination = output_dir / name
            with destination.open("xb") as stream:
                created.append(destination)
                stream.write(data)
    except BaseException:
        for path in created:
            path.unlink()
        raise
    return {name: output_dir / name for name in outputs}


def verify_companion(root: Path, output_dir: Path) -> None:
    """Bind package bytes to this exact curated source, not self-reported hashes."""
    output_dir = Path(output_dir).absolute()
    manifest = _read(output_dir / f"{NAME}-{VERSION}.manifest.json")
    try:
        epoch = json.loads(manifest)["source_date_epoch"]
    except (ValueError, KeyError, TypeError):
        raise PackageError("invalid companion package metadata") from None
    expected = _artifacts(Path(root).absolute(), _epoch(epoch))
    for name, data in expected.items():
        if _read(output_dir / name, max_bytes=MAX_FILE_BYTES * (len(RUNTIME_FILES) + 1)) != data:
            raise PackageError("companion package differs from curated source bytes")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("command", choices=("package", "verify"))
    args = parser.parse_args(argv)
    try:
        if args.command == "package":
            outputs = build_companion(args.root, args.output_dir)
            verify_companion(args.root, args.output_dir)
            for name in outputs:
                print(name)
        else:
            verify_companion(args.root, args.output_dir)
            print("companion package verified against curated source")
    except (OSError, ValueError) as exc:
        diagnostic = str(exc) if isinstance(exc, PackageError) else "filesystem operation failed"
        print(f"companion package error: {diagnostic}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
