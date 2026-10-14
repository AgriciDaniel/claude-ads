"""Current primary-source API changes remain accurately scoped and dated."""

from __future__ import annotations


def _text(repo_root, name):
    text = (repo_root / "ads/references" / name).read_text(encoding="utf-8")
    return " ".join(text.split())


def test_google_deprecations_preserve_existing_and_multichannel_behavior(repo_root):
    text = _text(repo_root, "google-audit.md")
    for fragment in (
        "Current API changes verified 2026-10-12",
        "2026-09-23",
        "Existing Smart Campaigns can continue serving",
        "2026-09-30",
        "Google Search portion of Performance Max",
        "still apply to other channels",
    ):
        assert fragment in text


def test_microsoft_guidance_does_not_call_soap_already_unsupported(repo_root):
    text = _text(repo_root, "microsoft-audit.md")
    assert "through 2027-01-31" in text
    assert "do not report SOAP as unsupported or REST-only before the deadline" in text


def test_reddit_guidance_distinguishes_active_and_future_contracts(repo_root):
    text = _text(repo_root, "reddit-audit.md")
    for fragment in (
        "2026-09-30",
        "410 Gone",
        "existing ads using onsite forms are paused",
        "2026-09-23",
        "enhancements.user_generated_content.enroll_status",
        "2026-12-08",
        "unsupported breakdown combinations",
        "2026-09-21",
        "use_catalog",
        "more than seven",
        "not an already-active response contract",
    ):
        assert fragment in text


def test_linkedin_guidance_marks_202510_sunset_as_imminent(repo_root):
    text = _text(repo_root, "linkedin-audit.md")
    assert "`202510`" in text
    assert "2026-10-15" in text
    assert "Do not report" in text
    assert "already removed before the effective date" in text


def test_linkedin_guidance_names_current_default_version_and_later_sunset(repo_root):
    text = _text(repo_root, "linkedin-audit.md")
    for fragment in ("`202609`", "`202511`", "2026-11-16", "legacy Geo", "2026-08-31"):
        assert fragment in text


def test_google_developer_token_and_migration_notes_are_scoped(repo_root):
    text = _text(repo_root, "google-audit.md")
    for fragment in (
        "Developer tokens were sunset on 2026-09-09",
        "optional and ignored",
        "CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION",
        "GeneratePMaxDraftCampaign",
        "cite September 2026",
        "February 2027",
    ):
        assert fragment in text
    assert "developer token is required" not in text.lower()


def test_apple_and_meta_guidance_carry_dated_lifecycle_notes(repo_root):
    apple = _text(repo_root, "apple-audit.md")
    assert "2027-01-26" in apple
    assert "Apple Ads Platform API" in apple
    meta = _text(repo_root, "meta-audit.md")
    for fragment in ("`v26.0`", "2026-07-29", "2026-10-27", "`v24.0`", "advantage_audience"):
        assert fragment in meta
