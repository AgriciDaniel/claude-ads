"""Landing analysis failures must not be reported as completed audits."""

import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
pytest.importorskip("playwright.sync_api")
import analyze_landing


@pytest.mark.parametrize("json_output", [False, True])
def test_cli_exits_nonzero_without_grades_when_analysis_is_blocked(json_output):
    command = [sys.executable, str(SCRIPTS_DIR / "analyze_landing.py"), "https://example.com"]
    if json_output:
        command.append("--json")
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)

    assert result.returncode == 1
    if json_output:
        output = json.loads(result.stdout)
        assert "egress-sandbox attestation" in output["error"]
        assert output["grades"] == {}
    else:
        assert "egress-sandbox attestation" in result.stderr
        assert result.stdout == ""


@pytest.mark.parametrize("error", ["Page load timed out", "Browser closed"])
def test_failed_analysis_is_not_graded(error):
    assert analyze_landing.grade_landing({"error": error}) == {}


def test_successful_analysis_is_still_graded():
    result = {
        "error": None,
        "performance": {"lcp_ms": 2000},
        "content": {"h1": "Example"},
        "schema": {"product_schema": True},
        "conversion": {"cta_above_fold": True, "form_present": False},
        "mobile": {"viewport_meta": True, "horizontal_scroll": False},
    }

    assert analyze_landing.grade_landing(result) == {
        "G59_mobile_speed": "PASS",
        "G60_relevance": "PASS",
        "G61_schema": "PASS",
        "cta_above_fold": "PASS",
        "mobile_responsive": "PASS",
    }
