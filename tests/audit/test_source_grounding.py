"""Evidence-contract tests for the five legacy platform catalogs."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse


PLATFORM_SOURCES = {
    "google": {
        "google-ads-api-official",
        "google-ads-conversion-goals-official",
        "google-ads-enhanced-conversions-official",
    },
    "meta": {"meta-marketing-api-official", "meta-conversions-api-official"},
    "linkedin": {
        "linkedin-marketing-api-official",
        "linkedin-conversion-tracking-official",
        "linkedin-conversions-api-official",
    },
    "tiktok": {
        "tiktok-business-api-official",
        "tiktok-events-api-official",
        "tiktok-pixel-official",
    },
    "microsoft": {
        "microsoft-advertising-api-official",
        "microsoft-uet-official",
        "microsoft-conversions-api-official",
        "microsoft-google-import-official",
    },
}

NEW_PLATFORM_FOUNDATION_SOURCES = {
    "CLM-0012": ("youtube-google-ads-video-official", "developers.google.com"),
    "CLM-0013": ("apple-ads-api-official", "developer.apple.com"),
    "CLM-0014": ("amazon-ads-api-official", "advertising.amazon.com"),
    "CLM-0015": ("reddit-business-help", "business.reddithelp.com"),
    "CLM-0016": ("pinterest-conversions-api", "help.pinterest.com"),
    "CLM-0017": ("snap-marketing-api", "developers.snap.com"),
    "CLM-0018": ("x-conversion-tracking", "business.x.com"),
}

ALLOWED_DISCOVERY_ONLY_SOURCES = {
    "public-claude-ads-issues",
    "public-claude-ads-pulls",
    "meta-video-ads-official",
    "linkedin-ads-guide-official",
    "tiktok-ad-format-policy-official",
    "apple-ads-creative-official",
    "amazon-creative-acceptance-official",
    "reddit-ads-help-official",
    "pinterest-ad-specs-official",
    "snap-creative-specs-official",
    "x-creative-specs-official",
}

UNSCORED_DISCOVERY_IDS = {
    "google": {"G-AI1", *{f"G{i}" for i in range(81, 96)}},
    "meta": {"M-AN1", "M-IA1", "M-TH1", *{f"M{i}" for i in range(51, 73)}},
    "linkedin": {f"L{i}" for i in range(28, 47)},
    "tiktok": {f"T{i}" for i in range(29, 47)},
    "microsoft": {f"MS{i}" for i in range(25, 42)},
}

_CONTROL_ROW_RE = re.compile(
    r"^\|\s*([A-Z]+(?:-[A-Z]+)?[0-9]+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$",
    re.MULTILINE,
)


def _manifest(repo_root, name: str) -> dict:
    path = repo_root / "control-plane" / "manifests" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_runtime_references_name_registered_official_sources(repo_root):
    for platform, source_ids in PLATFORM_SOURCES.items():
        text = (repo_root / "ads" / "references" / f"{platform}-audit.md").read_text(
            encoding="utf-8"
        )
        assert "## Runtime evaluation contract" in text
        assert "## Official evidence" in text
        assert "`not_applicable`" in text
        assert "`unknown`" in text
        for source_id in source_ids:
            assert f"`{source_id}`" in text, f"{platform} omits {source_id}"


def test_launch_discovery_is_explicitly_unscored(repo_root):
    for platform in PLATFORM_SOURCES:
        text = (repo_root / "ads" / "references" / f"{platform}-audit.md").read_text(
            encoding="utf-8"
        )
        assert "discovery" in text.lower()
        assert "unscored" in text.lower()
        assert "scored within existing categories" not in text.lower()


def test_every_legacy_row_has_one_safe_runtime_disposition(repo_root):
    for platform, expected_unscored in UNSCORED_DISCOVERY_IDS.items():
        text = (repo_root / "ads" / "references" / f"{platform}-audit.md").read_text(
            encoding="utf-8"
        )
        rows = {check_id: (intent, disposition) for check_id, intent, disposition in _CONTROL_ROW_RE.findall(text)}
        assert rows, f"{platform} has no control rows"
        actual_unscored = {
            check_id
            for check_id, (_, disposition) in rows.items()
            if disposition.startswith("Unscored source-refresh discovery:")
        }
        assert actual_unscored == expected_unscored
        for check_id, (_, disposition) in rows.items():
            assert disposition.startswith(
                (
                    "Conditional evidence control:",
                    "Unscored source-refresh discovery:",
                )
            ), f"{platform} {check_id} has unsafe disposition: {disposition}"


def test_registry_rows_contain_no_brittle_thresholds_or_mutable_dates(repo_root):
    forbidden_intent = re.compile(
        r"(?:\b20[0-9]{2}\b|\b[0-9]+(?:\.[0-9]+)?%|\$[0-9]|[<>]=?|[≥≤]|"
        r"\b[0-9]+(?:\.[0-9]+)?x\b)",
        re.IGNORECASE,
    )
    forbidden_legacy_phrases = (
        "expert consensus",
        "quick win",
        "always uncheck",
        "mandatory since",
        "scored within existing categories",
        "higher roas",
        "lower cpa",
        "conversion lift",
        "ctr lift",
        "cpl reduction",
        "pass | warning | fail",
    )
    for platform in PLATFORM_SOURCES:
        text = (repo_root / "ads" / "references" / f"{platform}-audit.md").read_text(
            encoding="utf-8"
        )
        rows = _CONTROL_ROW_RE.findall(text)
        for check_id, intent, disposition in rows:
            assert not forbidden_intent.search(intent), (
                f"{platform} {check_id} retains brittle precision in {intent!r}"
            )
            assert not forbidden_intent.search(disposition), (
                f"{platform} {check_id} retains brittle precision in its disposition"
            )
        lowered = text.lower()
        for phrase in forbidden_legacy_phrases:
            assert phrase not in lowered, f"{platform} retains legacy phrase {phrase!r}"


def test_source_and_claim_ledgers_are_reciprocal_and_unique(repo_root):
    source_doc = _manifest(repo_root, "source-ledger.json")
    claim_doc = _manifest(repo_root, "claim-ledger.json")
    sources = {item["id"]: item for item in source_doc["sources"]}
    claims = {item["id"]: item for item in claim_doc["claims"]}

    assert len(sources) == len(source_doc["sources"]), "duplicate source ID"
    assert len(claims) == len(claim_doc["claims"]), "duplicate claim ID"

    for claim_id, claim in claims.items():
        for source_id in claim["source_ids"]:
            assert source_id in sources, f"{claim_id} references unknown {source_id}"
            assert claim_id in sources[source_id]["claim_ids"], (
                f"{source_id} does not link back to {claim_id}"
            )
    for source_id, source in sources.items():
        for claim_id in source["claim_ids"]:
            assert claim_id in claims, f"{source_id} references unknown {claim_id}"
            assert source_id in claims[claim_id]["source_ids"], (
                f"{claim_id} does not link back to {source_id}"
            )


def test_ledgers_match_declared_required_and_allowed_fields(repo_root):
    """Exercise the repository schemas without requiring an optional validator."""
    for manifest_name, schema_name, collection, definition in (
        ("source-ledger.json", "source-ledger.schema.json", "sources", "source"),
        ("claim-ledger.json", "claim-ledger.schema.json", "claims", "claim"),
    ):
        document = _manifest(repo_root, manifest_name)
        schema = json.loads(
            (repo_root / "control-plane" / "schemas" / schema_name).read_text(
                encoding="utf-8"
            )
        )
        assert set(schema["required"]) <= set(document)
        item_schema = schema["$defs"][definition]
        required = set(item_schema["required"])
        allowed = set(item_schema["properties"])
        for item in document[collection]:
            assert required <= set(item), f"{item['id']} lacks required schema fields"
            assert set(item) <= allowed, f"{item['id']} has undeclared schema fields"


def test_platform_runtime_sources_use_https_official_hosts(repo_root):
    source_doc = _manifest(repo_root, "source-ledger.json")
    sources = {item["id"]: item for item in source_doc["sources"]}
    expected_hosts = {
        "developers.google.com",
        "support.google.com",
        "developers.facebook.com",
        "www.facebook.com",
        "learn.microsoft.com",
        "business-api.tiktok.com",
        "ads.tiktok.com",
    }
    for source_ids in PLATFORM_SOURCES.values():
        for source_id in source_ids:
            source = sources[source_id]
            parsed = urlparse(source["locator"])
            assert parsed.scheme == "https"
            assert parsed.hostname in expected_hosts
            assert source["authority_tier"] == 1
            assert source["redistribution"] == "metadata-only"


def test_platform_grounding_claims_are_load_bearing_and_fresh(repo_root):
    claim_doc = _manifest(repo_root, "claim-ledger.json")
    claims = {item["id"]: item for item in claim_doc["claims"]}
    for claim_id in (
        "CLM-0007", "CLM-0008", "CLM-0009", "CLM-0010", "CLM-0011",
        *NEW_PLATFORM_FOUNDATION_SOURCES,
    ):
        claim = claims[claim_id]
        assert claim["load_bearing"] is True
        assert claim["verdict"] == "verified"
        assert claim["last_verified"] == "2026-08-25"
        assert claim["refresh_due"] == "2026-09-24"


def test_new_platform_foundation_claims_use_registered_official_sources(repo_root):
    source_doc = _manifest(repo_root, "source-ledger.json")
    claim_doc = _manifest(repo_root, "claim-ledger.json")
    sources = {item["id"]: item for item in source_doc["sources"]}
    claims = {item["id"]: item for item in claim_doc["claims"]}
    for claim_id, (source_id, hostname) in NEW_PLATFORM_FOUNDATION_SOURCES.items():
        assert claims[claim_id]["source_ids"] == [source_id]
        assert claim_id in sources[source_id]["claim_ids"]
        parsed = urlparse(sources[source_id]["locator"])
        assert parsed.scheme == "https"
        assert parsed.hostname == hostname
        assert sources[source_id]["authority_tier"] == 1
        assert sources[source_id]["redistribution"] == "metadata-only"


def test_unclaimed_sources_are_an_explicit_discovery_only_allowlist(repo_root):
    source_doc = _manifest(repo_root, "source-ledger.json")
    unclaimed = {source["id"] for source in source_doc["sources"] if not source["claim_ids"]}
    assert unclaimed == ALLOWED_DISCOVERY_ONLY_SOURCES
