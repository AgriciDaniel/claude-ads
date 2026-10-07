#!/usr/bin/env python3
"""Verify a native pip report and downloaded wheel closure against reviewed evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
from pathlib import Path
import subprocess
import sys

_RELEASE_SPEC = importlib.util.spec_from_file_location("claude_ads_target_release", Path(__file__).with_name("release.py"))
if _RELEASE_SPEC is None or _RELEASE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("cannot load the release verifier")
release = importlib.util.module_from_spec(_RELEASE_SPEC)
sys.modules[_RELEASE_SPEC.name] = release
_RELEASE_SPEC.loader.exec_module(release)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_target_id(profile: str) -> str:
    if sys.implementation.name != "cpython" or sys.version_info[:2] not in {(3, 11), (3, 12)}:
        raise release.ReleaseError("native lock evidence requires CPython 3.11 or 3.12")
    system = platform.system().lower()
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    if system == "linux" and machine == "x86_64":
        libc_name, libc_version = platform.libc_ver()
        try:
            libc_ok = libc_name == "glibc" and tuple(map(int, libc_version.split(".")[:2])) >= (2, 28)
        except ValueError:
            libc_ok = False
        if not libc_ok:
            raise release.ReleaseError("native Linux lock evidence requires glibc >=2.28; musl is unsupported")
        target = "linux"
    elif system == "darwin" and machine in {"arm64", "x86_64"}:
        target = "macos-arm" if machine == "arm64" else "macos-x86"
    elif system == "windows" and machine == "x86_64":
        target = "windows"
    else:
        raise release.ReleaseError(f"no reviewed native lock target for {system}/{machine}")
    return f"{profile}-{target}-cp{sys.version_info.major}{sys.version_info.minor}"


def verify(root: Path, profile: str, pip_report: Path, wheel_dir: Path, output: Path) -> None:
    inventory = release._load_dependency_inventory(root)
    target_id = native_target_id(profile)
    target = next(item for item in inventory["targets"] if item["id"] == target_id)
    expected = {item["name"]: item for item in target["components"]}

    report_data = pip_report.read_bytes()
    report = json.loads(report_data)
    try:
        from pip import __version__ as executing_pip_version
    except ImportError as exc:
        raise release.ReleaseError("pip is required for native target verification") from exc
    if report.get("pip_version") != executing_pip_version:
        raise release.ReleaseError("pip report version does not equal the executing resolver")
    observed = {}
    for item in report.get("install", []):
        metadata = item.get("metadata", {})
        name = release._canonical_package_name(str(metadata.get("name", "")))
        download = item.get("download_info", {})
        hashes = download.get("archive_info", {}).get("hashes", {})
        record = expected.get(name)
        if record is None or name in observed:
            raise release.ReleaseError(f"pip report contains duplicate or unexpected component: {name}")
        artifact = record["artifact"]
        if (
            str(metadata.get("version")) != record["version"]
            or download.get("url") != artifact["url"]
            or hashes.get("sha256") != artifact["sha256"]
        ):
            raise release.ReleaseError(f"pip report artifact mismatch: {target_id}/{name}")
        observed[name] = {
            "name": name, "version": record["version"], "filename": artifact["filename"],
            "url": artifact["url"], "sha256": artifact["sha256"],
        }
    if set(observed) != set(expected):
        raise release.ReleaseError(f"pip report closure mismatch: missing={sorted(set(expected)-set(observed))}")

    wheels = {path.name: sha256(path) for path in wheel_dir.glob("*.whl") if path.is_file()}
    expected_wheels = {item["artifact"]["filename"]: item["artifact"]["sha256"] for item in expected.values()}
    if wheels != expected_wheels:
        raise release.ReleaseError("downloaded wheel filenames/hashes do not equal the target inventory")

    evidence_path = root / "control-plane/dependency-evidence" / f"{target_id}.json"
    inventory_path = root / "control-plane/manifests/dependency-inventory.json"
    lock_path = root / ("requirements.lock" if profile == "runtime" else "requirements-dev.lock")
    commit_result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=False, capture_output=True, text=True)
    if commit_result.returncode:
        raise release.ReleaseError("cannot bind native target evidence to a Git commit")
    attestation = {
        "schema_version": "1.0.0",
        "evidence_class": "native-pip-report-and-downloaded-wheel-confirmation",
        "target_id": target_id,
        "environment": {
            "implementation": platform.python_implementation(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "platform": platform.platform(),
            "machine": platform.machine(),
            "libc": list(platform.libc_ver()),
            "runner": {name: os.environ[name] for name in ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH") if name in os.environ},
        },
        "source_commit": commit_result.stdout.strip(),
        "dependency_inventory_sha256": sha256(inventory_path),
        "requirements_lock_sha256": sha256(lock_path),
        "pip_version": executing_pip_version,
        "pip_report_sha256": hashlib.sha256(report_data).hexdigest(),
        "normalized_evidence_sha256": sha256(evidence_path),
        "components": [observed[name] for name in sorted(observed)],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("runtime", "development"), required=True)
    parser.add_argument("--pip-report", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        verify(Path(__file__).resolve().parents[1], args.profile, args.pip_report, args.wheel_dir, args.output)
    except (OSError, ValueError, json.JSONDecodeError, release.ReleaseError) as exc:
        print(f"target lock verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"verified native target lock: {native_target_id(args.profile)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
