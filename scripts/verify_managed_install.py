#!/usr/bin/env python3
"""Verify a completed managed installer result on its native host."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any


RECEIPT_FIELDS = {
    "schema_version", "receipt_class", "target_id", "target", "resolver",
    "python_full_version", "pip_version", "requirements_lock_sha256",
    "dependency_inventory_sha256", "target_evidence_sha256",
    "pip_install_report_sha256", "components",
}
TARGET_FIELDS = ("python_version", "implementation", "os", "arch", "abi")
PROBE_FIELDS = {
    "python_full_version", "python_version", "implementation", "system", "machine",
    "abi", "pip_version", "claude_ads_core_version", "claude_ads_core_file",
    "installed",
}
BOOTSTRAP_COMPONENTS = {"pip", "setuptools", "wheel"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_name(value: str) -> str:
    return value.lower().replace("_", "-").replace(".", "-")


def _canonical_native_identity(system: str, machine: str) -> tuple[str, str, str]:
    system = system.lower()
    machine = machine.lower()
    if system == "linux" and machine in {"x86_64", "amd64"}:
        return "linux", "linux", "x86_64"
    if system == "darwin" and machine in {"x86_64", "amd64"}:
        return "macos-x86", "macos", "x86_64"
    if system == "darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm", "macos", "arm64"
    if system == "windows" and machine in {"amd64", "x86_64"}:
        return "windows", "windows", "amd64"
    raise ValueError(f"no managed install target for {system}/{machine}")


def _native_platform() -> tuple[str, str, str]:
    return _canonical_native_identity(platform.system(), platform.machine())


def _target_id(python_version: str | None = None) -> str:
    version = python_version or f"{sys.version_info.major}.{sys.version_info.minor}"
    if version not in {"3.11", "3.12"}:
        raise ValueError("managed install verification requires CPython 3.11 or 3.12")
    platform_id, _, _ = _native_platform()
    return f"runtime-{platform_id}-cp{version.replace('.', '')}"


def _read_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _managed_python(skill_dir: Path) -> Path:
    windows = platform.system().lower() == "windows"
    python = skill_dir / ".venv" / ("Scripts/python.exe" if windows else "bin/python")
    if not python.is_file():
        raise ValueError("managed runtime interpreter is missing")
    return python


def _probe_interpreter(python: Path, skill_dir: Path) -> dict[str, Any]:
    probe = r'''
import json
from importlib import metadata
import platform
import sys
sys.path.insert(0, sys.argv[1])
import claude_ads_core

def canonical(value):
    return value.lower().replace("_", "-").replace(".", "-")

installed = sorted(
    {
        (canonical(dist.metadata.get("Name", "")), dist.version)
        for dist in metadata.distributions()
        if dist.metadata.get("Name")
    }
)
print(json.dumps({
    "python_full_version": platform.python_version(),
    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
    "implementation": platform.python_implementation(),
    "system": platform.system(),
    "machine": platform.machine(),
    "abi": f"cp{sys.version_info.major}{sys.version_info.minor}",
    "pip_version": metadata.version("pip"),
    "claude_ads_core_version": str(claude_ads_core.__version__),
    "claude_ads_core_file": str(claude_ads_core.__file__),
    "installed": [{"name": name, "version": version} for name, version in installed],
}, sort_keys=True))
'''
    result = subprocess.run(
        [str(python), "-I", "-c", probe, str(skill_dir / "scripts")],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise ValueError(f"managed runtime interpreter probe failed: {result.stderr.strip()}")
    try:
        observed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("managed runtime interpreter probe did not return JSON") from exc
    if not isinstance(observed, dict) or set(observed) != PROBE_FIELDS:
        raise ValueError("managed runtime interpreter probe fields mismatch")
    for field in PROBE_FIELDS - {"installed"}:
        if not isinstance(observed[field], str) or not observed[field]:
            raise ValueError(f"managed runtime interpreter probe {field} is invalid")
    expected_core = (skill_dir / "scripts/claude_ads_core/__init__.py").resolve()
    if not expected_core.is_file() or Path(observed["claude_ads_core_file"]).resolve() != expected_core:
        raise ValueError("managed runtime interpreter imported core outside the installed skill")
    installed = observed["installed"]
    if not isinstance(installed, list):
        raise ValueError("managed runtime interpreter installed closure is invalid")
    seen: set[str] = set()
    for component in installed:
        if (
            not isinstance(component, dict)
            or set(component) != {"name", "version"}
            or not isinstance(component["name"], str)
            or not component["name"]
            or not isinstance(component["version"], str)
            or not component["version"]
            or component["name"] in seen
        ):
            raise ValueError("managed runtime interpreter installed closure is invalid")
        seen.add(component["name"])
    return observed


def _expected_receipt_components(target: dict[str, Any]) -> list[dict[str, Any]]:
    components = target.get("components")
    if not isinstance(components, list):
        raise ValueError("dependency inventory target components must be an array")
    expected: list[dict[str, Any]] = []
    names: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("dependency inventory target component is invalid")
        name = component.get("name")
        version = component.get("version")
        artifact = component.get("artifact")
        if (
            not isinstance(name, str)
            or not name
            or name != _canonical_name(name)
            or name in names
            or not isinstance(version, str)
            or not version
            or not isinstance(artifact, dict)
            or set(artifact) != {"filename", "url", "sha256"}
            or not all(isinstance(artifact[field], str) and artifact[field] for field in artifact)
        ):
            raise ValueError("dependency inventory target component is invalid")
        names.add(name)
        expected.append({"name": name, "version": version, "artifact": artifact})
    return sorted(expected, key=lambda item: item["name"])


def _validate_pip_report(
    report: Any,
    expected_components: list[dict[str, Any]],
    pip_version: str,
) -> None:
    if not isinstance(report, dict) or report.get("pip_version") != pip_version:
        raise ValueError("managed runtime pip report resolver version mismatch")
    install = report.get("install")
    if not isinstance(install, list):
        raise ValueError("managed runtime pip report install closure is invalid")
    expected = {component["name"]: component for component in expected_components}
    observed: set[str] = set()
    for item in install:
        if not isinstance(item, dict):
            raise ValueError("managed runtime pip report component is invalid")
        metadata = item.get("metadata")
        download = item.get("download_info")
        if not isinstance(metadata, dict) or not isinstance(download, dict):
            raise ValueError("managed runtime pip report component is invalid")
        name = _canonical_name(str(metadata.get("name", "")))
        component = expected.get(name)
        archive_info = download.get("archive_info")
        hashes = archive_info.get("hashes", {}) if isinstance(archive_info, dict) else {}
        if component is None or name in observed:
            raise ValueError(f"managed runtime pip report has unexpected or duplicate component: {name}")
        artifact = component["artifact"]
        if (
            metadata.get("version") != component["version"]
            or download.get("url") != artifact["url"]
            or hashes.get("sha256") != artifact["sha256"]
        ):
            raise ValueError(f"managed runtime pip report artifact mismatch: {name}")
        observed.add(name)
    if observed != set(expected):
        raise ValueError("managed runtime pip report closure mismatch")


def verify(repository: Path, skill_dir: Path) -> dict[str, object]:
    receipt_path = skill_dir / "managed-runtime-receipt.json"
    receipt = _read_json(receipt_path, "managed runtime receipt")
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        raise ValueError("managed runtime receipt fields mismatch")
    if (
        receipt.get("schema_version") != "1.0.0"
        or receipt.get("receipt_class") != "managed-python-runtime-install"
    ):
        raise ValueError("managed runtime receipt identity mismatch")

    python = _managed_python(skill_dir)
    probe = _probe_interpreter(python, skill_dir)
    if probe["implementation"] != "CPython":
        raise ValueError("managed runtime interpreter implementation mismatch")
    target_id = _target_id(probe["python_version"])
    if receipt.get("target_id") != target_id:
        raise ValueError("managed runtime receipt native target mismatch")

    inventory_path = repository / "control-plane/manifests/dependency-inventory.json"
    inventory = _read_json(inventory_path, "dependency inventory")
    targets = inventory.get("targets") if isinstance(inventory, dict) else None
    target = next(
        (
            candidate
            for candidate in targets or []
            if isinstance(candidate, dict) and candidate.get("id") == target_id
        ),
        None,
    )
    if target is None:
        raise ValueError(f"dependency inventory omits native target {target_id}")
    expected_target = {field: target.get(field) for field in TARGET_FIELDS}
    if receipt.get("target") != expected_target:
        raise ValueError("managed runtime receipt target metadata mismatch")
    host_identity = _native_platform()
    probe_identity = _canonical_native_identity(probe["system"], probe["machine"])
    _, native_os, native_arch = host_identity
    probe_target = {
        "python_version": probe["python_version"],
        "implementation": probe["implementation"],
        "os": probe_identity[1],
        "arch": probe_identity[2],
        "abi": probe["abi"],
    }
    if (
        probe_identity != host_identity
        or expected_target != probe_target
        or expected_target["os"] != native_os
        or expected_target["arch"] != native_arch
    ):
        raise ValueError("managed runtime interpreter does not match native inventory target")
    if receipt.get("resolver") != target.get("resolver") or receipt.get("resolver") != "pip / PyPI":
        raise ValueError("managed runtime receipt resolver mismatch")
    if receipt.get("python_full_version") != probe["python_full_version"]:
        raise ValueError("managed runtime receipt Python version mismatch")
    if receipt.get("pip_version") != probe["pip_version"]:
        raise ValueError("managed runtime receipt pip version mismatch")

    lock_path = repository / "requirements.lock"
    if receipt.get("requirements_lock_sha256") != _sha256(lock_path):
        raise ValueError("managed runtime receipt lock binding mismatch")
    if receipt.get("dependency_inventory_sha256") != _sha256(inventory_path):
        raise ValueError("managed runtime receipt inventory binding mismatch")
    evidence_path = repository / "control-plane/dependency-evidence" / f"{target_id}.json"
    evidence_sha256 = _sha256(evidence_path)
    if target.get("resolution_evidence_sha256") != evidence_sha256:
        raise ValueError("dependency inventory target evidence binding mismatch")
    if receipt.get("target_evidence_sha256") != evidence_sha256:
        raise ValueError("managed runtime receipt target evidence binding mismatch")

    expected_components = _expected_receipt_components(target)
    if receipt.get("components") != expected_components:
        raise ValueError("managed runtime receipt closure mismatch")
    report_path = skill_dir / ".venv" / "install-report.json"
    report = _read_json(report_path, "managed runtime pip install report")
    if receipt.get("pip_install_report_sha256") != _sha256(report_path):
        raise ValueError("managed runtime receipt pip report binding mismatch")
    _validate_pip_report(report, expected_components, probe["pip_version"])

    expected_versions = {
        component["name"]: component["version"] for component in expected_components
    }
    installed_versions = {
        component["name"]: component["version"] for component in probe["installed"]
    }
    unexpected = sorted(set(installed_versions) - set(expected_versions) - BOOTSTRAP_COMPONENTS)
    missing = sorted(set(expected_versions) - set(installed_versions))
    mismatched = sorted(
        name
        for name in set(expected_versions) & set(installed_versions)
        if expected_versions[name] != installed_versions[name]
    )
    if unexpected or missing or mismatched:
        raise ValueError(
            "managed runtime interpreter closure mismatch: "
            f"missing={missing}, unexpected={unexpected}, mismatched={mismatched}"
        )

    check = subprocess.run(
        [str(python), "-m", "pip", "check"],
        check=False,
        text=True,
        capture_output=True,
    )
    if check.returncode:
        raise ValueError(f"managed runtime execution check failed: {check.stderr.strip()}")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repository",
        type=Path,
        required=True,
        help="source checkout containing reviewed dependency inventory and target evidence",
    )
    parser.add_argument("--skill-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = verify(args.repository.resolve(), args.skill_dir.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"managed install verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"verified managed install: {receipt['target_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
