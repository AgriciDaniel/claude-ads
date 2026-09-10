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
    records, scope = audit.load_exceptions(ROOT, date(2026, 9, 10))
    assert len(records) == 17
    assert scope == ["claude_ads_core", "evals", "scripts"]
    summary = audit.evaluate_reports(_reports(records), records)
    assert summary == {
        "status": "pass",
        "profiles": ["development", "runtime", "schema-tests"],
        "not_affected_advisory_count": 17,
        "vulnerable_package_count": 3,
        "unhandled_advisory_count": 0,
    }


def test_unhandled_advisory_fails_closed() -> None:
    records, _ = audit.load_exceptions(ROOT, date(2026, 9, 10))
    reports = _reports(records)
    reports["runtime"]["dependencies"].append(
        {"name": "example", "version": "1.0", "vulns": [{"id": "PYSEC-2099-1"}]}
    )
    with pytest.raises(audit.DependencyAuditError, match="unhandled dependency vulnerabilities"):
        audit.evaluate_reports(reports, records)


def test_stale_exception_document_fails_closed() -> None:
    with pytest.raises(audit.DependencyAuditError, match="stale or future-dated"):
        audit.load_exceptions(ROOT, date(2026, 10, 11))


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
        audit.load_exceptions(ROOT, date(2026, 9, 10))


def _document() -> dict:
    return json.loads(
        (ROOT / "control-plane/manifests/vulnerability-exceptions.json").read_text(
            encoding="utf-8"
        )
    )


def test_exception_for_unreviewed_package_fails_closed(monkeypatch) -> None:
    document = _document()
    document["exceptions"][0]["package"] = "requests"
    monkeypatch.setattr(audit.json, "loads", lambda _value: document)

    with pytest.raises(audit.DependencyAuditError, match="invalid vulnerability exception ID"):
        audit.load_exceptions(ROOT, date(2026, 9, 10))


def test_exception_without_any_guard_fails_closed(monkeypatch) -> None:
    document = _document()
    document["exceptions"][0]["forbidden_import_prefixes"] = []
    document["exceptions"][0].pop("forbidden_call_keywords", None)
    monkeypatch.setattr(audit.json, "loads", lambda _value: document)

    with pytest.raises(audit.DependencyAuditError, match="lacks import guards"):
        audit.load_exceptions(ROOT, date(2026, 9, 10))


def test_weasyprint_exception_is_guarded_by_call_keywords() -> None:
    records, _ = audit.load_exceptions(ROOT, date(2026, 9, 10))
    record = records["PYSEC-2026-3940"]
    assert record.package == "weasyprint"
    assert record.forbidden_import_prefixes == ()
    assert record.forbidden_call_keywords == (
        "write_pdf:stylesheets",
        "render:stylesheets",
        "write_pdf:xmp_metadata",
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("doc.write_pdf(stylesheets=[sheet])\n", "write_pdf:stylesheets"),
        ("write_pdf(xmp_metadata=[url])\n", "write_pdf:xmp_metadata"),
        ("HTML(string=s).write_pdf(**options)\n", "write_pdf:**"),
        ("HTML(string=s).render(stylesheets=[sheet]).write_pdf()\n", "render:stylesheets"),
        ("pdf = html.write_pdf\npdf(stylesheets=[sheet])\n", "pdf:stylesheets"),
        ('getattr(html, "write_pdf")(stylesheets=[sheet])\n', "?:stylesheets"),
        ("functools.partial(html.write_pdf, stylesheets=[sheet])\n", "partial:stylesheets"),
        ('fns["w"](stylesheets=[sheet])\n', "?:stylesheets"),
        ("html.write_pdf.__call__(xmp_metadata=[url])\n", "__call__:xmp_metadata"),
        ("factory()(**options)\n", "?:**"),
    ],
)
def test_call_keyword_guard_detects_guarded_arguments(
    tmp_path: Path, source: str, expected: str
) -> None:
    observed = audit._call_keywords(_source(tmp_path, "calls.py", source))
    assert expected in observed
    assert any(
        audit._matches_call_keyword(call, "write_pdf:stylesheets")
        or audit._matches_call_keyword(call, "write_pdf:xmp_metadata")
        for call in observed
    )


def test_call_keyword_guard_ignores_unguarded_calls(tmp_path: Path) -> None:
    observed = audit._call_keywords(
        _source(
            tmp_path,
            "safe.py",
            "HTML(string=s, base_url=None).write_pdf()\nrender(base_url=None)\nlog(**fields)\n",
        )
    )
    assert not any(audit._matches_call_keyword(call, "write_pdf:stylesheets") for call in observed)


def test_mismatched_profile_versions_fail_closed(monkeypatch) -> None:
    def mismatched_locks(path: Path) -> dict[str, str]:
        version = "49.0.0" if path.name == "requirements-dev.lock" else "48.0.1"
        return {"cryptography": version}

    monkeypatch.setattr(audit, "_lock_versions", mismatched_locks)

    with pytest.raises(audit.DependencyAuditError, match="lock versions disagree"):
        audit.load_exceptions(ROOT, date(2026, 9, 10))


