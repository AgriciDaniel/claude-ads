#!/usr/bin/env python3
"""Generate ad creative images through an explicitly selected API adapter.

This local CLI is a fallback for environments whose approved image capability is
not exposed through a host-native tool. It has no default provider or model.
Select both from current capability evidence for every run.

Implemented adapters are Gemini, OpenAI, Stability AI, Replicate, and MuAPI. Adapter
availability does not imply operator approval, account access, model availability,
or fitness for a placement.

Usage:
    python generate_image.py "prompt text" --provider "$ADS_IMAGE_PROVIDER" --model "$ADS_IMAGE_MODEL" --ratio 9:16 --output ad.png
    python generate_image.py --batch prompts.json --provider "$ADS_IMAGE_PROVIDER" --model "$ADS_IMAGE_MODEL" --output-dir ./ad-assets/

Environment variables:
    ADS_IMAGE_PROVIDER   Required unless --provider is supplied
    ADS_IMAGE_MODEL      Required unless --model is supplied
    GOOGLE_API_KEY       Required for gemini provider
    OPENAI_API_KEY       Required for openai provider
    STABILITY_API_KEY    Required for stability provider
    REPLICATE_API_TOKEN  Required for replicate provider
    MUAPI_API_KEY        Required for muapi provider

See ads/references/image-providers.md for pricing and capability details.
"""

import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
import os
import re
import secrets
import stat
import struct
import sys
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote, urlparse

from claude_ads_core.contracts import ContractError, load_contract, validate_contract
# Single source of truth for credential redaction (see scripts/url_utils.py).
# Re-exported under the local _sanitize_error name so existing call sites do
# not need to change.
from url_utils import artifact_locator, guarded_request, resolve_output_path, sanitize_error as _sanitize_error

# Aspect ratio shorthand → (width, height)
ASPECT_RATIOS = {
    "1:1":   (1080, 1080),
    "9:16":  (1080, 1920),
    "16:9":  (1920, 1080),
    "4:5":   (1080, 1350),
    "4:3":   (1200, 900),
    "3:4":   (900, 1200),
    "1.91:1": (1200, 628),  # Google PMax / LinkedIn landscape
    "4:1":   (1200, 300),   # Google Logo landscape
    "21:9":  (2520, 1080),  # Ultra-wide
}

# Gemini API ratio strings (closest supported ratio for each alias)
GEMINI_RATIO_MAP = {
    "1:1":    "1:1",
    "9:16":   "9:16",
    "16:9":   "16:9",
    "4:5":    "4:5",
    "4:3":    "4:3",
    "3:4":    "3:4",
    "1.91:1": "16:9",  # Closest Gemini supports; crop in post if needed
    "4:1":    "4:1",
    "21:9":   "21:9",
}

MAX_RETRIES = 4
RETRY_BACKOFF = [1, 2, 4, 8]  # seconds

MAX_BATCH_SIZE = 50
MAX_DIMENSION = 8192
MUAPI_API_BASE = "https://api.muapi.ai"
MUAPI_MAX_POLLS = 60
MUAPI_POLL_INTERVAL = 2


