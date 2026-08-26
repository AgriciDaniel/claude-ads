from __future__ import annotations

from datetime import date
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit_dependencies.py"
SPEC = importlib.util.spec_from_file_location("claude_ads_dependency_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def _reports(records):
    dependencies = {}
    for record in records.values():
        key = (record.package, record.affected_version)
        dependencies.setdefault(key, []).append({"id": record.advisory_id})
    runtime = {
        "dependencies": [
            {"name": package, "version": version, "vulns": vulnerabilities}
            for (package, version), vulnerabilities in sorted(dependencies.items())
        ]
    }
    development = {
        "dependencies": [
            item for item in runtime["dependencies"] if item["name"] == "cryptography"
        ]
    }
    return {
        "runtime": runtime,
        "development": development,
        "schema-tests": {"dependencies": []},
    }


def test_not_affected_evidence_matches_locks_and_code_paths() -> None:
    records, scope = audit.load_exceptions(ROOT, date(2026, 8, 25))
    assert len(records) == 16
    assert scope == ["claude_ads_core", "evals", "scripts"]
    summary = audit.evaluate_reports(_reports(records), records)
    assert summary == {
        "status": "pass",
        "profiles": ["development", "runtime", "schema-tests"],
        "not_affected_advisory_count": 16,
        "vulnerable_package_count": 2,
        "unhandled_advisory_count": 0,
    }


def test_unhandled_advisory_fails_closed() -> None:
    records, _ = audit.load_exceptions(ROOT, date(2026, 8, 25))
    reports = _reports(records)
    reports["runtime"]["dependencies"].append(
        {"name": "example", "version": "1.0", "vulns": [{"id": "PYSEC-2099-1"}]}
    )
    with pytest.raises(audit.DependencyAuditError, match="unhandled dependency vulnerabilities"):
        audit.evaluate_reports(reports, records)


def test_stale_exception_document_fails_closed() -> None:
    with pytest.raises(audit.DependencyAuditError, match="stale or future-dated"):
        audit.load_exceptions(ROOT, date(2026, 9, 25))


def test_import_prefix_guard_detects_parent_and_child_imports() -> None:
    assert audit._matches_prefix("PIL.Image", "PIL")
    assert audit._matches_prefix("cryptography", "cryptography.x509")
    assert not audit._matches_prefix("cryptography.exceptions", "cryptography.x509")


def test_vulnerability_evidence_path_traversal_fails_closed(monkeypatch) -> None:
    document = json.loads(
        (ROOT / "control-plane/manifests/vulnerability-exceptions.json").read_text(
            encoding="utf-8"
        )
    )
    document["exceptions"][0]["evidence_paths"] = ["../outside.py"]
    monkeypatch.setattr(audit.json, "loads", lambda _value: document)

    with pytest.raises(audit.DependencyAuditError, match="unsafe vulnerability evidence"):
        audit.load_exceptions(ROOT, date(2026, 8, 25))


def test_mismatched_profile_versions_fail_closed(monkeypatch) -> None:
    def mismatched_locks(path: Path) -> dict[str, str]:
        version = "49.0.0" if path.name == "requirements-dev.lock" else "48.0.1"
        return {"cryptography": version}

    monkeypatch.setattr(audit, "_lock_versions", mismatched_locks)

    with pytest.raises(audit.DependencyAuditError, match="lock versions disagree"):
        audit.load_exceptions(ROOT, date(2026, 8, 25))


def test_dynamic_import_guard_cannot_be_bypassed(tmp_path: Path) -> None:
    literal = tmp_path / "literal.py"
    literal.write_text(
        'import importlib\nimportlib.import_module("PIL.Image")\n', encoding="utf-8"
    )
    assert "PIL.Image" in audit._import_names(literal)

    dynamic = tmp_path / "dynamic.py"
    dynamic.write_text(
        'import importlib\nmodule_name = "PIL.Image"\nimportlib.import_module(module_name)\n',
        encoding="utf-8",
    )
    with pytest.raises(audit.DependencyAuditError, match="dynamic module name"):
        audit._import_names(dynamic)
