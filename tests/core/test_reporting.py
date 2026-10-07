from __future__ import annotations

import copy
import inspect
import json
import os
import stat
import tomllib
from pathlib import Path

import pytest

import claude_ads_core as public_api
from claude_ads_core.cli import main
from claude_ads_core.contracts import validate_contract
from claude_ads_core.reporting import (
    PDFDependencyError,
    ReportRenderError,
    _render_html_layout,
    _render_markdown_layout,
    _render_pdf_layout,
    atomic_write_report,
    render_html,
    render_markdown,
    render_pdf,
    render_report,
    resolve_report_path,
    write_report_bundle,
)
from tests.core.test_contracts import registry_report_bundle, synthetic_report_registry


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "reports"
BUNDLE_PATH = FIXTURE_ROOT / "sanitized-report-bundle.json"
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_bundle() -> dict:
    return json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))


def test_product_manifest_advertises_only_executable_report_formats():
    manifest = json.loads(
        (REPO_ROOT / "control-plane" / "manifests" / "product-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["human_renderers"] == ["markdown", "html", "pdf"]
    for output_format in manifest["human_renderers"]:
        assert output_format in {"markdown", "html", "pdf"}

    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert any(
        requirement.startswith("weasyprint>=")
        for requirement in project["project"]["optional-dependencies"]["pdf"]
    )


def test_sanitized_report_fixture_is_a_valid_bundle():
    validate_contract("report-bundle", load_bundle())


def test_markdown_matches_golden_report():
    bundle = load_bundle()
    expected = (FIXTURE_ROOT / "sanitized-report.md").read_text(encoding="utf-8").rstrip("\n") + "\n"
    assert _render_markdown_layout(bundle) == expected


def test_html_matches_golden_report_and_is_self_contained():
    bundle = load_bundle()
    expected = (FIXTURE_ROOT / "sanitized-report.html").read_text(encoding="utf-8").rstrip("\n") + "\n"
    rendered = _render_html_layout(bundle)
    assert rendered == expected
    lowered = rendered.lower()
    assert "<script" not in lowered
    assert "<link" not in lowered
    assert " src=" not in lowered
    assert " url(" not in lowered


def test_rendering_is_reproducible_and_does_not_mutate_input():
    bundle = load_bundle()
    original = copy.deepcopy(bundle)
    assert _render_markdown_layout(bundle) == _render_markdown_layout(bundle)
    assert _render_html_layout(bundle) == _render_html_layout(bundle)
    assert bundle == original


def test_report_surfaces_partial_provisional_evidence_contradictions_and_actions():
    bundle = load_bundle()
    markdown = _render_markdown_layout(bundle)
    assert "Run completeness: **Partial**" in markdown
    assert "Evidence status: **Provisional**" in markdown
    assert "must not be presented as a complete audit" in markdown
    assert "Campaign eligibility is present" in markdown
    assert "Verify and repair the primary conversion action" in markdown
    assert '{"field":"primary_conversion_status","value":"inactive"}' in markdown


def test_insufficient_evidence_is_visible_and_health_is_not_invented():
    bundle = load_bundle()
    for finding in bundle["findings"]:
        finding.update(status="unknown", evidence=[], confidence="none")
    registry = synthetic_report_registry(bundle)
    bundle["scoring"] = registry.score_platform("google", bundle["findings"]).to_dict()
    markdown = _render_markdown_layout(bundle)
    html = _render_html_layout(bundle)
    assert "Evidence status: **Insufficient evidence**" in markdown
    assert "Health score: **Not scored**" in markdown
    assert "Evidence is insufficient for a defensible health score" in markdown
    assert "Evidence status: Insufficient evidence" in html
    assert "Health score<strong>Not scored</strong>" in html


def test_untrusted_content_is_escaped_and_obvious_credentials_and_pii_are_redacted():
    bundle = load_bundle()
    finding = bundle["findings"][0]
    finding["observation"] = (
        "Contact analyst@example.test with access_token=secret-value "
        "and <script>alert('untrusted')</script>."
    )
    finding["evidence"].append(
        {"authorization": "Bearer credential-value", "nested": {"email": "person@example.test"}}
    )
    markdown = _render_markdown_layout(bundle)
    rendered_html = _render_html_layout(bundle)
    combined = markdown + rendered_html
    assert "analyst@example.test" not in combined
    assert "person@example.test" not in combined
    assert "secret-value" not in combined
    assert "credential-value" not in combined
    assert "<script>" not in rendered_html
    assert "&lt;script&gt;" in rendered_html
    assert "[REDACTED]" in combined


def test_renderer_rejects_invalid_bundle_and_malformed_extensions():
    invalid = load_bundle()
    invalid["schema_version"] = "2.0.0"
    with pytest.raises(ReportRenderError, match="invalid report bundle"):
        render_markdown(invalid, policy_root=REPO_ROOT)

    invalid = load_bundle()
    invalid["actions"] = {"action": "not an array"}
    with pytest.raises(ReportRenderError, match=r"\$\.actions"):
        render_html(invalid, policy_root=REPO_ROOT)


@pytest.mark.parametrize("destination", ["../outside.md", "/tmp/outside.md", "nested/../../outside.md"])
def test_safe_report_path_rejects_absolute_and_traversal_paths(tmp_path, destination):
    with pytest.raises(ReportRenderError, match="relative path"):
        resolve_report_path(tmp_path / "reports", destination)


def test_safe_report_path_rejects_parent_and_destination_symlinks(tmp_path):
    root = tmp_path / "reports"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "linked").symlink_to(outside, target_is_directory=True)
        (root / "report.md").symlink_to(outside / "report.md")
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ReportRenderError, match="parent must not be a symlink"):
        resolve_report_path(root, "linked/report.md")
    with pytest.raises(ReportRenderError, match="output must not be a symlink"):
        resolve_report_path(root, "report.md")