def _windows_acl_api():
    """Return Win32 ACL libraries with pointer-safe ctypes signatures."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    void_pp = ctypes.POINTER(ctypes.c_void_p)
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    advapi32.OpenProcessToken.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)
    ]
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetTokenInformation.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.GetTokenInformation.restype = wintypes.BOOL
    advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, void_pp, ctypes.POINTER(wintypes.DWORD)
    ]
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    advapi32.GetSecurityDescriptorDacl.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL), void_pp,
        ctypes.POINTER(wintypes.BOOL),
    ]
    advapi32.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    advapi32.SetSecurityInfo.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.DWORD, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ]
    advapi32.SetSecurityInfo.restype = wintypes.DWORD
    advapi32.GetSecurityInfo.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.DWORD, void_pp, void_pp,
        void_pp, void_pp, void_pp,
    ]
    advapi32.GetSecurityInfo.restype = wintypes.DWORD
    advapi32.GetSecurityDescriptorControl.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)
    ]
    advapi32.GetSecurityDescriptorControl.restype = wintypes.BOOL
    advapi32.GetAclInformation.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.c_int
    ]
    advapi32.GetAclInformation.restype = wintypes.BOOL
    advapi32.GetAce.argtypes = [ctypes.c_void_p, wintypes.DWORD, void_pp]
    advapi32.GetAce.restype = wintypes.BOOL
    kernel32.ReOpenFile.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD
    ]
    kernel32.ReOpenFile.restype = wintypes.HANDLE
    return ctypes, wintypes, kernel32, advapi32


def _windows_current_user_sid() -> str:
    ctypes, wintypes, kernel32, advapi32 = _windows_acl_api()

    class _SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

    class _TOKEN_USER(ctypes.Structure):
        _fields_ = [("User", _SID_AND_ATTRIBUTES)]

    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        required = wintypes.DWORD()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
        if required.value == 0:
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_string_buffer(required.value)
        if not advapi32.GetTokenInformation(
            token, 1, buffer, required.value, ctypes.byref(required)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        sid = ctypes.cast(buffer, ctypes.POINTER(_TOKEN_USER)).contents.User.Sid
        string_sid = wintypes.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(sid, ctypes.byref(string_sid)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return string_sid.value
        finally:
            kernel32.LocalFree(ctypes.cast(string_sid, ctypes.c_void_p))
    finally:
        kernel32.CloseHandle(token)


def _windows_sid_string(sid: int) -> str:
    ctypes, wintypes, kernel32, advapi32 = _windows_acl_api()
    string_sid = wintypes.LPWSTR()
    if not advapi32.ConvertSidToStringSidW(ctypes.c_void_p(sid), ctypes.byref(string_sid)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return string_sid.value
    finally:
        kernel32.LocalFree(ctypes.cast(string_sid, ctypes.c_void_p))


def _windows_handle_has_owner_only_acl(handle: int) -> bool:
    ctypes, wintypes, kernel32, advapi32 = _windows_acl_api()

    class _ACL_SIZE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("AceCount", wintypes.DWORD),
            ("AclBytesInUse", wintypes.DWORD),
            ("AclBytesFree", wintypes.DWORD),
        ]

    descriptor = ctypes.c_void_p()
    dacl = ctypes.c_void_p()
    owner = ctypes.c_void_p()
    result = advapi32.GetSecurityInfo(
        wintypes.HANDLE(handle), 1, 0x00000005, ctypes.byref(owner), None,
        ctypes.byref(dacl), None, ctypes.byref(descriptor),
    )
    if result:
        raise ctypes.WinError(result)
    try:
        control = wintypes.WORD()
        revision = wintypes.DWORD()
        if not advapi32.GetSecurityDescriptorControl(
            descriptor, ctypes.byref(control), ctypes.byref(revision)
        ) or not (control.value & 0x1000):
            return False
        info = _ACL_SIZE_INFORMATION()
        if not advapi32.GetAclInformation(
            dacl, ctypes.byref(info), ctypes.sizeof(info), 2
        ) or info.AceCount != 1:
            return False
        ace = ctypes.c_void_p()
        if not advapi32.GetAce(dacl, 0, ctypes.byref(ace)):
            return False
        address = ace.value
        ace_type = ctypes.c_ubyte.from_address(address).value
        ace_flags = ctypes.c_ubyte.from_address(address + 1).value
        mask = wintypes.DWORD.from_address(address + 4).value
        trustee = _windows_sid_string(address + 8)
        owner_sid = _windows_sid_string(owner.value)
        current_sid = _windows_current_user_sid()
        return (
            ace_type == 0
            and ace_flags == 0
            and mask == 0x001F01FF
            and trustee == current_sid
            and owner_sid == current_sid
        )
    finally:
        kernel32.LocalFree(descriptor)


def _windows_file_identity(handle: int) -> tuple[int, bytes]:
    """Return FileIdInfo identity, including the 128-bit ReFS-safe file ID."""
    ctypes, wintypes, kernel32, _ = _windows_acl_api()

    class _FILE_ID_128(ctypes.Structure):
        _fields_ = [("Identifier", ctypes.c_ubyte * 16)]

    class _FILE_ID_INFO(ctypes.Structure):
        _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong), ("FileId", _FILE_ID_128)]

    kernel32.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
    ]
    kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    info = _FILE_ID_INFO()
    if not kernel32.GetFileInformationByHandleEx(
        wintypes.HANDLE(handle), 18, ctypes.byref(info), ctypes.sizeof(info)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return info.VolumeSerialNumber, bytes(info.FileId.Identifier)


def _windows_open_path_guard(path: Path, anchor: int) -> int:
    """Open and verify the current path without delete sharing, then hold it."""
    ctypes, wintypes, kernel32, _ = _windows_acl_api()
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    guard = kernel32.CreateFileW(
        str(path),
        0x80020000,  # GENERIC_READ|READ_CONTROL: participate in share enforcement.
        0x00000001,  # FILE_SHARE_READ only; deny write/truncate/delete/swap.
        None,
        3,  # OPEN_EXISTING
        0x00000080,  # FILE_ATTRIBUTE_NORMAL
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if guard == invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if _windows_file_identity(guard) != _windows_file_identity(anchor):
            raise PermissionError("Private file path no longer identifies the created object")
        if not _windows_handle_has_owner_only_acl(guard):
            raise PermissionError("Private file path has an invalid owner or DACL")
        return guard
    except Exception:
        kernel32.CloseHandle(guard)
        raise


def _windows_delete_by_anchor(anchor: int) -> None:
    """Mark the exact anchored object for deletion without consulting its path."""
    ctypes, wintypes, kernel32, _ = _windows_acl_api()

    class _FILE_DISPOSITION_INFO(ctypes.Structure):
        _fields_ = [("DeleteFile", ctypes.c_ubyte)]  # Win32 BOOLEAN, exactly 1 byte.

    kernel32.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
    ]
    kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
    invalid_handle = ctypes.c_void_p(-1).value
    deletion_handle = kernel32.ReOpenFile(
        wintypes.HANDLE(anchor),
        0x00010000,  # DELETE
        0x00000007,
        0,
    )
    if deletion_handle == invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        disposition = _FILE_DISPOSITION_INFO(True)
        if not kernel32.SetFileInformationByHandle(
            deletion_handle, 4, ctypes.byref(disposition), ctypes.sizeof(disposition)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(deletion_handle)


def _windows_create_private_temp(
    directory: Path, prefix: str, suffix: str, *, temporary: bool
) -> tuple[int, Path, int]:
    """Atomically create a private temp file and return fd, path, anchored ACL handle."""
    import msvcrt

    ctypes, wintypes, kernel32, advapi32 = _windows_acl_api()

    class _SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", wintypes.BOOL),
        ]

    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(_SECURITY_ATTRIBUTES), wintypes.DWORD, wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    security_descriptor = ctypes.c_void_p()
    current_sid = _windows_current_user_sid()
    sddl = f"O:{current_sid}D:P(A;;FA;;;{current_sid})"
    if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, 1, ctypes.byref(security_descriptor), None
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    file_handle = None
    acl_handle = None
    path = None
    returned = False
    try:
        present = wintypes.BOOL()
        defaulted = wintypes.BOOL()
        dacl = ctypes.c_void_p()
        if not advapi32.GetSecurityDescriptorDacl(
            security_descriptor, ctypes.byref(present), ctypes.byref(dacl),
            ctypes.byref(defaulted),
        ) or not present:
            raise ctypes.WinError(ctypes.get_last_error())
        attributes = _SECURITY_ATTRIBUTES(
            ctypes.sizeof(_SECURITY_ATTRIBUTES), security_descriptor, False
        )
        invalid_handle = ctypes.c_void_p(-1).value
        for _ in range(128):
            candidate = directory / f"{prefix}{secrets.token_hex(16)}{suffix}"
            file_handle = kernel32.CreateFileW(
                str(candidate),
                0xC0060000,  # GENERIC_READ|GENERIC_WRITE|READ_CONTROL|WRITE_DAC
                0x00000007,  # FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE
                ctypes.byref(attributes),
                1,  # CREATE_NEW
                0x00000100 if temporary else 0x00000080,
                None,
            )
            if file_handle != invalid_handle:
                path = candidate
                break
            error = ctypes.get_last_error()
            if error not in {80, 183}:  # ERROR_FILE_EXISTS / ERROR_ALREADY_EXISTS
                raise ctypes.WinError(error)
        if path is None or file_handle == invalid_handle:
            raise FileExistsError("Could not allocate a unique private temporary file")
        acl_handle = kernel32.ReOpenFile(
            file_handle,
            0x00060000,  # READ_CONTROL|WRITE_DAC
            0x00000007,
            0,
        )
        if acl_handle == invalid_handle:
            raise ctypes.WinError(ctypes.get_last_error())
        result = advapi32.SetSecurityInfo(
            acl_handle, 1, 0x80000004, None, None, dacl, None
        )
        if result:
            raise ctypes.WinError(result)
        if not _windows_handle_has_owner_only_acl(acl_handle):
            raise PermissionError(f"Owner-only Windows ACL verification failed for {path.name}")
        descriptor = msvcrt.open_osfhandle(
            file_handle, os.O_RDWR | getattr(os, "O_BINARY", 0)
        )
        file_handle = None  # The CRT descriptor now owns the original handle.
        returned = True
        return descriptor, path, acl_handle
    finally:
        if not returned:
            cleanup_anchor = acl_handle if acl_handle not in {None, ctypes.c_void_p(-1).value} else file_handle
            if cleanup_anchor not in {None, ctypes.c_void_p(-1).value}:
                try:
                    _windows_delete_by_anchor(cleanup_anchor)
                except OSError:
                    pass
        if file_handle not in {None, ctypes.c_void_p(-1).value}:
            kernel32.CloseHandle(file_handle)
        if not returned and acl_handle not in {None, ctypes.c_void_p(-1).value}:
            kernel32.CloseHandle(acl_handle)
        kernel32.LocalFree(security_descriptor)


def _close_windows_handle(handle: int | None) -> None:
    if handle is None:
        return
    _, wintypes, kernel32, _ = _windows_acl_api()
    if not kernel32.CloseHandle(wintypes.HANDLE(handle)):
        raise OSError("Could not close the Windows ACL anchor handle")


def _windows_path_has_owner_only_acl(path: Path) -> bool:
    if os.name != "nt":
        return False
    ctypes, wintypes, kernel32, _ = _windows_acl_api()
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    handle = kernel32.CreateFileW(
        str(path),
        0x00020000,  # READ_CONTROL
        0x00000007,
        None,
        3,  # OPEN_EXISTING
        0x00000080,  # FILE_ATTRIBUTE_NORMAL
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle == invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return _windows_handle_has_owner_only_acl(handle)
    finally:
        kernel32.CloseHandle(handle)


def _set_private_permissions(path: Path, descriptor: int | None = None) -> None:
    """Apply and verify owner-only permissions on the current platform."""
    if os.name == "nt":
        raise RuntimeError("Windows private files must use atomic CreateFileW creation")
    elif descriptor is not None and hasattr(os, "fchmod"):
        os.fchmod(descriptor, 0o600)
    else:
        os.chmod(path, 0o600)


def _path_has_private_permissions(path: Path) -> bool:
    if os.name == "nt":
        return _windows_path_has_owner_only_acl(path)
    return stat.S_IMODE(path.stat().st_mode) == 0o600


MAX_REFERENCE_IMAGE_BYTES = 20 * 1024 * 1024
MAX_REFERENCE_DECODED_BYTES = 128 * 1024 * 1024
_ALLOWED_IMAGE_EXTENSIONS = {'.png'}
_WINDOWS_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
    "com¹", "com²", "com³", "lpt¹", "lpt²", "lpt³",
}

_PROMPT_SUMMARY = "[redacted: raw prompt is ephemeral and is not persisted]"


def _prompt_record(prompt: str) -> dict[str, str]:
    """Return the irreversible prompt identity allowed in shipped JSON."""
    return {
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_summary": _PROMPT_SUMMARY,
    }


def _reference_input_root(input_root: str | None) -> Path:
    """Return the explicit, canonical operator boundary for reference images."""
    configured = input_root or os.environ.get("CLAUDE_ADS_INPUT_ROOT")
    if not configured:
        raise ValueError(
            "Reference images require --input-root or CLAUDE_ADS_INPUT_ROOT"
        )
    candidate = Path(configured).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError("Reference-image input root does not exist") from exc
    if not resolved.is_dir():
        raise ValueError("Reference-image input root must be a directory")
    return resolved


def _resolve_reference_source(reference: Any, input_root: Path) -> Path:
    """Resolve one untrusted batch reference beneath an explicit local root.

    Batch documents are data, not authority to read arbitrary workstation files.
    Reference paths are therefore portable relative paths, may not traverse or use
    symlinks, and must resolve to a bounded regular image file.
    """
    if not isinstance(reference, str) or not reference or "\x00" in reference:
        raise ValueError("Reference image must be a non-empty relative path")
    if reference != reference.strip():
        raise ValueError("Reference image path may not have surrounding whitespace")
    value = reference
    if (
        Path(value).is_absolute()
        or value.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:", value)
        or "\\" in value
    ):
        raise ValueError("Reference image must be relative to the configured input root")
    parts = Path(value).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Reference image path traversal is forbidden")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("Reference image path contains a control character")
    for part in parts:
        if re.search(r'[<>:"|?*]', part):
            raise ValueError("Reference image path is not portable")
        if part.endswith((" ", ".")):
            raise ValueError("Reference image path has a trailing space or dot")
        if part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_NAMES:
            raise ValueError("Reference image path uses a Windows-reserved name")
    if Path(value).suffix.lower() not in _ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Unsupported reference image format")

    lexical = input_root.joinpath(*parts)
    current = input_root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlinked reference images and parent paths are forbidden")
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(input_root)
    except (OSError, ValueError) as exc:
        raise ValueError("Reference image escapes the configured input root") from exc
    if not resolved.is_file():
        raise ValueError("Reference image must be a regular file")
    return resolved, parts


def _assert_descriptor_beneath_root(
    descriptor: int, input_root: Path, expected_path: Path
) -> None:
    """Bind the opened handle—not merely its pre-open pathname—to the input root."""
    if os.name == "nt":  # pragma: no cover - exercised by the native Windows matrix
        import ctypes
        import msvcrt

        handle = msvcrt.get_osfhandle(descriptor)
        buffer = ctypes.create_unicode_buffer(32768)
        get_final_path = ctypes.WinDLL("kernel32", use_last_error=True).GetFinalPathNameByHandleW
        get_final_path.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        get_final_path.restype = ctypes.c_uint32
        length = get_final_path(
            ctypes.c_void_p(handle), buffer, len(buffer), 0
        )
        if not length or length >= len(buffer):
            raise ValueError("Cannot verify the opened reference-image handle")
        final_name = buffer.value
        if final_name.startswith("\\\\?\\UNC\\"):
            final_name = "\\\\" + final_name[8:]
        elif final_name.startswith("\\\\?\\"):
            final_name = final_name[4:]
        final_path = Path(final_name).resolve(strict=True)
        try:
            final_path.relative_to(input_root)
        except ValueError as exc:
            raise ValueError("Opened reference image escapes the configured input root") from exc
        return

    proc_descriptor = Path(f"/proc/self/fd/{descriptor}")
    if proc_descriptor.exists():
        try:
            proc_descriptor.resolve(strict=True).relative_to(input_root)
        except (OSError, ValueError) as exc:
            raise ValueError("Opened reference image escapes the configured input root") from exc
        return

    if sys.platform == "darwin":  # pragma: no cover - exercised by native macOS CI
        import fcntl

        try:
            raw_path = fcntl.fcntl(descriptor, 50, b"\x00" * 1024)  # F_GETPATH
            final_path = Path(raw_path.split(b"\x00", 1)[0].decode()).resolve(strict=True)
            final_path.relative_to(input_root)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError("Opened reference image escapes the configured input root") from exc
        return

    raise ValueError("This platform cannot attest the opened reference-image path")


def _open_reference_beneath(
    input_root: Path, parts: tuple[str, ...], resolved: Path
) -> int:
    """Open a relative file through anchored directory descriptors when supported."""
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    cloexec = getattr(os, "O_CLOEXEC", 0)
    nonblock = getattr(os, "O_NONBLOCK", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if os.open in os.supports_dir_fd and directory and nofollow:
        root_descriptor = os.open(input_root, os.O_RDONLY | directory | nofollow | cloexec)
        current_descriptor = root_descriptor
        opened_directories: list[int] = []
        try:
            for part in parts[:-1]:
                next_descriptor = os.open(
                    part,
                    os.O_RDONLY | directory | nofollow | cloexec,
                    dir_fd=current_descriptor,
                )
                opened_directories.append(next_descriptor)
                current_descriptor = next_descriptor
            descriptor = os.open(
                parts[-1],
                os.O_RDONLY | nofollow | cloexec | nonblock,
                dir_fd=current_descriptor,
            )
            try:
                _assert_descriptor_beneath_root(descriptor, input_root, resolved)
            except Exception:
                os.close(descriptor)
                raise
            return descriptor
        finally:
            for opened in reversed(opened_directories):
                os.close(opened)
            os.close(root_descriptor)

    descriptor = os.open(resolved, os.O_RDONLY | nofollow | cloexec | nonblock)
    try:
        _assert_descriptor_beneath_root(descriptor, input_root, resolved)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _validate_reference_payload(payload: bytes, suffix: str) -> None:
    """Validate a bounded, decodable PNG raster—not only a spoofable prefix."""
    if suffix != ".png" or not _validate_png(payload):
        raise ValueError("Reference image bytes do not form a valid supported PNG")


def _validate_png(payload: bytes) -> bool:
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    position = 8
    seen_ihdr = seen_idat = seen_iend = False
    idat_finished = False
    compressed = bytearray()
    width = height = bit_depth = color_type = interlace = 0
    while position + 12 <= len(payload):
        length = struct.unpack(">I", payload[position:position + 4])[0]
        chunk_type = payload[position + 4:position + 8]
        if not re.fullmatch(rb"[A-Za-z]{4}", chunk_type) or not chunk_type[2:3].isupper():
            return False
        data_start = position + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(payload):
            return False
        expected_crc = struct.unpack(">I", payload[data_end:crc_end])[0]
        if zlib.crc32(chunk_type + payload[data_start:data_end]) & 0xFFFFFFFF != expected_crc:
            return False
        if not seen_ihdr:
            if chunk_type != b"IHDR" or length != 13:
                return False
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", payload[data_start:data_end]
            )
            if not (1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION):
                return False
            if (
                bit_depth != 8
                or color_type not in {0, 2, 4, 6}
                or compression != 0
                or filter_method != 0
                or interlace != 0
            ):
                return False
            seen_ihdr = True
        elif chunk_type == b"IHDR":
            return False
        if chunk_type == b"PLTE":
            return False
        if chunk_type == b"IDAT":
            if idat_finished:
                return False
            seen_idat = True
            compressed.extend(payload[data_start:data_end])
        elif seen_idat and chunk_type != b"IEND":
            idat_finished = True
        if chunk_type not in {b"IHDR", b"PLTE", b"IDAT", b"IEND"} and chunk_type[:1].isupper():
            return False
        if chunk_type == b"IEND":
            if length != 0 or not seen_idat:
                return False
            seen_iend = True
            position = crc_end
            break
        position = crc_end
    if not (seen_ihdr and seen_idat and seen_iend and position == len(payload)):
        return False

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    bits_per_pixel = channels * bit_depth

    row_size = 1 + (width * bits_per_pixel + 7) // 8
    expected_size = height * row_size
    row_sizes = [row_size] * height
    if expected_size > MAX_REFERENCE_DECODED_BYTES or not compressed:
        return False
    try:
        decompressor = zlib.decompressobj()
        decoded = decompressor.decompress(bytes(compressed), expected_size + 1)
    except zlib.error:
        return False
    if (
        len(decoded) != expected_size
        or not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
    ):
        return False
    offset = 0
    for row_size in row_sizes:
        if offset >= len(decoded) or decoded[offset] > 4:
            return False
        offset += row_size
    return offset == len(decoded)


@contextmanager
def _private_reference_snapshot(reference: Any, input_root: Path):
    """Yield an immutable private snapshot of a validated reference image."""
    if reference is None:
        yield None, None
        return
    source, parts = _resolve_reference_source(reference, input_root)
    descriptor = _open_reference_beneath(input_root, parts, source)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("Reference image must be a regular file")
        if metadata.st_size > MAX_REFERENCE_IMAGE_BYTES:
            raise ValueError("Reference image exceeds the 20 MiB limit")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            payload = stream.read(MAX_REFERENCE_IMAGE_BYTES + 1)
        if len(payload) > MAX_REFERENCE_IMAGE_BYTES:
            raise ValueError("Reference image exceeds the 20 MiB limit")
        _validate_reference_payload(payload, source.suffix.lower())
    finally:
        os.close(descriptor)

    snapshot_acl_handle = None
    snapshot_path_guard = None
    if os.name == "nt":
        snapshot_descriptor, snapshot, snapshot_acl_handle = _windows_create_private_temp(
            Path(tempfile.gettempdir()),
            ".claude-ads-reference-",
            source.suffix.lower(),
            temporary=True,
        )
    else:
        snapshot_descriptor, snapshot_name = tempfile.mkstemp(
            prefix=".claude-ads-reference-", suffix=source.suffix.lower()
        )
        snapshot = Path(snapshot_name)
    try:
        if os.name != "nt":
            try:
                _set_private_permissions(snapshot, snapshot_descriptor)
            except Exception:
                os.close(snapshot_descriptor)
                raise
        with os.fdopen(snapshot_descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if snapshot_acl_handle is not None:
            snapshot_path_guard = _windows_open_path_guard(
                snapshot, snapshot_acl_handle
            )
        yield str(snapshot), hashlib.sha256(payload).hexdigest()
    finally:
        if os.name == "nt":
            try:
                _close_windows_handle(snapshot_path_guard)
            finally:
                try:
                    if snapshot_acl_handle is not None:
                        _windows_delete_by_anchor(snapshot_acl_handle)
                finally:
                    _close_windows_handle(snapshot_acl_handle)
        else:
            snapshot.unlink(missing_ok=True)


def _write_private(path: Path, data: bytes) -> None:
    """Atomically write a generated asset with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    acl_handle = None
    path_guard = None
    keep_output = False
    if os.name == "nt":
        descriptor, temporary, acl_handle = _windows_create_private_temp(
            path.parent, f".{path.name}.", ".tmp", temporary=False
        )
    else:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
    try:
        if os.name != "nt":
            try:
                _set_private_permissions(temporary, descriptor)
            except Exception:
                os.close(descriptor)
                raise
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if acl_handle is not None:
            path_guard = _windows_open_path_guard(path, acl_handle)
        else:
            _set_private_permissions(path)
        keep_output = True
    finally:
        if os.name == "nt":
            try:
                _close_windows_handle(path_guard)
            finally:
                try:
                    if acl_handle is not None and not keep_output:
                        _windows_delete_by_anchor(acl_handle)
                finally:
                    _close_windows_handle(acl_handle)
        else:
            temporary.unlink(missing_ok=True)


