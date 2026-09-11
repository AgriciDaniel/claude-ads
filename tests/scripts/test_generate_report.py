"""Security regressions for the legacy ReportLab renderer."""

from __future__ import annotations

import base64
import html
from pathlib import Path
import sys

import pytest


pytest.importorskip("reportlab")
pytest.importorskip("matplotlib")

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_report  # noqa: E402


# Distinct payloads per value so the assertions can tell which route leaked.
IMG_ATTACK = "<img src='file:///private/sentinel.png'>"
GRADE_ATTACK = "<font color='red'>INJECTED</font>"
SCORE_ATTACK = "<img src='file:///private/score.png'>"
ESCAPED_IMG = html.escape(IMG_ATTACK, quote=True)

# 1x1 white PNG so the chart routes can be exercised without matplotlib output.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _malicious_text() -> str:
    return f"{IMG_ATTACK} **verified bold**"


def _report(**overrides) -> dict:
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
    data.update(overrides)
    return data


def _assert_no_raw_markup(paragraphs: list[str]) -> None:
    leaked = [text for text in paragraphs if "<img" in text or "<font color" in text]
    assert leaked == []


@pytest.fixture
def rendered(monkeypatch, tmp_path: Path):
    """Build a PDF while recording every Paragraph text and Table cell given to ReportLab."""
    paragraphs: list[str] = []
    cells: list[object] = []
    original_paragraph = generate_report.Paragraph
    original_table = generate_report.Table

    def inspect_paragraph(text, *args, **kwargs):
        paragraphs.append(str(text))
        return original_paragraph(text, *args, **kwargs)

    def inspect_table(rows, *args, **kwargs):
        cells.extend(cell for row in rows for cell in row)
        return original_table(rows, *args, **kwargs)

    monkeypatch.setattr(generate_report, "Paragraph", inspect_paragraph)
    monkeypatch.setattr(generate_report, "Table", inspect_table)
    monkeypatch.setattr(
        generate_report, "build_result_distribution_chart", lambda *_args: None
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(tmp_path))
    counter = {"png": 0}

    def png_factory(enabled: bool):
        def build_chart(*_args):
            if not enabled:
                return None
            counter["png"] += 1
            path = tmp_path / f"chart-{counter['png']}.png"
            path.write_bytes(_PNG)
            return str(path)

        return build_chart

    def build(data: dict, *, gauge: bool, platform: bool, brand: str = ""):
        monkeypatch.setattr(generate_report, "build_gauge_chart", png_factory(gauge))
        monkeypatch.setattr(generate_report, "build_platform_chart", png_factory(platform))
        output = tmp_path / "report.pdf"
        generate_report.build_pdf(data, str(output), brand)
        assert output.is_file()
        return paragraphs, cells

    return build


def test_markdown_conversion_escapes_reportlab_markup_before_formatting() -> None:
    converted = generate_report._md_to_html(_malicious_text())

    assert "<img" not in converted
    assert ESCAPED_IMG in converted
    assert "<b>verified bold</b>" in converted


def test_pdf_builder_escapes_every_body_paragraph_route(rendered) -> None:
    paragraphs, _cells = rendered(
        _report(), gauge=False, platform=False, brand=_malicious_text()
    )

    _assert_no_raw_markup(paragraphs)
    # One escaped copy per route: brand title, critical issue, quick win,
    # section title, subtitle, bullet, text, table header, table cell.
    assert sum(ESCAPED_IMG in text for text in paragraphs) == 9


@pytest.mark.parametrize(
    ("gauge", "platform", "suffix"),
    [
        (True, True, "  |  Fig 2: Platform Score Comparison"),
        (True, False, ""),
    ],
)
def test_health_caption_routes_escape_score_and_grade(
    rendered, gauge: bool, platform: bool, suffix: str
) -> None:
    paragraphs, _cells = rendered(
        _report(
            health_score=SCORE_ATTACK,
            grade=GRADE_ATTACK,
            platform_scores={"Google": 70},
        ),
        gauge=gauge,
        platform=platform,
    )

    captions = [text for text in paragraphs if text.startswith("Fig 1:")]
    expected = (
        f"Fig 1: Health Score {html.escape(SCORE_ATTACK, quote=True)}/100 "
        f"(Grade {html.escape(GRADE_ATTACK, quote=True)}){suffix}"
    )
    assert captions == [expected]
    _assert_no_raw_markup(paragraphs)


def test_health_score_fallback_table_uses_literal_cells(rendered) -> None:
    paragraphs, cells = rendered(
        _report(health_score=SCORE_ATTACK, grade=GRADE_ATTACK),
        gauge=False,
        platform=False,
    )

    # ReportLab draws plain string cells literally, so the fallback score table
    # must keep raw strings rather than Paragraphs with unescaped markup.
    literal_cells = [cell for cell in cells if isinstance(cell, str)]
    assert f"{SCORE_ATTACK}/100" in literal_cells
    assert f"Grade: {GRADE_ATTACK}" in literal_cells
    assert not [text for text in paragraphs if text.startswith("Fig 1:")]
    _assert_no_raw_markup(paragraphs)