def test_atomic_report_write_uses_private_permissions_and_leaves_no_temp_file(tmp_path):
    output = atomic_write_report(tmp_path / "reports", "run-1/report.md", "report\n")
    assert output.read_text(encoding="utf-8") == "report\n"
    if os.name != "nt":
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert list(output.parent.glob(".report.md.*")) == []


def test_pdf_bridge_fails_clearly_when_optional_dependency_is_unavailable(monkeypatch):
    def unavailable(name: str):
        raise ImportError(name)

    monkeypatch.setattr("claude_ads_core.reporting.importlib.import_module", unavailable)
    bundle = registry_report_bundle(REPO_ROOT)
    with pytest.raises(PDFDependencyError, match="optional 'weasyprint'"):
        render_pdf(bundle, policy_root=REPO_ROOT)


def test_real_pdf_render_smoke_when_runtime_dependencies_are_installed():
    pytest.importorskip("weasyprint")
    bundle = load_bundle()
    rendered = _render_pdf_layout(bundle)
    assert rendered.startswith(b"%PDF-")
    assert len(rendered) > 1_000


def test_cli_render_writes_policy_validated_report_under_safe_root(
    tmp_path, capsys, repo_root: Path
):
    root = tmp_path / "runs"
    bundle = registry_report_bundle(repo_root)
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    assert (
        main(
            [
                "render",
                str(bundle_path),
                "--format",
                "html",
                "--root",
                str(root),
                "--policy-root",
                str(repo_root),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    output = root / "run-20260711-001" / "report.html"
    assert result == {
        "format": "html",
        "path": str(output),
        "run_id": "run-20260711-001",
        "status": "rendered",
    }
    assert output.read_text(encoding="utf-8") == render_html(bundle, policy_root=repo_root)


def test_cli_render_returns_machine_readable_error_for_unsafe_output(
    tmp_path, capsys, repo_root: Path
):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(registry_report_bundle(repo_root)), encoding="utf-8")
    assert (
        main(
            [
                "report",
                str(bundle_path),
                "--root",
                str(tmp_path / "runs"),
                "--policy-root",
                str(repo_root),
                "--output",
                "../outside.md",
            ]
        )
        == 2
    )
    result = json.loads(capsys.readouterr().err)
    assert result["status"] == "invalid"
    assert "relative path" in result["error"]


def test_exported_render_markdown_rejects_forged_health_by_default(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["scoring"].update(
        health_score=100.0,
        evidence_coverage=100.0,
        status="normal",
    )
    with pytest.raises(ReportRenderError, match="report policy validation failed"):
        public_api.render_markdown(bundle)


@pytest.mark.parametrize(
    "operation",
    [
        lambda bundle, root, output: public_api.render_markdown(bundle, policy_root=root),
        lambda bundle, root, output: public_api.render_html(bundle, policy_root=root),
        lambda bundle, root, output: public_api.render_pdf(bundle, policy_root=root),
        lambda bundle, root, output: public_api.render_report(
            bundle, "markdown", policy_root=root
        ),
        lambda bundle, root, output: public_api.write_report_bundle(
            bundle,
            "markdown",
            output,
            "run/report.md",
            policy_root=root,
        ),
    ],
)
def test_every_exported_high_level_report_api_rejects_forged_health(
    tmp_path: Path, repo_root: Path, operation
):
    bundle = registry_report_bundle(repo_root)
    bundle["scoring"].update(
        health_score=100.0,
        evidence_coverage=100.0,
        status="normal",
    )
    with pytest.raises(ReportRenderError, match="report policy validation failed"):
        operation(bundle, repo_root, tmp_path / "reports")


def test_public_report_apis_reject_injected_registry_and_spoofed_health(
    tmp_path: Path, repo_root: Path
):
    bundle = registry_report_bundle(repo_root)
    for finding in bundle["findings"]:
        finding.update(status="pass", evidence=[{"caller": "forged"}], confidence="high")
    for control in bundle["control_definitions"]:
        control.update(scoring_behavior="health", stability="stable", severity="high")
    entries = tuple(
        public_api.RegistryEntry(
            platform="google",
            control_id=control["control_id"],
            intent="caller selected",
            disposition="health",
            source_claim_ids=(),
            control_definition=control,
        )
        for control in bundle["control_definitions"]
    )
    category = entries[0].control_definition["category"]
    profile = public_api.ScoringProfile(
        profile_id="google-caller-selected-v1",
        platform="google",
        status="enabled",
        category_weights={category: 100.0},
        health_control_ids=tuple(entry.control_id for entry in entries),
        disabled_reason=None,
    )
    spoofed_registry = public_api.ControlRegistry(entries=entries, profiles=(profile,))
    bundle["scoring"] = spoofed_registry.score_platform("google", bundle["findings"]).to_dict()
    assert bundle["scoring"]["health_score"] == 100.0

    operations = (
        lambda **kwargs: public_api.render_markdown(bundle, **kwargs),
        lambda **kwargs: public_api.render_html(bundle, **kwargs),
        lambda **kwargs: public_api.render_pdf(bundle, **kwargs),
        lambda **kwargs: public_api.render_report(bundle, "markdown", **kwargs),
        lambda **kwargs: public_api.write_report_bundle(
            bundle, "markdown", tmp_path / "reports", "run/report.md", **kwargs
        ),
    )
    for public_function in (
        public_api.render_markdown,
        public_api.render_html,
        public_api.render_pdf,
        public_api.render_report,
        public_api.write_report_bundle,
    ):
        assert "registry" not in inspect.signature(public_function).parameters
    for operation in operations:
        with pytest.raises(TypeError, match="registry"):
            operation(registry=spoofed_registry)
        with pytest.raises(ReportRenderError, match="report policy validation failed"):
            operation(policy_root=repo_root)