def _actual_dimensions(image_bytes: bytes) -> tuple[int, int] | None:
    """
    Extract actual width/height from PNG or JPEG header without PIL.
    Returns (width, height) or None if format is unrecognised.
    """
    if len(image_bytes) < 24:
        return None
    # PNG: 8-byte signature + 4-byte IHDR length + 4-byte "IHDR" + 4-byte W + 4-byte H
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        w = struct.unpack('>I', image_bytes[16:20])[0]
        h = struct.unpack('>I', image_bytes[20:24])[0]
        return w, h
    # JPEG: scan for SOF0 (0xFF 0xC0) or SOF2 (0xFF 0xC2) marker
    i = 2  # skip FF D8 SOI
    while i < len(image_bytes) - 8:
        if image_bytes[i] != 0xFF:
            break
        marker = image_bytes[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):  # SOFn markers
            h = struct.unpack('>H', image_bytes[i + 5:i + 7])[0]
            w = struct.unpack('>H', image_bytes[i + 7:i + 9])[0]
            return w, h
        seg_len = struct.unpack('>H', image_bytes[i + 2:i + 4])[0]
        i += 2 + seg_len
    return None


def _get_api_key(provider: str) -> str:
    """Retrieve API key for the given provider from environment."""
    key_map = {
        "gemini":    ("GOOGLE_API_KEY",      "console.cloud.google.com/apis/credentials"),
        "openai":    ("OPENAI_API_KEY",       "platform.openai.com/api-keys"),
        "stability": ("STABILITY_API_KEY",    "platform.stability.ai"),
        "replicate": ("REPLICATE_API_TOKEN",  "replicate.com/account/api-tokens"),
        "muapi":     ("MUAPI_API_KEY",         "muapi.ai/access-keys"),
    }

    if provider not in key_map:
        print(
            f"Error: Unknown provider '{provider}'. Valid options: gemini, openai, stability, replicate, muapi",
            file=sys.stderr,
        )
        sys.exit(1)

    env_var, url = key_map[provider]
    key = os.environ.get(env_var)

    if not key:
        print(
            f"Error: {env_var} not set.\n"
            f"To use the {provider} provider:\n"
            f"  export {env_var}=\"your-key\"\n"
            f"  Get a key at: {url}\n"
            f"\nTo use a different approved capability, set both "
            f"ADS_IMAGE_PROVIDER and ADS_IMAGE_MODEL explicitly.",
            file=sys.stderr,
        )
        sys.exit(1)

    return key


