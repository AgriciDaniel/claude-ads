"""Public documentation and repository-template consistency checks."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DASHES = (chr(0x2013), chr(0x2014))
OWNED_TEXT_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "install.sh",
    "install.ps1",
    "uninstall.sh",
    "uninstall.ps1",
    ".gitignore",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
)


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_owned_documents_use_no_em_or_en_dashes() -> None:
    for relative in OWNED_TEXT_FILES:
        text = _text(relative)
        assert not any(dash in text for dash in DASHES), relative


def test_contributing_matches_control_plane_publication_stance() -> None:
    contributing = _text("CONTRIBUTING.md")
    policy = _text("control-plane/PUBLISHING_POLICY.md")
    assert "remains private" not in contributing
    assert "existing MIT public distribution at `AgriciDaniel/claude-ads`" in contributing
    assert "existing MIT public distribution at\n`AgriciDaniel/claude-ads`" in policy
    assert "explicit approval" in contributing
    assert "PUBLISHING_POLICY.md" in contributing


def test_pull_request_template_matches_contributing_requirements() -> None:
    template = _text(".github/PULL_REQUEST_TEMPLATE.md")
    contributing = _text("CONTRIBUTING.md")
    assert "python scripts/release.py audit" in contributing
    assert "python -m pytest -q" in contributing
    assert "python scripts/release.py audit" in template
    assert "python -m pytest -q" in template
    assert "200 lines" not in template
    assert "500 lines" in template


def test_bug_report_collects_version_install_method_and_host() -> None:
    form = yaml.safe_load(_text(".github/ISSUE_TEMPLATE/bug_report.yml"))
    fields = {item["id"]: item for item in form["body"] if "id" in item}
    assert {"version", "install_method", "host"} <= set(fields)
    for identifier in ("version", "install_method", "host"):
        assert fields[identifier]["validations"]["required"] is True
    assert "OpenAI Codex CLI" in fields["host"]["attributes"]["options"]


def test_security_policy_is_accurate_about_pdf_paths_and_versions() -> None:
    security = _text("SECURITY.md")
    assert "v2.0.0" not in security
    assert "WeasyPrint" in security and "ReportLab" in security
    assert "weasyprint" in _text("claude_ads_core/reporting.py")
    assert "reportlab" in _text("scripts/generate_report.py")


def test_support_does_not_point_at_a_missing_readme_faq() -> None:
    support = _text("SUPPORT.md")
    readme = _text("README.md")
    assert "FAQ" not in support
    for heading in ("Quickstart", "Installation", "Commands"):
        assert re.search(rf"^## {heading}$", readme, flags=re.MULTILINE)
        assert heading in support


def test_readme_states_status_quickstart_and_experimental_hosts() -> None:
    readme = _text("README.md")
    assert "development candidate" in readme
    assert "control-plane/RELEASE_REQUIREMENTS.md" in readme
    assert "All twelve account-health scoring profiles are disabled" in readme
    assert "optional and not yet natively accepted" in readme
    quickstart = readme.split("## Quickstart", 1)[1].split("\n<p", 1)[0]
    for command in ("/ads setup", "/ads audit"):
        assert command in quickstart
    assert len(re.findall(r"^\d\. ", quickstart, flags=re.MULTILINE)) == 5
    install = readme.split("## Installation", 1)[1].split("## Architecture", 1)[0]
    assert "EXPERIMENTAL" in install
    for host in ("Codex", "Gemini", "Cursor", "Windsurf", "Goose"):
        assert host in install.split("EXPERIMENTAL", 1)[1][:400]
    assert "sha256sum -c SHA256SUMS" in install
    assert "checksummed, not signed" in install
    assert "signed release" not in readme.lower()


def test_status_claims_match_the_scoring_manifest() -> None:
    import json

    profiles = json.loads(_text("control-plane/manifests/scoring-profiles.json"))["profiles"]
    assert len(profiles) == 12
    assert {profile["status"] for profile in profiles} == {"disabled"}


def test_no_tracked_file_is_ignored() -> None:
    result = subprocess.run(
        ["git", "ls-files", "-ci", "--exclude-standard"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return  # Not a Git checkout (for example an extracted archive).
    assert result.stdout.strip() == ""
