"""Fail-closed behavior for the landing-page analysis CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


pytest.importorskip("playwright.sync_api")

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import analyze_landing as analyze_landing_module  # noqa: E402


def _successful_result() -> dict:
    return {
        "url": "https://example.com/landing",
        "performance": {
            "lcp_ms": 1800,
            "cls": 0.02,
            "ttfb_ms": 120,
            "dom_content_loaded_ms": 450,
        },
        "content": {
            "title": "Example landing page",
            "h1": "A verified headline",
            "meta_description": "A verified description",
            "word_count": 250,
        },
        "conversion": {
            "cta_above_fold": True,
            "form_present": False,
            "form_fields": 0,
            "phone_number": False,
            "chat_widget": False,
        },
        "trust": {
            "testimonials": False,
            "trust_badges": False,
            "reviews_schema": False,
        },
        "mobile": {
            "viewport_meta": True,
            "horizontal_scroll": False,
            "font_readable": True,
        },
        "schema": {
            "types_found": ["Service"],
            "product_schema": False,
            "faq_schema": False,
            "service_schema": True,
        },
        "error": None,
        "egress_attestation": {"attestation_id": "attestation:test"},
    }


@pytest.mark.parametrize(
    ("exception_factory", "expected_error"),
    [
        (
            lambda: analyze_landing_module.PlaywrightTimeout("navigation timed out"),
            "Page load timed out after 17000ms",
        ),
        (lambda: ValueError("blocked redirect"), "blocked redirect"),
        (lambda: RuntimeError("browser process exited"), "browser process exited"),
    ],
)
def test_analysis_converts_acquisition_exceptions_to_errors(
    monkeypatch,
    exception_factory,
    expected_error,
):
    exception = exception_factory()

    def fail_launch(**_kwargs):
        raise exception

    class PlaywrightContext:
        def __enter__(self):
            return SimpleNamespace(
                chromium=SimpleNamespace(launch=fail_launch),
            )

        def __exit__(self, *_args):
            return False

    attestation = SimpleNamespace(
        audit_reference=lambda: {"attestation_id": "attestation:test"},
    )
    monkeypatch.setattr(
        analyze_landing_module,
        "validate_browser_url",
        lambda url, **_kwargs: url,
    )
    monkeypatch.setattr(
        analyze_landing_module,
        "sync_playwright",
        PlaywrightContext,
    )

    result = analyze_landing_module.analyze_landing(
        "https://example.com/landing",
        timeout=17000,
        egress_attestation=attestation,
    )

    assert result["error"] == expected_error


@pytest.mark.parametrize(
    "error",
    [
        "Page load timed out after 30000ms",
        "verified egress-sandbox attestation document is required",
        "browser process exited unexpectedly",
    ],
)
@pytest.mark.parametrize("json_output", [False, True])
def test_cli_does_not_grade_or_report_success_after_analysis_error(
    monkeypatch,
    capsys,
    error,
    json_output,
):
    failed_result = _successful_result()
    failed_result["error"] = error
    monkeypatch.setattr(
        analyze_landing_module,
        "analyze_landing",
        lambda *args, **kwargs: failed_result,
    )

    def reject_grading(_result):
        raise AssertionError("failed analysis must not be graded")

    monkeypatch.setattr(analyze_landing_module, "grade_landing", reject_grading)
    args = ["https://example.com/landing"]
    if json_output:
        args.append("--json")

    exit_code = analyze_landing_module.main(args)
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err == f"Error: {error}\n"
    assert "Audit Grades" not in captured.out
    if json_output:
        payload = json.loads(captured.out)
        assert payload["error"] == error
        assert "grades" not in payload
    else:
        assert captured.out == ""


@pytest.mark.parametrize("json_output", [False, True])
def test_cli_rejects_invalid_attestation_before_analysis(
    monkeypatch,
    capsys,
    json_output,
):
    def reject_attestation(_path):
        raise ValueError("attestation authentication failed")

    def reject_analysis(*_args, **_kwargs):
        raise AssertionError("analysis must not run with an invalid attestation")

    monkeypatch.setattr(
        analyze_landing_module,
        "load_egress_sandbox_attestation",
        reject_attestation,
    )
    monkeypatch.setattr(
        analyze_landing_module,
        "analyze_landing",
        reject_analysis,
    )
    args = [
        "https://example.com/landing",
        "--egress-attestation",
        "invalid-attestation.json",
    ]
    if json_output:
        args.append("--json")

    exit_code = analyze_landing_module.main(args)
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Error: attestation authentication failed\n"


def test_grade_landing_rejects_failed_analysis():
    failed_result = _successful_result()
    failed_result["error"] = "page was not fetched"

    with pytest.raises(ValueError, match="cannot grade a failed landing-page analysis"):
        analyze_landing_module.grade_landing(failed_result)


def test_cli_preserves_successful_json_audit(monkeypatch, capsys):
    monkeypatch.setattr(
        analyze_landing_module,
        "analyze_landing",
        lambda *args, **kwargs: _successful_result(),
    )

    exit_code = analyze_landing_module.main(["https://example.com/landing", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert payload["error"] is None
    assert payload["grades"] == {
        "G59_mobile_speed": "PASS",
        "G60_relevance": "PASS",
        "G61_schema": "PASS",
        "cta_above_fold": "PASS",
        "mobile_responsive": "PASS",
    }