def _dims_from_ratio(ratio: str) -> tuple[int, int]:
    """Return (width, height) for a ratio string."""
    if ratio in ASPECT_RATIOS:
        return ASPECT_RATIOS[ratio]
    # Try parsing WxH directly (e.g. "1200x628")
    if "x" in ratio:
        try:
            w, h = int(ratio.lower().split("x")[0]), int(ratio.lower().split("x")[1])
            if w < 1 or h < 1 or w > MAX_DIMENSION or h > MAX_DIMENSION:
                print(f"Error: Dimensions must be 1-{MAX_DIMENSION}. Got {w}x{h}", file=sys.stderr)
                sys.exit(1)
            return w, h
        except (ValueError, IndexError):
            pass
    print(f"Error: Unknown ratio '{ratio}'. Use one of: {', '.join(ASPECT_RATIOS.keys())} or WxH (e.g. 1200x628)", file=sys.stderr)
    sys.exit(1)


def generate_gemini(prompt: str, width: int, height: int, api_key: str, model: str, reference_image_path: str | None = None) -> bytes:
    """Generate image using Gemini API (google-genai package).

    Args:
        reference_image_path: Optional path to a brand screenshot for style-guided
            generation. When provided, the image is passed as a visual style reference
            alongside the text prompt when the explicitly selected model supports it.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print(
            "Error: google-genai package required.\n"
            "Install with: pip install google-genai>=1.16.0",
            file=sys.stderr,
        )
        sys.exit(1)

    # Determine closest Gemini aspect ratio
    ratio_key = None
    for k, (w, h) in ASPECT_RATIOS.items():
        if w == width and h == height:
            ratio_key = k
            break
    gemini_ratio = GEMINI_RATIO_MAP.get(ratio_key, "1:1") if ratio_key else "1:1"

    client = genai.Client(api_key=api_key)

    # Build contents, with optional brand reference image for style guidance
    if reference_image_path and os.path.exists(reference_image_path):
        if Path(reference_image_path).suffix.lower() not in _ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported reference image format: {Path(reference_image_path).suffix}")
        with open(reference_image_path, 'rb') as f:
            ref_bytes = f.read()
        mime = {
            ".png": "image/png",
        }[Path(reference_image_path).suffix.lower()]
        ref_part = types.Part.from_bytes(data=ref_bytes, mime_type=mime)
        contents = [
            ref_part,
            f"Generate an ad creative that matches the visual style, color palette, "
            f"and aesthetic of the brand shown in the reference image. {prompt}"
        ]
    else:
        contents = prompt

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=gemini_ratio,
                    ),
                ),
            )
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    return part.inline_data.data  # already bytes in google-genai >= 1.16.0
            raise RuntimeError("No image data in Gemini response")

        except Exception as e:
            err_str = _sanitize_error(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF[attempt]
                    print(f"Rate limit hit, retrying in {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                    continue
            raise


def generate_openai(prompt: str, width: int, height: int, api_key: str, model: str) -> bytes:
    """Generate image using OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "Error: openai package required.\n"
            "Install with: pip install openai>=1.75.0",
            file=sys.stderr,
        )
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # OpenAI gpt-image-1 supported sizes: 1024x1024, 1536x1024, 1024x1536
    if width == height:
        size = "1024x1024"
    elif width > height:
        size = "1536x1024"
    else:
        size = "1024x1536"

    response = client.images.generate(
        model=model,
        prompt=prompt,
        n=1,
        size=size,
        response_format="b64_json",
    )
    return base64.b64decode(response.data[0].b64_json)


