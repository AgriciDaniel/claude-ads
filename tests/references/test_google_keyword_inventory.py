"""Public issue 75: negative keywords must never enter the Google keyword inventory."""

from __future__ import annotations

import json


GOOGLE_KEYWORD_SURFACES = (
    "agents/audit-google.md",
    "skills/ads-google/SKILL.md",
    "ads/references/google-audit.md",
)


def test_google_keyword_surfaces_route_to_the_inventory_rules(repo_root):
    for relative in GOOGLE_KEYWORD_SURFACES:
        text = (repo_root / relative).read_text(encoding="utf-8")
        assert "gaql-notes.md" in text, f"{relative} never loads the keyword inventory rules"


def test_inventory_rules_split_positives_from_scoped_negatives(repo_root):
    notes = (repo_root / "ads/references/gaql-notes.md").read_text(encoding="utf-8")
    assert "ad_group_criterion.type = 'KEYWORD'" in notes
    assert "ad_group_criterion.negative = FALSE" in notes
    for negative_scope in (
        "ad_group_criterion.negative = TRUE",
        "campaign_criterion.negative = TRUE",
        "campaign_shared_set",
        "customer_negative_criterion",
    ):
        assert negative_scope in notes
    for match_rule in ("negative exact:", "negative phrase:", "negative broad:"):
        assert match_rule in notes
    assert "### Plausibility guards" in notes


def test_keyword_controls_cite_current_negative_keyword_evidence(repo_root):
    manifests = repo_root / "control-plane/manifests"
    claims = {
        claim["id"]: claim
        for claim in json.loads(
            (manifests / "claim-ledger.json").read_text(encoding="utf-8")
        )["claims"]
    }
    registry = {
        control["control_id"]: control
        for control in json.loads(
            (manifests / "control-registry.json").read_text(encoding="utf-8")
        )["controls"]
        if control["platform"] == "google"
    }
    expected = {"G14": "CLM-0213", "G15": "CLM-0213", "G-KW1": "CLM-0214"}
    for control_id, claim_id in expected.items():
        assert claim_id in registry[control_id]["source_claim_ids"]
        claim = claims[claim_id]
        assert claim["load_bearing"] is True
        assert claim["verdict"] == "verified"
