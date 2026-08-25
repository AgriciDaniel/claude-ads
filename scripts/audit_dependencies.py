#!/usr/bin/env python3
"""Run pip-audit with expiring, code-path-bound not-affected evidence."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from datetime import date, timedelta
from importlib.metadata import PackageNotFoundError, version as distribution_version
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from packaging.version import InvalidVersion, Version


class DependencyAuditError(RuntimeError):
    """Raised when dependency evidence or audit output fails closed."""


PIP_AUDIT_VERSION = "2.10.1"
EXPECTED_CODE_SCOPE = ["claude_ads_core", "evals", "scripts"]
EXPECTED_POLICY = (
    "Only time-bounded not_affected dispositions are allowed. Accepted risk is not "
    "represented here. Any package, version, advisory, import, execution-path, or "
    "expiry drift fails closed."
)
MAX_EXCEPTION_AGE = timedelta(days=30)


@dataclass(frozen=True)
class ExceptionRecord:
    advisory_id: str
    package: str
    affected_version: str
    forbidden_import_prefixes: tuple[str, ...]


def _parse_date(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise DependencyAuditError(f"invalid {label} date") from exc


def _lock_versions(path: Path) -> dict[str, str]:
    logical = path.read_text(encoding="utf-8").replace("\\\n", " ")
    versions: dict[str, str] = {}
    for raw in logical.splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)==([^\s\\]+)", value)
        if not match:
            raise DependencyAuditError(f"lock entry is not exact: {path.name}")
        name = re.sub(r"[-_.]+", "-", match.group(1)).casefold()
        if name in versions:
            raise DependencyAuditError(f"duplicate lock component: {path.name}/{name}")
        versions[name] = match.group(2)
    return versions


def _repository_file(root: Path, relative: Any, label: str) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or relative.startswith("/")
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise DependencyAuditError(f"unsafe {label} path: {relative!r}")
    candidate = root
    for part in relative.split("/"):
        candidate = candidate / part
        if candidate.is_symlink():
            raise DependencyAuditError(f"symlinked {label} path: {relative}")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise DependencyAuditError(f"missing or escaping {label} path: {relative}") from exc
    if not resolved.is_file():
        raise DependencyAuditError(f"{label} path is not a file: {relative}")
    return resolved


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _import_names(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise DependencyAuditError(f"cannot inspect Python imports: {path}") from exc
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call) and _call_name(node.func) in {
            "__import__",
            "importlib.import_module",
        }:
            if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                raise DependencyAuditError(
                    f"dynamic module name bypasses vulnerability import guard: {path}"
                )
            names.add(node.args[0].value)
    return names


def _matches_prefix(import_name: str, prefix: str) -> bool:
    return (
        import_name == prefix
        or import_name.startswith(prefix + ".")
        or prefix.startswith(import_name + ".")
    )


def load_exceptions(root: Path, as_of: date) -> tuple[dict[str, ExceptionRecord], list[str]]:
    path = root / "control-plane/manifests/vulnerability-exceptions.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyAuditError(f"cannot load vulnerability exceptions: {exc}") from exc
    if set(document) != {
        "schema_version", "generated_at", "expires_at", "policy", "code_scope", "exceptions"
    } or document["schema_version"] != "1.0.0":
        raise DependencyAuditError("vulnerability exception document fields mismatch")
    if document["policy"] != EXPECTED_POLICY:
        raise DependencyAuditError("vulnerability exception policy mismatch")
    generated = _parse_date(document["generated_at"], "document generated_at")
    expires = _parse_date(document["expires_at"], "document expires_at")
    if (
        generated > as_of
        or expires < as_of
        or expires < generated
        or expires - generated > MAX_EXCEPTION_AGE
    ):
        raise DependencyAuditError("vulnerability exception document is stale or future-dated")

    runtime = _lock_versions(root / "requirements.lock")
    development = _lock_versions(root / "requirements-dev.lock")
    inconsistent = sorted(
        name
        for name in runtime.keys() & development.keys()
        if runtime[name] != development[name]
    )
    if inconsistent:
        raise DependencyAuditError(
            "runtime and development lock versions disagree: " + ", ".join(inconsistent)
        )
    locked = {**runtime, **development}
    records: dict[str, ExceptionRecord] = {}
    forbidden: set[str] = set()
    seen_aliases: set[str] = set()
    required_fields = {
        "advisory_id", "aliases", "advisory_url", "package", "affected_version",
        "fixed_versions", "status", "justification", "analysis", "evidence_paths",
        "forbidden_import_prefixes", "verified_at", "expires_at", "owner",
    }
    exceptions = document["exceptions"]
    if not isinstance(exceptions, list) or not exceptions:
        raise DependencyAuditError("vulnerability exception document is empty")
    for raw in exceptions:
        if not isinstance(raw, dict) or set(raw) != required_fields:
            raise DependencyAuditError("vulnerability exception fields mismatch")
        advisory_id = raw["advisory_id"]
        package = re.sub(r"[-_.]+", "-", str(raw["package"])).casefold()
        if (
            not isinstance(advisory_id, str)
            or not re.fullmatch(r"PYSEC-[0-9]{4}-[0-9]+", advisory_id)
            or advisory_id in records
            or package not in {"cryptography", "pillow"}
        ):
            raise DependencyAuditError("duplicate or invalid vulnerability exception ID")
        if raw["status"] != "not_affected" or raw["justification"] != "vulnerable_code_not_in_execute_path":
            raise DependencyAuditError(f"unsupported vulnerability disposition: {advisory_id}")
        verified = _parse_date(raw["verified_at"], f"{advisory_id} verified_at")
        record_expires = _parse_date(raw["expires_at"], f"{advisory_id} expires_at")
        if (
            verified != generated
            or verified > as_of
            or record_expires < as_of
            or record_expires > expires
            or record_expires - verified > MAX_EXCEPTION_AGE
        ):
            raise DependencyAuditError(f"vulnerability exception is stale or future-dated: {advisory_id}")
        if locked.get(package) != raw["affected_version"]:
            raise DependencyAuditError(f"vulnerability exception version drift: {advisory_id}")
        evidence_paths = raw["evidence_paths"]
        if (
            not isinstance(evidence_paths, list)
            or not evidence_paths
            or not all(isinstance(item, str) for item in evidence_paths)
            or len(evidence_paths) != len(set(evidence_paths))
        ):
            raise DependencyAuditError(f"vulnerability exception lacks evidence: {advisory_id}")
        for relative in evidence_paths:
            _repository_file(root, relative, f"vulnerability evidence for {advisory_id}")
        prefixes = raw["forbidden_import_prefixes"]
        if (
            not isinstance(prefixes, list)
            or not prefixes
            or not all(isinstance(item, str) for item in prefixes)
            or len(prefixes) != len(set(prefixes))
            or not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", item) for item in prefixes)
        ):
            raise DependencyAuditError(f"vulnerability exception lacks import guards: {advisory_id}")
        forbidden.update(prefixes)
        records[advisory_id] = ExceptionRecord(
            advisory_id=advisory_id,
            package=package,
            affected_version=raw["affected_version"],
            forbidden_import_prefixes=tuple(prefixes),
        )

        aliases = raw["aliases"]
        fixed_versions = raw["fixed_versions"]
        advisory_url = raw["advisory_url"]
        ghsa_aliases = (
            [item for item in aliases if isinstance(item, str) and item.startswith("GHSA-")]
            if isinstance(aliases, list)
            else []
        )
        try:
            affected = Version(raw["affected_version"])
            fixes = [Version(item) for item in fixed_versions]
        except (InvalidVersion, TypeError) as exc:
            raise DependencyAuditError(
                f"vulnerability exception version is invalid: {advisory_id}"
            ) from exc
        if (
            not isinstance(aliases, list)
            or not aliases
            or not all(isinstance(item, str) for item in aliases)
            or len(aliases) != len(set(aliases))
            or len(ghsa_aliases) != 1
            or seen_aliases.intersection(aliases)
            or not isinstance(advisory_url, str)
            or not re.fullmatch(
                rf"https://github\.com/[^/]+/[^/]+/security/advisories/{re.escape(ghsa_aliases[0])}",
                advisory_url,
            )
            or not isinstance(fixed_versions, list)
            or not fixed_versions
            or not all(isinstance(item, str) for item in fixed_versions)
            or len(fixed_versions) != len(set(fixed_versions))
            or any(item <= affected for item in fixes)
            or not isinstance(raw["analysis"], str)
            or len(raw["analysis"]) < 20
            or raw["owner"] != "security-owner"
            or record_expires < verified
        ):
            raise DependencyAuditError(f"vulnerability exception evidence is invalid: {advisory_id}")
        seen_aliases.update(aliases)

    scope = document["code_scope"]
    if scope != EXPECTED_CODE_SCOPE:
        raise DependencyAuditError("vulnerability exception code scope mismatch")
    imports: dict[str, set[str]] = {}
    for relative in scope:
        target = root / relative
        if not isinstance(relative, str) or not target.exists():
            raise DependencyAuditError(f"vulnerability code scope is missing: {relative}")
        candidates = [target] if target.is_file() else sorted(target.rglob("*.py"))
        for candidate in candidates:
            imports[candidate.relative_to(root).as_posix()] = _import_names(candidate)
    violations = sorted(
        f"{relative}: {import_name} matches prohibited {prefix}"
        for relative, imported in imports.items()
        for import_name in imported
        for prefix in forbidden
        if _matches_prefix(import_name, prefix)
    )
    if violations:
        raise DependencyAuditError("vulnerability execution-path guard failed: " + "; ".join(violations))
    return records, sorted(scope)


def evaluate_reports(
    reports: dict[str, dict[str, Any]], records: dict[str, ExceptionRecord]
) -> dict[str, Any]:
    observed: set[str] = set()
    unhandled: list[str] = []
    vulnerable_packages: set[str] = set()
    for profile, report in reports.items():
        dependencies = report.get("dependencies")
        if not isinstance(dependencies, list):
            raise DependencyAuditError(f"pip-audit report is invalid: {profile}")
        for dependency in dependencies:
            package = re.sub(r"[-_.]+", "-", str(dependency.get("name", ""))).casefold()
            version = str(dependency.get("version", ""))
            for vulnerability in dependency.get("vulns", []):
                advisory_id = vulnerability.get("id")
                record = records.get(advisory_id)
                vulnerable_packages.add(package)
                if record and record.package == package and record.affected_version == version:
                    observed.add(advisory_id)
                else:
                    unhandled.append(f"{profile}:{package}@{version}:{advisory_id}")
    stale = sorted(set(records) - observed)
    if unhandled:
        raise DependencyAuditError("unhandled dependency vulnerabilities: " + ", ".join(sorted(unhandled)))
    if stale:
        raise DependencyAuditError("vulnerability exceptions no longer match audit output: " + ", ".join(stale))
    return {
        "status": "pass",
        "profiles": sorted(reports),
        "not_affected_advisory_count": len(observed),
        "vulnerable_package_count": len(vulnerable_packages),
        "unhandled_advisory_count": 0,
    }


def _run_pip_audit(root: Path, lock_name: str) -> dict[str, Any]:
    try:
        installed_version = distribution_version("pip-audit")
    except PackageNotFoundError as exc:
        raise DependencyAuditError("pip-audit is not installed") from exc
    if installed_version != PIP_AUDIT_VERSION:
        raise DependencyAuditError(
            f"pip-audit version mismatch: expected {PIP_AUDIT_VERSION}, got {installed_version}"
        )
    command = [
        sys.executable, "-m", "pip_audit", "--no-deps", "--disable-pip",
        "--strict", "-r", str(root / lock_name), "-f", "json",
    ]
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        detail = result.stderr.strip().splitlines()[-1:] or ["no diagnostic"]
        raise DependencyAuditError(f"pip-audit did not return JSON for {lock_name}: {detail[0]}") from exc
    if result.returncode not in {0, 1}:
        raise DependencyAuditError(f"pip-audit failed for {lock_name} with exit {result.returncode}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        records, scope = load_exceptions(root, args.as_of)
        reports = {
            "runtime": _run_pip_audit(root, "requirements.lock"),
            "development": _run_pip_audit(root, "requirements-dev.lock"),
        }
        summary = evaluate_reports(reports, records)
        summary["guarded_code_scope"] = scope
        print(json.dumps(summary, sort_keys=True))
        return 0
    except DependencyAuditError as exc:
        print(f"dependency audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