def generate_stability(prompt: str, width: int, height: int, api_key: str, model: str) -> bytes:
    """Generate image using Stability AI API."""
    try:
        import requests
    except ImportError:
        print("Error: requests package required. pip install requests", file=sys.stderr)
        sys.exit(1)

    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    headers = {
        "authorization": f"Bearer {api_key}",
        "accept": "image/*",
    }
    data = {
        "prompt": prompt,
        "model": model.split("/")[-1] if "/" in model else model,
        "aspect_ratio": _nearest_stability_ratio(width, height),
        "output_format": "png",
    }
    resp = guarded_request(
        requests,
        "POST",
        url,
        headers=headers,
        files={"none": ""},
        data=data,
        timeout=120,
    )
    if resp.status_code == 200:
        return resp.content
    raise RuntimeError(f"Stability API error {resp.status_code}: {resp.text[:200]}")


def _nearest_stability_ratio(width: int, height: int) -> str:
    """Map dimensions to Stability AI's supported aspect ratio strings."""
    ratio = width / height
    stability_ratios = {
        "1:1": 1.0,
        "16:9": 16/9,
        "9:16": 9/16,
        "4:5": 4/5,
        "5:4": 5/4,
        "3:2": 3/2,
        "2:3": 2/3,
    }
    return min(stability_ratios.keys(), key=lambda r: abs(stability_ratios[r] - ratio))