def _source(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "source",
    [
        'import importlib\nimportlib.import_module("PIL.Image")\n',
        'import importlib.util\nimportlib.import_module("PIL.Image")\n',
        'import importlib as il\nil.import_module("PIL.Image")\n',
        'from importlib import import_module\nimport_module("PIL.Image")\n',
        'from importlib import import_module as load\nload("PIL.Image")\n',
        'from importlib import *\nimport_module("PIL.Image")\n',
        'import importlib\nim = importlib.import_module\nim("PIL.Image")\n',
        'import importlib\nload = im = importlib.import_module\nload("PIL.Image")\n',
        'import importlib as il\nim = il.import_module\nload = im\nload("PIL.Image")\n',
        'import importlib\nil = importlib\nil.import_module("PIL.Image")\n',
        'import importlib\nimportlib.__import__("PIL.Image")\n',
        'import importlib\nimportlib.import_module(name="PIL.Image")\n',
        'import importlib\nimportlib.import_module(".Image", "PIL")\n',
        'import importlib\nimportlib.import_module(".Image", package="PIL")\n',
        '__import__("PIL.Image")\n',
        '__builtins__.__import__("PIL.Image")\n',
        'import builtins\nbuiltins.__import__("PIL.Image")\n',
        'import builtins as b\nb.__import__("PIL.Image")\n',
        'from builtins import __import__ as imp\nimp("PIL.Image")\n',
        'import builtins\nimp = builtins.__import__\nimp("PIL.Image")\n',
        'import builtins\ngetattr(builtins, "__import__")("PIL.Image")\n',
        'import builtins\nbuiltins["__import__"]("PIL.Image")\n',
        'def load():\n    import importlib\n    return importlib.import_module("PIL.Image")\n',
    ],
)
def test_dynamic_import_guard_cannot_be_bypassed(tmp_path: Path, source: str) -> None:
    names = audit._import_names(_source(tmp_path, "literal.py", source))
    assert "PIL.Image" in names
    assert any(audit._matches_prefix(name, "PIL") for name in names)


@pytest.mark.parametrize(
    "source",
    [
        'import importlib\nmodule_name = "PIL.Image"\nimportlib.import_module(module_name)\n',
        'from importlib import import_module\nname = "PIL.Image"\nimport_module(name)\n',
        'from importlib import import_module as load\nload("PIL" + ".Image")\n',
        'import importlib\nim = importlib.import_module\nim(f"{prefix}.Image")\n',
        'import importlib\nim = importlib.import_module\nload = im\nload(name)\n',
        'name = "PIL.Image"\n__import__(name)\n',
        'import builtins\nname = "PIL.Image"\nbuiltins.__import__(name)\n',
        '__builtins__.__import__(name)\n',
        'from builtins import __import__ as imp\nimp(name)\n',
        'import importlib\nimportlib.import_module(*["PIL.Image"])\n',
        'import importlib\nimportlib.import_module(**{"name": "PIL.Image"})\n',
        'import importlib\nimportlib.import_module(".Image", package)\n',
        'import importlib\nimportlib.import_module("Image", None, None, [], 1)\n',
        'import importlib\nlist(map(importlib.import_module, ["PIL.Image"]))\n',
        'import importlib\nloaders = [importlib.import_module]\nloaders[0]("PIL.Image")\n',
        'import importlib\nattr = "import_module"\ngetattr(importlib, attr)("PIL.Image")\n',
        'import builtins\nattr = "__import__"\nbuiltins[attr]("PIL.Image")\n',
        'loader = __import__\nloader(name)\n',
    ],
)
def test_dynamic_import_guard_flags_unresolvable_dynamic_imports(
    tmp_path: Path, source: str
) -> None:
    with pytest.raises(audit.DependencyAuditError, match="unresolvable dynamic import"):
        audit._import_names(_source(tmp_path, "dynamic.py", source))


def test_dynamic_import_guard_ignores_unrelated_importlib_usage(tmp_path: Path) -> None:
    source = (
        "import importlib.util\n"
        "from importlib import metadata\n"
        "spec = importlib.util.spec_from_file_location(name, path)\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "version = metadata.version(package)\n"
    )
    names = audit._import_names(_source(tmp_path, "unrelated.py", source))
    assert names == {"importlib.util", "importlib", "importlib.metadata"}


@pytest.mark.parametrize("source", [
    'import importlib\nil = importlib.import_module("importlib")\nil.import_module("PIL.Image")\n',
    'b = __import__("builtins")\nb.__import__("PIL.Image")\n',
    'import importlib\nimportlib.import_module("importlib").import_module("PIL.Image")\n',
])
def test_returned_importer_module_cannot_hide_prohibited_import(tmp_path, source):
    names = audit._import_names(_source(tmp_path, "importer.py", source))
    assert any(audit._matches_prefix(name, "PIL") for name in names)


@pytest.mark.parametrize("source", [
    'writer = html.write_pdf\nwriter(**options)\n',
    'writer = html.write_pdf\nsecond = writer\nsecond(**options)\n',
    'writer: object = html.write_pdf\nwriter(**options)\n',
    'writer = html.write_pdf\nwriter = safe_writer\nwriter(**options)\n',
    'writer = other\nother = writer\nwriter(**options)\n',
    'from library import write_pdf\ndef unrelated():\n    write_pdf = safe_writer\nwrite_pdf(**options)\n',
])
def test_forwarded_mapping_cannot_hide_guarded_callable(tmp_path, source):
    calls = audit._call_keywords(_source(tmp_path, "alias.py", source))
    assert any(audit._matches_call_keyword(call, "write_pdf:xmp_metadata") for call in calls)
