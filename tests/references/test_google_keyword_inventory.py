"""Issue 75 regression: negatives must not enter the Google positive inventory."""

from __future__ import annotations

import json


GOOGLE_KEYWORD_SURFACES = (
    "agents/audit-google.md",
    "skills/ads-google/SKILL.md",
    "ads/references/google-audit.md",
)


def _case(repo_root):
    return json.loads(
        (
            repo_root
            / "tests/references/fixtures/google-keyword-inventory.json"
        ).read_text(encoding="utf-8")
    )


def test_google_keyword_surfaces_route_to_inventory_rules(repo_root):
    for relative in GOOGLE_KEYWORD_SURFACES:
        text = (repo_root / relative).read_text(encoding="utf-8")
        assert "gaql-notes.md" in text


def test_inventory_rules_split_positive_and_scoped_negative_criteria(repo_root):
    notes = (repo_root / "ads/references/gaql-notes.md").read_text(encoding="utf-8")
    for fragment in (
        "ad_group_criterion.type = 'KEYWORD'",
        "ad_group_criterion.negative = FALSE",
        "ad_group_criterion.negative = TRUE",
        "campaign_criterion.negative = TRUE",
        "campaign_shared_set",
        "customer_negative_criterion",
        "negative exact:",
        "negative phrase:",
        "negative broad:",
        "### Plausibility guards",
    ):
        assert fragment in notes


def test_regression_fixture_has_expected_polarity_and_zero_impression_counts(repo_root):
    case = _case(repo_root)
    positives = [row for row in case["criteria"] if not row["negative"]]
    negatives = [row for row in case["criteria"] if row["negative"]]
    zero_impression = [row["id"] for row in positives if row["impressions"] == 0]
    assert len(positives) == case["expected"]["positive_count"]
    assert len(negatives) == case["expected"]["negative_count"]
    assert zero_impression == case["expected"]["zero_impression_positive_ids"]


def test_model_case_requires_fail_closed_plausibility_guard(repo_root):
    case = _case(repo_root)
    implausible = case["implausible_case"]
    assert implausible["reported_self_blocked_count"] == implausible[
        "in_scope_negative_count"
    ]
    assert implausible["expected_status"] == "unknown"
    required = case["model_case"]["required_behaviors"]
    forbidden = case["model_case"]["forbidden_behaviors"]
    assert "return unknown when a reported conflict count equals the negative count" in required
    assert "count negatives as zero-impression positives" in forbidden