def generate_replicate(prompt: str, width: int, height: int, api_key: str, model: str) -> bytes:
    """Generate image using Replicate API."""
    try:
        import replicate
        import requests
    except ImportError:
        print(
            "Error: replicate package required.\n"
            "Install with: pip install replicate>=1.0.4",
            file=sys.stderr,
        )
        sys.exit(1)

    client = replicate.Client(api_token=api_key)
    output = client.run(
        model,
        input={
            "prompt": prompt,
            "width": width,
            "height": height,
            "output_format": "png",
        },
    )
    # Output is a URL or list of URLs
    url = output[0] if isinstance(output, list) else str(output)
    if urlparse(url).scheme != "https":
        raise RuntimeError(f"Replicate returned non-HTTPS URL: {url[:100]}")
    # Defense-in-depth: Replicate is trusted but revalidate against the SSRF
    # blocklist so an upstream compromise can't redirect us to a private IP.
    try:
        from url_utils import validate_url as _validate_url
        _validate_url(url)
    except ValueError as ve:
        raise RuntimeError(f"Replicate URL failed SSRF validation: {ve}") from ve
    # allow_redirects=False — the SSRF check above only validated the original
    # URL. A redirect target could be a private IP; refuse to follow at all.
    resp = guarded_request(requests, "GET", url, timeout=120)
    resp.raise_for_status()
    return resp.content


