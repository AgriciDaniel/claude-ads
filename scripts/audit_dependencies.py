#!/usr/bin/env python3
"""Run pip-audit with expiring, code-path-bound not-affected evidence."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from datetime import date, timedelta
from importlib.metadata import PackageNotFoundError, version as distribution_version
import importlib.util
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
# Packages that may carry a reviewed not_affected exception. Adding a package
# here is a reviewed change; the audit rejects exceptions for any other package.
EXCEPTION_PACKAGES = frozenset({"cryptography", "pillow", "weasyprint"})


@dataclass(frozen=True)
class ExceptionRecord:
    advisory_id: str
    package: str
    affected_version: str
    forbidden_import_prefixes: tuple[str, ...]
    forbidden_call_keywords: tuple[str, ...] = ()


CALL_KEYWORD_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*")


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


# Modules whose attributes import other modules by name. A local name bound
# to one of these modules, or to one of these attributes, is tracked so the
# guard can see the module name passed to the eventual call.
IMPORTER_ATTRIBUTES: dict[str, frozenset[str]] = {
    "importlib": frozenset({"import_module", "__import__"}),
    "builtins": frozenset({"__import__"}),
}


def _string_constant(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


class _ImportGuard:
    """Static import resolver for one source file.

    Tracks names bound to ``importlib``/``builtins`` and to their importer
    callables (``import_module`` and ``__import__`` in any spelling, including
    from-imports and simple ``name = <importer>`` aliases), then requires every
    reference to an importer to be a direct call with a string-literal module
    name. Anything else raises ``DependencyAuditError`` so it cannot pass
    silently. This is a syntactic guard over first-party source only.
    """

    def __init__(self, path: Path, tree: ast.AST) -> None:
        self.path = path
        self.tree = tree
        self.modules: dict[str, str] = {"__builtins__": "builtins"}
        self.importers: set[str] = {"__import__"}
        self.alias_values: set[int] = set()

    def _fail(self, node: ast.AST, reason: str) -> DependencyAuditError:
        line = getattr(node, "lineno", "?")
        return DependencyAuditError(
            f"unresolvable dynamic import bypasses vulnerability import guard "
            f"({reason}): {self.path}:{line}"
        )

    def _module_of(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return self.modules.get(node.id)
        if isinstance(node, ast.Call) and self._is_importer(node.func):
            module = self._literal_module_name(node)
            if module in IMPORTER_ATTRIBUTES:
                return module
        return None

    def _attribute_target(self, node: ast.expr) -> tuple[str, ast.expr | None] | None:
        """Return (module, attribute node) for ``mod.x``, ``mod["x"]``, ``getattr(mod, x)``."""
        if isinstance(node, ast.Attribute):
            module = self._module_of(node.value)
            return (module, ast.Constant(node.attr)) if module else None
        if isinstance(node, ast.Subscript):
            module = self._module_of(node.value)
            return (module, node.slice) if module else None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and node.args
        ):
            module = self._module_of(node.args[0])
            attribute = node.args[1] if len(node.args) > 1 else None
            return (module, attribute) if module else None
        return None

    def _is_importer(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return isinstance(node.ctx, ast.Load) and node.id in self.importers
        target = self._attribute_target(node)
        if target is None:
            return False
        module, attribute = target
        name = _string_constant(attribute)
        if name is None:
            raise self._fail(node, f"computed attribute of {module}")
        return name in IMPORTER_ATTRIBUTES[module]

    def _bind(self) -> None:
        """Collect module and importer bindings until no new name appears."""
        while True:
            before = (len(self.modules), len(self.importers), len(self.alias_values))
            for node in ast.walk(self.tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if alias.asname is None and top in IMPORTER_ATTRIBUTES:
                            self.modules[top] = top
                        elif alias.asname and alias.name in IMPORTER_ATTRIBUTES:
                            self.modules[alias.asname] = alias.name
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module in IMPORTER_ATTRIBUTES:
                        exported = IMPORTER_ATTRIBUTES[node.module]
                        for alias in node.names:
                            if alias.name == "*":
                                self.importers.update(exported)
                            elif alias.name in exported:
                                self.importers.add(alias.asname or alias.name)
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    names = [t.id for t in targets if isinstance(t, ast.Name)]
                    if node.value is None or len(names) != len(targets):
                        continue
                    if self._is_importer(node.value):
                        self.importers.update(names)
                        self.alias_values.add(id(node.value))
                    else:
                        module = self._module_of(node.value)
                        if module:
                            self.modules.update((name, module) for name in names)
            if before == (len(self.modules), len(self.importers), len(self.alias_values)):
                return

    def _literal_module_name(self, call: ast.Call) -> str | None:
        if any(isinstance(arg, ast.Starred) for arg in call.args) or any(
            keyword.arg is None for keyword in call.keywords
        ):
            return None
        keywords = {keyword.arg: keyword.value for keyword in call.keywords}
        name = _string_constant(call.args[0] if call.args else keywords.get("name"))
        if name is None:
            return None
        level = call.args[4] if len(call.args) > 4 else keywords.get("level")
        if level is not None and not (isinstance(level, ast.Constant) and level.value == 0):
            return None
        if not name.startswith("."):
            return name
        package = _string_constant(call.args[1] if len(call.args) > 1 else keywords.get("package"))
        if package is None:
            return None
        try:
            return importlib.util.resolve_name(name, package)
        except (ImportError, ValueError):
            return None

    def dynamic_imports(self) -> set[str]:
        self._bind()
        names: set[str] = set()
        call_targets: set[int] = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and self._is_importer(node.func):
                call_targets.add(id(node.func))
                name = self._literal_module_name(node)
                if name is None:
                    raise self._fail(node, "module name is not a string literal")
                names.add(name)
        for node in ast.walk(self.tree):
            if id(node) in call_targets or id(node) in self.alias_values:
                continue
            if isinstance(node, ast.expr) and self._is_importer(node):
                raise self._fail(node, "importer referenced outside a literal call")
        return names


def _call_keywords(path: Path) -> set[str]:
    """Return ``function:keyword`` for every keyword argument passed to a call.

    A call that forwards ``**mapping`` is reported as ``function:**`` and a
    call whose target is not a plain name or attribute (``getattr(...)()``,
    ``table["key"]()``, ``factory()()``) is reported with the function ``?``,
    so a guarded keyword or an unresolvable forward never passes silently.
    Forwarded mappings follow simple assignment aliases conservatively across
    the file; cycles remain unresolved. Computed values assigned to
    names (such as dynamic HTTP dispatchers), interprocedural data flow, and
    assignments to library option dictionaries are outside this guard.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases: dict[str, list[ast.expr]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(
            node.value, (ast.Name, ast.Attribute)
        ):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    aliases.setdefault(target.id, []).append(node.value)

    def forwarded_targets(func: ast.expr, visiting: frozenset[str] = frozenset()) -> set[str]:
        if isinstance(func, ast.Attribute):
            return {func.attr}
        if isinstance(func, ast.Name):
            if func.id in visiting:
                return {"?"}
            if func.id not in aliases:
                return {func.id}
            # Preserve the syntactic name: aliases elsewhere in the file must
            # not hide a guarded call in another scope.
            return {func.id}.union(*(
                forwarded_targets(value, visiting | {func.id})
                for value in aliases[func.id]
            ))
        return {"?"}

    observed: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        else:
            name = "?"
        for keyword in node.keywords:
            if keyword.arg is None:
                observed.update(f"{target}:**" for target in forwarded_targets(func))
            else:
                observed.add(f"{name}:{keyword.arg}")
    return observed


def _matches_call_keyword(observed: str, pattern: str) -> bool:
    """A guarded keyword passed to any callable matches; so does a forwarded
    mapping to the guarded function or to an unresolvable callee."""

    function, _, keyword = observed.partition(":")
    guarded_function, _, guarded_keyword = pattern.partition(":")
    if keyword == guarded_keyword:
        return True
    return keyword == "**" and function in {guarded_function, "?"}


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
    names.update(_ImportGuard(path, tree).dynamic_imports())
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
    forbidden_calls: set[str] = set()
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
        if not isinstance(raw, dict) or set(raw) - {"forbidden_call_keywords"} != required_fields:
            raise DependencyAuditError("vulnerability exception fields mismatch")
        advisory_id = raw["advisory_id"]
        package = re.sub(r"[-_.]+", "-", str(raw["package"])).casefold()
        if (
            not isinstance(advisory_id, str)
            or not re.fullmatch(r"PYSEC-[0-9]{4}-[0-9]+", advisory_id)
            or advisory_id in records
            or package not in EXCEPTION_PACKAGES
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
        call_keywords = raw.get("forbidden_call_keywords", [])
        if (
            not isinstance(prefixes, list)
            or not all(isinstance(item, str) for item in prefixes)
            or len(prefixes) != len(set(prefixes))
            or not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", item) for item in prefixes)
            or not isinstance(call_keywords, list)
            or not all(isinstance(item, str) for item in call_keywords)
            or len(call_keywords) != len(set(call_keywords))
            or not all(CALL_KEYWORD_PATTERN.fullmatch(item) for item in call_keywords)
            or not (prefixes or call_keywords)
        ):
            raise DependencyAuditError(f"vulnerability exception lacks import guards: {advisory_id}")
        forbidden.update(prefixes)
        forbidden_calls.update(call_keywords)
        records[advisory_id] = ExceptionRecord(
            advisory_id=advisory_id,
            package=package,
            affected_version=raw["affected_version"],
            forbidden_import_prefixes=tuple(prefixes),
            forbidden_call_keywords=tuple(call_keywords),
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
    calls: dict[str, set[str]] = {}
    for relative in scope:
        target = root / relative
        if not isinstance(relative, str) or not target.exists():
            raise DependencyAuditError(f"vulnerability code scope is missing: {relative}")
        candidates = [target] if target.is_file() else sorted(target.rglob("*.py"))
        for candidate in candidates:
            key = candidate.relative_to(root).as_posix()
            imports[key] = _import_names(candidate)
            calls[key] = _call_keywords(candidate)
    violations = sorted(
        f"{relative}: {import_name} matches prohibited {prefix}"
        for relative, imported in imports.items()
        for import_name in imported
        for prefix in forbidden
        if _matches_prefix(import_name, prefix)
    )
    violations.extend(
        sorted(
            f"{relative}: {call} matches prohibited {pattern}"
            for relative, observed_calls in calls.items()
            for call in observed_calls
            for pattern in forbidden_calls
            if _matches_call_keyword(call, pattern)
        )
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
            "schema-tests": _run_pip_audit(
                root, ".github/requirements-schema-tests.lock"
            ),
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
