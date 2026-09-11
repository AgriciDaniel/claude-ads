from __future__ import annotations

import re
from pathlib import Path


REFERENCE_NAMES = (
    "benchmarks.md",
    "platform-specs.md",
    "compliance.md",
    "compliance-requirements.md",
    "conversion-tracking.md",
    "bidding-strategies.md",
    "budget-allocation.md",
    "mcp-integration.md",
    "automation-tier-classifier.md",
    "meta-ai-stack.md",
)

LEGACY_BRITTLE_FRAGMENTS = (
    "all cited figures verified current",
    "70/20/10",
    "3× kill rule",
    "20% rule (scale up)",
    "50 conversions per week per ad set",
    "200 calls/hour",
    "22-state map",
    "server-side conversion apis are now mandatory",
    "dda (data-driven attribution) is now mandatory",
    "creative similarity score >60%",
    "always overclaims 20-40%",
)

REQUIRED_SOURCE_IDS = {
    "google-smart-bidding-official",
    "google-rsa-official",
    "google-consent-modeling-official",
    "google-consent-modeling-improvement-official",
    "tiktok-events-api-official",
    "eu-ai-act-article-50-official",
    "eu-dsa-official",
    "hhs-tracking-guidance-official",
    "ftc-endorsement-guides-official",
    "google-ads-mcp-official",
    "amazon-ads-mcp-official",
    "tiktok-ads-mcp-official",
    "microsoft-ads-mcp-official",
    "meta-andromeda-engineering-official",
    "meta-ai-ads-ranking-official",
    "meta-gem-training-official",
    "meta-sequence-ranking-official",
}


def _reference_texts(repo_root: Path) -> dict[str, str]:
    root = repo_root / "ads" / "references"
    return {
        name: (root / name).read_text(encoding="utf-8") for name in REFERENCE_NAMES
    }


def test_cross_platform_references_have_verification_and_refresh_metadata(repo_root):
    for name, text in _reference_texts(repo_root).items():
        assert re.search(r"\*\*Verified:\*\* 20\d{2}-\d{2}-\d{2}", text), name
        assert "**Refresh" in text, name


def test_cross_platform_references_do_not_restore_legacy_universal_claims(repo_root):
    corpus = "\n".join(_reference_texts(repo_root).values()).lower()
    for fragment in LEGACY_BRITTLE_FRAGMENTS:
        assert fragment not in corpus


def test_precise_current_claims_use_named_first_party_or_regulator_sources(repo_root):
    corpus = "\n".join(_reference_texts(repo_root).values())
    cited_ids = set(re.findall(r"`([a-z0-9][a-z0-9-]+)`", corpus))
    assert REQUIRED_SOURCE_IDS <= cited_ids

    markdown_links = re.findall(r"\[[^]]+\]\((https://[^)]+)\)", corpus)
    assert len(markdown_links) >= len(REQUIRED_SOURCE_IDS)
    assert all(" " not in link for link in markdown_links)


def test_benchmarks_are_contextual_and_vendor_evidence_is_labeled(repo_root):
    texts = _reference_texts(repo_root)
    assert "Benchmarks are comparison evidence, not pass/fail controls" in texts[
        "benchmarks.md"
    ]
    assert "vendor-supplied" in texts["benchmarks.md"]
    assert "vendor-supplied" in texts["meta-ai-stack.md"]


def test_meta_architecture_does_not_adopt_unverified_issue_prescriptions(repo_root):
    meta = " ".join(_reference_texts(repo_root)["meta-ai-stack.md"].lower().split())
    for unsupported in (
        "1-2 campaigns max",
        "campaign consolidation | 1-2 campaigns",
        "4×4 creative framework",
        "cpmr (cost per 1,000 reached)",
    ):
        assert unsupported not in meta
    assert "cited practitioner articles, not a current meta source" in meta


def test_consent_reference_does_not_invent_an_unpublished_threshold(repo_root):
    conversion = " ".join(
        _reference_texts(repo_root)["conversion-tracking.md"].lower().split()
    )
    assert "100 ad clicks" not in conversion
    assert "does not publish another numeric click threshold" in conversion


def test_automation_and_mcp_do_not_imply_write_authority(repo_root):
    texts = _reference_texts(repo_root)
    assert "disabled by default" in texts["mcp-integration.md"]
    assert "A server's write capability does not upgrade" in texts[
        "mcp-integration.md"
    ]
    assert "not an account-health score" in texts["automation-tier-classifier.md"]