def _muapi_request(method: str, path: str, api_key: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make one guarded MuAPI JSON request against the fixed public API origin."""
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("requests package required for muapi provider") from exc

    if not path.startswith("/api/v1/"):
        raise ValueError("MuAPI path must be an /api/v1 endpoint")
    response = guarded_request(
        requests,
        method,
        f"{MUAPI_API_BASE}{path}",
        headers={"Accept": "application/json", "x-api-key": api_key},
        json=body,
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("MuAPI returned a non-object JSON response")
    return payload


def _muapi_find_model(identifier: str, api_key: str) -> dict[str, Any]:
    catalog = _muapi_request("GET", "/api/v1/models", api_key)
    models = catalog.get("models")
    if not isinstance(models, list):
        raise RuntimeError("MuAPI model catalog did not contain a models array")
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        endpoint = str(item.get("endpoint") or "").strip()
        category = str(item.get("category") or "").strip().lower()
        if identifier not in {name, endpoint}:
            continue
        if category not in {"text to image", "image to image"}:
            raise ValueError(f"MuAPI model '{name}' is not an image-generation model")
        if not endpoint.startswith("/api/v1/"):
            raise RuntimeError("MuAPI catalog returned an invalid model endpoint")
        return {"name": name, "endpoint": endpoint, "category": category}
    raise ValueError(f"No current MuAPI image model matched '{identifier}'")


def _muapi_dimension(value: int, schema: Mapping[str, Any]) -> int:
    minimum = int(schema.get("minValue", 1))
    maximum = int(schema.get("maxValue", MAX_DIMENSION))
    step = max(1, int(schema.get("step", 1)))
    rounded = round(value / step) * step
    return max(minimum, min(maximum, rounded))


def _muapi_payload(prompt: str, width: int, height: int, schema: Mapping[str, Any]) -> dict[str, Any]:
    properties = schema.get("schemas", {}).get("input_data", {}).get("properties", {})
    if not isinstance(properties, dict) or "prompt" not in properties:
        raise RuntimeError("Selected MuAPI model did not expose a prompt input schema")
    payload: dict[str, Any] = {"prompt": prompt}
    if "width" in properties and "height" in properties:
        payload["width"] = _muapi_dimension(width, properties["width"])
        payload["height"] = _muapi_dimension(height, properties["height"])
    elif "aspect_ratio" in properties:
        supported = properties["aspect_ratio"].get("enum", [])
        requested = min(
            ASPECT_RATIOS,
            key=lambda ratio: abs(
                (ASPECT_RATIOS[ratio][0] / ASPECT_RATIOS[ratio][1]) - (width / height)
            ),
        )
        if requested in supported:
            payload["aspect_ratio"] = requested
        elif "Auto" in supported:
            payload["aspect_ratio"] = "Auto"
    if "num_images" in properties:
        payload["num_images"] = 1
    return payload


def _muapi_output_urls(value: Any) -> list[str]:
    if isinstance(value, str) and value.startswith("https://"):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_muapi_output_urls(item))
        return result
    if isinstance(value, dict):
        result = []
        for key, item in value.items():
            if key in {"get", "request_url", "status", "id", "created_at"}:
                continue
            result.extend(_muapi_output_urls(item))
        return result
    return []


def _muapi_request_id(value: Mapping[str, Any]) -> str | None:
    data = value.get("data")
    candidates = [value.get("request_id"), value.get("id")]
    if isinstance(data, dict):
        candidates.extend([data.get("request_id"), data.get("id")])
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return None


def _muapi_download(url: str) -> bytes:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("requests package required for muapi provider") from exc
    if not url.startswith("https://"):
        raise RuntimeError("MuAPI returned a non-HTTPS output URL")
    response = guarded_request(
        requests,
        "GET",
        url,
        headers={"Accept": "image/*"},
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def generate_muapi(
    prompt: str,
    width: int,
    height: int,
    api_key: str,
    model: str,
    reference_image_path: str | None = None,
) -> bytes:
    """Generate one image through an explicitly selected current MuAPI model."""
    if reference_image_path:
        raise ValueError(
            "The muapi adapter does not declare reference-image support; "
            "use a verified image-to-image capability through a provider that supports local references"
        )
    selected = _muapi_find_model(model, api_key)
    detail = _muapi_request("GET", f"/api/v1/models/{quote(selected['name'], safe='')}", api_key)
    schema = detail.get("input_schema")
    if not isinstance(schema, dict):
        raise RuntimeError("MuAPI model metadata did not include an input schema")
    payload = _muapi_payload(prompt, width, height, schema)

    submission = _muapi_request("POST", selected["endpoint"], api_key, payload)
    request_id = _muapi_request_id(submission)
    if not request_id:
        raise RuntimeError("MuAPI submission did not return a request ID")

    for attempt in range(MUAPI_MAX_POLLS):
        result = _muapi_request(
            "GET",
            f"/api/v1/predictions/{quote(request_id, safe='')}/result",
            api_key,
        )
        data = result.get("data")
        status = str(
            result.get("status")
            or (data.get("status") if isinstance(data, dict) else "")
            or ""
        ).lower()
        outputs = _muapi_output_urls(result.get("outputs"))
        if not outputs:
            outputs = _muapi_output_urls(result.get("output"))
        if not outputs:
            outputs = _muapi_output_urls(result.get("data"))
        if outputs:
            return _muapi_download(outputs[0])
        if status in {"failed", "error", "canceled", "cancelled", "timeout"}:
            detail_message = result.get("error")
            if not detail_message and isinstance(data, dict):
                detail_message = data.get("error")
            raise RuntimeError(f"MuAPI generation failed: {detail_message or status}")
        if attempt + 1 < MUAPI_MAX_POLLS:
            time.sleep(MUAPI_POLL_INTERVAL)
    raise RuntimeError(f"MuAPI prediction did not finish after {MUAPI_MAX_POLLS} polls for request {request_id}")


def generate_image(
    prompt: str,
    ratio: str,
    provider: str,
    model: str,
    api_key: str,
    reference_image_path: str | None = None,
) -> tuple[bytes, int, int]:
    """
    Generate a single image. Returns (image_bytes, width, height).
    """
    provider, model = _require_selection(provider, model)
    width, height = _dims_from_ratio(ratio)

    if provider == "gemini":
        image_bytes = generate_gemini(
            prompt, width, height, api_key, model, reference_image_path
        )
    elif provider == "openai":
        if reference_image_path:
            raise ValueError(
                "The openai adapter does not declare reference-image support; "
                "choose a verified compatible capability or omit the reference image"
            )
        image_bytes = generate_openai(prompt, width, height, api_key, model)
    elif provider == "stability":
        if reference_image_path:
            raise ValueError(
                "The stability adapter does not declare reference-image support; "
                "choose a verified compatible capability or omit the reference image"
            )
        image_bytes = generate_stability(prompt, width, height, api_key, model)
    elif provider == "replicate":
        if reference_image_path:
            raise ValueError(
                "The replicate adapter does not declare reference-image support; "
                "choose a verified compatible capability or omit the reference image"
            )
        image_bytes = generate_replicate(prompt, width, height, api_key, model)
    elif provider == "muapi":
        image_bytes = generate_muapi(prompt, width, height, api_key, model, reference_image_path)
    else:
        print(f"Error: Unknown provider '{provider}'", file=sys.stderr)
        sys.exit(1)

    # Read actual dimensions from image header. Handles ratio remapping
    # (e.g. 1.91:1 request → Gemini generates 16:9 natively)
    actual = _actual_dimensions(image_bytes)
    if actual:
        width, height = actual

    return image_bytes, width, height


def _require_selection(provider: str | None, model: str | None) -> tuple[str, str]:
    """Return explicit provider/model identifiers or fail before credentials/network."""
    selected_provider = (provider or "").strip().lower()
    selected_model = (model or "").strip()
    if not selected_provider:
        raise ValueError(
            "Image provider is required; use --provider or ADS_IMAGE_PROVIDER "
            "after capability discovery"
        )
    if not selected_model:
        raise ValueError(
            "Image model is required; use --model or ADS_IMAGE_MODEL after "
            "capability discovery"
        )
    return selected_provider, selected_model


def run_batch(
    batch_file: str,
    output_dir: str,
    provider: str,
    model: str,
    api_key: str,
    as_json: bool,
    data_lifecycle: Mapping[str, Any],
    input_root: str | None = None,
) -> None:
    """
    Process a batch JSON file of generation jobs.

    Batch file format:
    [
        {"prompt": "...", "ratio": "9:16", "output": "tiktok-ad.png"},
        {"prompt": "...", "ratio": "1:1",  "output": "meta-square.png"}
    ]
    """
    provider, model = _require_selection(provider, model)
    validate_contract("data-lifecycle", data_lifecycle)
    with open(batch_file) as f:
        jobs = json.load(f)

    if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
        raise ValueError("Batch file must contain a JSON array of job objects")
    has_references = any(job.get("reference_image") is not None for job in jobs)
    reference_root = _reference_input_root(input_root) if has_references else Path.cwd()
    if len(jobs) > MAX_BATCH_SIZE:
        print(f"Error: Batch file contains {len(jobs)} jobs, max is {MAX_BATCH_SIZE}", file=sys.stderr)
        sys.exit(1)

    output_dir_path = resolve_output_path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    results = []

    for i, job in enumerate(jobs):
        prompt = job.get("prompt", "")
        ratio = job.get("ratio", "1:1")
        output_name = job.get("output", f"image_{i:03d}.png")
        # Security: strip path components to prevent directory traversal
        output_name = Path(output_name).name
        output_path = resolve_output_path(output_dir_path / output_name)
        reference_image = job.get("reference_image", None)

        result = {
            "index": i,
            **_prompt_record(prompt),
            "ratio": ratio,
            "file_locator": artifact_locator(output_path),
            "provider": provider,
            "model": model,
            "reference_image_sha256": None,
            "data_lifecycle": dict(data_lifecycle),
            "generation_success": False,
            "error": None,
        }

        try:
            print(f"[{i+1}/{len(jobs)}] Generating {output_name}...", file=sys.stderr)
            with _private_reference_snapshot(reference_image, reference_root) as (
                reference_snapshot,
                reference_sha256,
            ):
                image_bytes, width, height = generate_image(
                    prompt, ratio, provider, model, api_key, reference_snapshot
                )
            _write_private(output_path, image_bytes)
            result["reference_image_sha256"] = reference_sha256
            result["generation_success"] = True
            result["width"] = width
            result["height"] = height
            print(f"  ✓ Saved artifact {artifact_locator(output_path)} ({width}×{height})", file=sys.stderr)
        except Exception as e:
            result["error"] = "generation failed; inspect private ephemeral runtime logs"
            print(f"  ✗ Error: {_sanitize_error(e)}", file=sys.stderr)

        results.append(result)

    if as_json:
        print(json.dumps(results, indent=2))
    else:
        passed = sum(1 for r in results if r["generation_success"])
        print(f"\nBatch complete: {passed}/{len(results)} images generated")
        for r in results:
            status = "✓" if r["generation_success"] else "✗"
            print(f"  {status} {r['file_locator']}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate ad creative images using a pluggable image generation API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_image.py "approved creative prompt" --provider "$ADS_IMAGE_PROVIDER" --model "$ADS_IMAGE_MODEL" --ratio 16:9 --output ad.png
  python generate_image.py --batch prompts.json --provider "$ADS_IMAGE_PROVIDER" --model "$ADS_IMAGE_MODEL" --output-dir ./ad-assets/

Supported ratios: 1:1  9:16  16:9  4:5  4:3  3:4  1.91:1  4:1  21:9
Or use --size WxH for exact dimensions (e.g. --size 1200x628)

Both provider and model are required. Discover an approved capability first, then
use --provider/--model or ADS_IMAGE_PROVIDER/ADS_IMAGE_MODEL.
""",
    )

    # Prompt or batch mode
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("prompt", nargs="?", help="Image generation prompt")
    group.add_argument("--batch", "-b", metavar="FILE", help="Batch JSON file with multiple generation jobs")

    # Output options
    parser.add_argument("--output", "-o", metavar="FILE", help="Output file path (default: ad_[ratio].png)")
    parser.add_argument("--output-dir", metavar="DIR", default=".", help="Output directory for batch mode")
    parser.add_argument(
        "--input-root",
        metavar="DIR",
        help="Root containing rights-cleared reference images. Batch references must "
             "be relative paths beneath this root. CLAUDE_ADS_INPUT_ROOT is used "
             "when this option is omitted; one of them is required for references.",
    )

    # Dimension options
    dim_group = parser.add_mutually_exclusive_group()
    dim_group.add_argument(
        "--ratio", "-r",
        default="1:1",
        help="Aspect ratio shorthand (e.g. 9:16, 16:9, 4:5, 1:1). Default: 1:1",
    )
    dim_group.add_argument(
        "--size", "-s",
        metavar="WxH",
        help="Exact dimensions (e.g. 1200x628). Overrides --ratio.",
    )

    # Provider / model
    parser.add_argument(
        "--provider", "-p",
        default=None,
        help="Required provider adapter ID. Overrides ADS_IMAGE_PROVIDER.",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Required model ID from current capability evidence. Overrides ADS_IMAGE_MODEL.",
    )
    parser.add_argument(
        "--reference-image", "-i",
        metavar="FILE",
        dest="reference_image",
        help="Path to a rights-cleared brand reference image. Requires explicit "
             "support from the selected provider/model adapter.",
    )

    # Output format
    parser.add_argument("--json", "-j", action="store_true", help="Output result as JSON")
    parser.add_argument(
        "--data-lifecycle",
        required=True,
        help="Path to a valid data-lifecycle JSON contract for this generation run.",
    )

    args = parser.parse_args()

    # Resolve the explicitly selected, capability-verified provider and model.
    try:
        provider, model = _require_selection(
            args.provider or os.environ.get("ADS_IMAGE_PROVIDER"),
            args.model or os.environ.get("ADS_IMAGE_MODEL"),
        )
    except ValueError as exc:
        parser.error(str(exc))
    api_key = _get_api_key(provider)

    try:
        data_lifecycle = load_contract("data-lifecycle", args.data_lifecycle)
    except ContractError as exc:
        print(f"Error: {_sanitize_error(exc)}", file=sys.stderr)
        sys.exit(1)

    # Batch mode
    if args.batch:
        run_batch(
            args.batch,
            args.output_dir,
            provider,
            model,
            api_key,
            args.json,
            data_lifecycle,
            args.input_root,
        )
        return

    # Single image mode
    ratio = args.size if args.size else args.ratio

    output_path = args.output
    if not output_path:
        safe_ratio = ratio.replace(":", "-").replace(".", "_")
        output_path = f"ad_{safe_ratio}.png"

    try:
        if args.reference_image and not (
            args.input_root or os.environ.get("CLAUDE_ADS_INPUT_ROOT")
        ):
            raise ValueError(
                "--reference-image requires --input-root or CLAUDE_ADS_INPUT_ROOT; "
                "use a relative path beneath that root"
            )
        direct_root = _reference_input_root(args.input_root) if args.reference_image else Path.cwd()
        with _private_reference_snapshot(args.reference_image, direct_root) as (
            reference_snapshot,
            reference_sha256,
        ):
            image_bytes, width, height = generate_image(
                args.prompt, ratio, provider, model, api_key, reference_snapshot
            )
    except Exception as e:
        print(f"Error: {_sanitize_error(e)}", file=sys.stderr)
        sys.exit(1)

    try:
        resolved_output = resolve_output_path(output_path, create_parent=True)
    except ValueError as exc:
        print(f"Error: {_sanitize_error(exc)}", file=sys.stderr)
        sys.exit(1)
    _write_private(resolved_output, image_bytes)

    result = {
        "success": True,
        "file_locator": artifact_locator(resolved_output),
        "provider": provider,
        "model": model,
        "width": width,
        "height": height,
        "ratio": ratio,
        **_prompt_record(args.prompt),
        "reference_image_sha256": reference_sha256,
        "data_lifecycle": data_lifecycle,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"✓ Generated {width}×{height} image → {artifact_locator(resolved_output)}")


if __name__ == "__main__":
    main()
