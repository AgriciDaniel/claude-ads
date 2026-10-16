from __future__ import annotations

from pathlib import Path

import pytest

from claude_ads_core.adapters import GenericCSVExportAdapter, NativeCSVExportAdapter
from claude_ads_core.contracts import PLATFORMS, validate_contract
from claude_ads_core.control_registry import load_control_registry
from claude_ads_core.reporting import _render_html_layout, _render_markdown_layout


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

PLATFORM_CONTEXTS = {
    "google": {},
    "meta": {"currency": "USD"},
    "youtube": {},
    "linkedin": {"account_id": "demo-linkedin-account", "currency": "USD"},
    "tiktok": {"currency": "USD"},
    "microsoft": {},
    "apple": {},
    "amazon": {},
    "reddit": {"currency": "USD"},
    "pinterest": (
        {
            "account_id": "demo-pinterest-account",
            "campaign_id": "demo-pinterest-campaign",
            "currency": "USD",
        }
    ),
    "snapchat": {"account_id": "demo-snapchat-account", "currency": "USD"},
    "x": {},
}


def _snapshot(platform: str, context: dict[str, str]) -> dict:
    if platform in {"amazon", "x"}:
        return GenericCSVExportAdapter(platform).read_snapshot(
            FIXTURES / "exports" / f"{platform}.csv"
        )
    return NativeCSVExportAdapter(platform, context).read_snapshot(
        FIXTURES / "native_exports" / f"{platform}.csv"
    )


@pytest.mark.parametrize("platform", sorted(PLATFORMS))
def test_every_platform_produces_a_schema_valid_unscored_finding_and_report(
    platform: str, repo_root: Path
):
    registry = load_control_registry(repo_root)
    entries = registry.entries_for(platform)
    sourced = [entry for entry in entries if entry.source_claim_ids]
    entry = sourced[0] if sourced else entries[0]
    control = dict(entry.control_definition)
    control_id = entry.control_id
    context = PLATFORM_CONTEXTS[platform]
    snapshot = _snapshot(platform, context)
    finding = {
        "schema_version": "1.0.0",
        "control_id": control_id,
        "status": "unknown",
        "evidence": [],
        "confidence": "none",
        "source_classification": "evidence_based",
        "observation": "The sanitized fixture does not contain every input required by this control.",
        "diagnosis": "The control cannot be resolved from the available projection.",
        "recommendation": "Supply the missing platform evidence for the same reporting window.",
    }
    scoring = registry.score_platform(platform, [finding]).to_dict()
    bundle = {
        "schema_version": "1.0.0",
        "run_manifest": {
            "schema_version": "1.0.0",
            "run_id": f"fixture-{platform}-domain-contract",
            "started_at": "2026-07-11T00:00:00Z",
            "scopes": ["audit", platform],
            "adapters": [{"platform": platform, "mode": "export"}],
            "sources": list(control["source_ids"]),
            "privacy_class": "public",
            "data_lifecycle": {
                "schema_version": "1.0.0",
                "lifecycle_id": f"fixture-{platform}-public-lifecycle",
                "classification": "public",
                "retention": {"minimum_seconds": 0, "mode": "ephemeral", "delete_after": None, "purpose": "Render sanitized public fixture", "exception_reason": None},
                "encryption": {"at_rest": "not-applicable", "in_transit": "not-applicable", "evidence_refs": []},
                "access": {"owner": "fixture-owner", "authorized_roles": ["fixture-runner"], "access_log_locator": None},
                "deletion": {"status": "scheduled", "method": "Fixture cleanup", "verification_required": True, "verification_artifact_locator": None},
                "incident": {"owner": "fixture-owner", "reporting_channel": "Private security channel", "status": "not-triggered", "record_locator": None},
            },
            "worker_status": {platform: "completed"},
            "completeness": "partial",
        },
        "account_snapshot": snapshot,
        "control_definitions": [control],
        "findings": [finding],
        "scoring": scoring,
        "contradictions": [],
        "actions": [],
    }
    validate_contract("report-bundle", bundle)
    markdown = _render_markdown_layout(bundle)
    html = _render_html_layout(bundle)
    assert control_id in markdown.replace("\\-", "-")
    assert control_id in html
    assert "Insufficient evidence" in markdown
    assert "must not be presented as a complete audit" in markdown
    assert control["severity"] == "informational"
    assert control["scoring_behavior"] == "watchlist"
    assert scoring == {
        "health_score": None,
        "evidence_coverage": 0.0,
        "status": "insufficient_evidence",
        "categories": [],
    }


def test_platform_report_cases_cover_exact_product_manifest_platforms():
    assert set(PLATFORM_CONTEXTS) == PLATFORMS
