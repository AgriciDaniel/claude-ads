"""Security regressions for the legacy ReportLab renderer."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


pytest.importorskip("reportlab")
pytest.importorskip("matplotlib")

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_report  # noqa: E402


def _malicious_text() -> str:
    return "<img src='file:///private/sentinel.png'> **verified bold**"


def test_markdown_conversion_escapes_reportlab_markup_before_formatting() -> None:
    converted = generate_report._md_to_html(_malicious_text())

    assert "<img" not in converted
    assert "&lt;img src=&#x27;file:///private/sentinel.png&#x27;&gt;" in converted
    assert "<b>verified bold</b>" in converted


def test_pdf_builder_escapes_every_user_controlled_paragraph_route(
    monkeypatch, tmp_path: Path
) -> None:
    observed: list[str] = []
    original_paragraph = generate_report.Paragraph

    def inspect_paragraph(text, *args, **kwargs):
        observed.append(str(text))
        return original_paragraph(text, *args, **kwargs)

    monkeypatch.setattr(generate_report, "Paragraph", inspect_paragraph)
    monkeypatch.setattr(generate_report, "build_gauge_chart", lambda *_args: None)
    monkeypatch.setattr(generate_report, "build_platform_chart", lambda *_args: None)
    monkeypatch.setattr(
        generate_report, "build_result_distribution_chart", lambda *_args: None
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(tmp_path))
    attack = _malicious_text()
    data = {
        "title": attack,
        "health_score": None,
        "grade": "",
        "platform_scores": {},
        "critical_issues": [attack],
        "quick_wins": [attack],
        "sections": [
            {
                "title": attack,
                "items": [
                    {"type": "subtitle", "text": attack},
                    {"type": "bullet", "text": attack},
                    {"type": "text", "text": attack},
                    {"type": "table", "headers": [attack], "rows": [[attack]]},
                ],
            }
        ],
        "tables": [],
        "result_counts": {"Pass": 0, "Warning": 0, "Fail": 0},
    }

    output = tmp_path / "report.pdf"
    generate_report.build_pdf(data, str(output), attack)

    assert output.is_file()
    assert observed
    assert all("<img" not in text for text in observed)
    assert any("&lt;img" in text for text in observed)
