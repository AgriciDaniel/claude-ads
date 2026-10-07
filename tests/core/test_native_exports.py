from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from claude_ads_core.adapters import (
    MutationDisabledError,
    NativeCSVExportAdapter,
    NativeExportError,
    get_native_profile,
)
from claude_ads_core.adapters.mappings_v1 import PROFILES
from claude_ads_core.contracts import PLATFORMS, validate_contract


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "native_exports"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

CONTEXT = {
    "google": {},
    "youtube": {},
    "meta": {"currency": "USD"},
    "linkedin": {"account_id": "demo-linkedin-account", "currency": "USD"},
    "tiktok": {"currency": "USD"},
    "microsoft": {},
    "apple": {},
    "amazon": {},
    "reddit": {"currency": "USD"},
    "pinterest": {
        "account_id": "demo-pinterest-account",
        "campaign_id": "demo-pinterest-campaign",
        "currency": "USD",
    },
    "snapchat": {"account_id": "demo-snapchat-account", "currency": "USD"},
    "x": {},
}

EXPECTED = {
    "google": (42.5, 12.0, "google_ads_conversions_metric", 0, 1),
    "youtube": (40.5, 10.0, "google_ads_conversions_metric", 0, 1),
    "meta": (41.5, None, None, 0, 0),
    "linkedin": (39.5, 9.0, "external_website_conversions", 0, 0),
    "tiktok": (38.5, 8.0, "selected_optimization_event", 1, 0),
    "microsoft": (37.5, 7.0, "bidding_qualified_conversions", 1, 0),
    "apple": (36.5, 6.0, "total_installs", 0, 1),
    "reddit": (34.5, 4.0, "key_conversion_total_count", 1, 0),
    "pinterest": (33.5, 3.0, "total_conversions", 0, 0),
    "snapchat": (32.5, 2.0, "conversion_purchases", 0, 0),
}

EXPECTED_PROFILE_STATUSES = {
    platform: (
        "disabled"
        if platform in {"amazon", "x"}
        else "fixture-verified"
    )
    for platform in PLATFORMS
}


def _rewrite_csv(source: Path, target: Path, mutate) -> Path:
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    headers, rows = mutate(headers, rows)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    return target


def test_v1_profiles_and_sanitized_fixtures_cover_exactly_all_twelve_platforms():
    assert set(PROFILES) == PLATFORMS
    assert {path.stem for path in FIXTURE_ROOT.glob("*.csv")} == PLATFORMS
    assert all(profile.schema_version == "1.0.0" for profile in PROFILES.values())
    assert len({profile.profile_id for profile in PROFILES.values()}) == 12


def test_profile_status_schema_rejects_unknown_or_unexplained_nonverified_statuses():
    assert {platform: profile.status for platform, profile in PROFILES.items()} == EXPECTED_PROFILE_STATUSES
    with pytest.raises(ValueError, match="implemented.*require a status reason"):
        replace(PROFILES["google"], status="implemented")
    with pytest.raises(ValueError, match="unsupported native export profile status"):
        replace(PROFILES["google"], status="unknown")


@pytest.mark.parametrize("platform", ["meta", "tiktok"])
def test_reverified_profiles_expose_fixture_maturity_and_decode_without_warning(platform: str):
    adapter = NativeCSVExportAdapter(platform, CONTEXT[platform])
    capability = adapter.discover_capabilities().capabilities[0]
    assert capability.status == "fixture-verified"
    assert capability.disabled_reason is adapter.profile.disabled_reason is None
    snapshot = adapter.read_snapshot(FIXTURE_ROOT / f"{platform}.csv")
    validate_contract("account-snapshot", snapshot)
    assert snapshot["account"]["platform"] == platform


def test_profile_source_ids_resolve_and_every_profile_cites_official_https_evidence():
    ledger = json.loads((REPOSITORY_ROOT / "control-plane" / "manifests" / "source-ledger.json").read_text())
    sources = {source["id"]: source for source in ledger["sources"]}
    claims = {
        claim["id"]: claim
        for claim in json.loads(
            (REPOSITORY_ROOT / "control-plane" / "manifests" / "claim-ledger.json").read_text()
        )["claims"]
    }
    for profile in PROFILES.values():
        assert set(profile.source_ids) <= set(sources)
        assert profile.source_urls
        assert all(url.startswith("https://") for url in profile.source_urls)
        assert all("github.com" not in url for url in profile.source_urls)
        if profile.status == "fixture-verified":
            for source_id in profile.source_ids:
                linked = [claims[claim_id] for claim_id in sources[source_id]["claim_ids"]]
                assert any(
                    claim["load_bearing"] and claim["verdict"] == "verified"
                    for claim in linked
                ), f"{profile.profile_id} source {source_id} lacks a verified load-bearing claim"
        elif profile.status == "implemented":
            for source_id in profile.source_ids:
                linked = [claims[claim_id] for claim_id in sources[source_id]["claim_ids"]]
                assert not any(
                    claim["load_bearing"] and claim["verdict"] == "verified"
                    for claim in linked
                ), f"{profile.profile_id} must be promoted before asserting current evidence"

    assert PROFILES["google"].source_urls == (
        "https://developers.google.com/google-ads/api/fields/v25/campaign",
    )
    assert "https://developers.google.com/google-ads/api/fields/v25/campaign" in PROFILES[
        "youtube"
    ].source_urls


def test_profile_fields_are_unambiguous_and_semantically_documented():
    for profile in PROFILES.values():
        assert json.loads(json.dumps(profile.to_dict()))["profile_id"] == profile.profile_id
        sources = [field.source for field in profile.fields]
        targets = [field.target for field in profile.fields]
        guards = [guard.source for guard in profile.guards]
        assert len(sources + guards) == len(set(sources + guards))
        assert len(targets) == len(set(targets))
        assert all(field.semantic.strip() for field in profile.fields)
        assert all(guard.semantic.strip() for guard in profile.guards)
        assert all(check.semantic.strip() for check in profile.date_checks)
        if profile.status == "disabled":
            assert not profile.fields
            assert profile.disabled_reason


@pytest.mark.parametrize("platform", sorted(EXPECTED))
def test_enabled_native_profiles_normalize_representative_official_report_rows(platform: str):
    spend, conversions, action, creative_count, budget_count = EXPECTED[platform]
    adapter = NativeCSVExportAdapter(platform, CONTEXT[platform])
    snapshot = adapter.read_snapshot(FIXTURE_ROOT / f"{platform}.csv")
    validate_contract("account-snapshot", snapshot)
    assert snapshot["account"]["platform"] == platform
    assert snapshot["account"]["account_id"] == f"demo-{platform}-account"
    assert snapshot["window"] == {"start": "2026-06-15", "end": "2026-06-15"}
    assert snapshot["currency"] == "USD"
    assert snapshot["spend"] == spend
    assert len(snapshot["campaigns"]) == 1
    assert len(snapshot["creatives"]) == creative_count
    assert len(snapshot["budgets"]) == budget_count
    if conversions is None:
        assert snapshot["conversions"] == []
    else:
        assert snapshot["conversions"] == [{"action": action, "count": conversions}]


@pytest.mark.parametrize("platform", ["amazon", "x"])
def test_unverified_native_schemas_are_explicitly_disabled_and_fail_before_parsing(platform: str):
    adapter = NativeCSVExportAdapter(platform)
    capabilities = adapter.discover_capabilities()
    native = capabilities.capabilities[0]
    assert native.status == "disabled"
    assert native.disabled_reason == adapter.profile.disabled_reason
    assert adapter.profile.unsupported_normalized_fields
    with pytest.raises(NativeExportError, match="is disabled"):
        adapter.read_snapshot(FIXTURE_ROOT / f"{platform}.csv")


@pytest.mark.parametrize("platform", sorted(PLATFORMS))
def test_every_native_profile_remains_read_only(platform: str):
    adapter = NativeCSVExportAdapter(platform, CONTEXT[platform])
    assert adapter.discover_capabilities().writes_enabled is False
    with pytest.raises(MutationDisabledError, match="read-only"):
        adapter.apply_changes({})


def test_exact_profile_rejects_unknown_or_missing_headers(tmp_path: Path):
    source = FIXTURE_ROOT / "meta.csv"

    def add_unknown(headers, rows):
        headers.append("actions")
        rows[0]["actions"] = "untyped-structured-value"
        return headers, rows

    unknown = _rewrite_csv(source, tmp_path / "unknown.csv", add_unknown)
    with pytest.raises(NativeExportError, match="unmapped column.*actions"):
        NativeCSVExportAdapter("meta", CONTEXT["meta"]).read_snapshot(unknown)

    def drop_spend(headers, rows):
        headers.remove("spend")
        rows[0].pop("spend")
        return headers, rows

    missing = _rewrite_csv(source, tmp_path / "missing.csv", drop_spend)
    with pytest.raises(NativeExportError, match="missing profile column.*spend"):
        NativeCSVExportAdapter("meta", CONTEXT["meta"]).read_snapshot(missing)


def test_request_scope_context_is_exact_required_and_nonempty():
    with pytest.raises(NativeExportError, match=r"context\.currency must not be empty"):
        NativeCSVExportAdapter("meta")
    with pytest.raises(NativeExportError, match="does not accept context field.*campaign_id"):
        NativeCSVExportAdapter("meta", {"currency": "USD", "campaign_id": "invented"})


def test_google_and_youtube_channel_guards_prevent_cross_platform_misattribution(tmp_path: Path):
    google_source = FIXTURE_ROOT / "google.csv"

    def make_video(headers, rows):
        rows[0]["campaign.advertising_channel_type"] = "VIDEO"
        return headers, rows

    video_google = _rewrite_csv(google_source, tmp_path / "video-google.csv", make_video)
    with pytest.raises(NativeExportError, match="routes to a different platform profile"):
        NativeCSVExportAdapter("google").read_snapshot(video_google)

    youtube_source = FIXTURE_ROOT / "youtube.csv"

    def make_search(headers, rows):
        rows[0]["campaign.advertising_channel_type"] = "SEARCH"
        return headers, rows

    search_youtube = _rewrite_csv(youtube_source, tmp_path / "search-youtube.csv", make_search)
    with pytest.raises(NativeExportError, match="outside profile values VIDEO"):
        NativeCSVExportAdapter("youtube").read_snapshot(search_youtube)


@pytest.mark.parametrize("platform", ["google", "youtube", "reddit", "pinterest", "snapchat"])
def test_microcurrency_profiles_convert_exactly_once(platform: str):
    adapter = NativeCSVExportAdapter(platform, CONTEXT[platform])
    snapshot = adapter.read_snapshot(FIXTURE_ROOT / f"{platform}.csv")
    assert snapshot["spend"] == EXPECTED[platform][0]
    assert snapshot["spend"] < 1000


def test_duplicate_native_grain_fails_instead_of_double_counting(tmp_path: Path):
    source = FIXTURE_ROOT / "tiktok.csv"

    def duplicate(headers, rows):
        rows.append(dict(rows[0]))
        return headers, rows

    duplicate_source = _rewrite_csv(source, tmp_path / "duplicate.csv", duplicate)
    with pytest.raises(NativeExportError, match="duplicate native report grain"):
        NativeCSVExportAdapter("tiktok", CONTEXT["tiktok"]).read_snapshot(duplicate_source)


def test_snap_daily_timestamp_requires_offset(tmp_path: Path):
    source = FIXTURE_ROOT / "snapchat.csv"

    def remove_offset(headers, rows):
        rows[0]["start_time"] = "2026-06-15T00:00:00"
        return headers, rows

    ambiguous = _rewrite_csv(source, tmp_path / "ambiguous.csv", remove_offset)
    with pytest.raises(NativeExportError, match="must include a timezone offset"):
        NativeCSVExportAdapter("snapchat", CONTEXT["snapchat"]).read_snapshot(ambiguous)


@pytest.mark.parametrize(
    ("platform", "field", "bad_value", "relation"),
    [
        ("meta", "date_stop", "2026-06-16", "same_date"),
        ("linkedin", "dateRange.end", "2026-06-16", "same_date"),
        ("snapchat", "end_time", "2026-06-17T00:00:00-07:00", "next_calendar_date"),
    ],
)
def test_daily_profiles_reject_multi_day_rows(
    tmp_path: Path, platform: str, field: str, bad_value: str, relation: str
):
    source = FIXTURE_ROOT / f"{platform}.csv"

    def change_end(headers, rows):
        rows[0][field] = bad_value
        return headers, rows

    invalid = _rewrite_csv(source, tmp_path / f"{platform}-multi-day.csv", change_end)
    with pytest.raises(NativeExportError, match=f"date relationship {relation} failed"):
        NativeCSVExportAdapter(platform, CONTEXT[platform]).read_snapshot(invalid)


def test_linkedin_campaign_profile_rejects_a_non_campaign_pivot_urn(tmp_path: Path):
    source = FIXTURE_ROOT / "linkedin.csv"

    def use_creative_pivot(headers, rows):
        rows[0]["pivotValues.0"] = "urn:li:sponsoredCreative:1234567"
        return headers, rows

    wrong_pivot = _rewrite_csv(source, tmp_path / "wrong-pivot.csv", use_creative_pivot)
    with pytest.raises(NativeExportError, match="must be a sponsoredCampaign URN"):
        NativeCSVExportAdapter("linkedin", CONTEXT["linkedin"]).read_snapshot(wrong_pivot)


def test_profile_lookup_rejects_unknown_platform_without_fallback():
    with pytest.raises(ValueError, match="unsupported native export platform"):
        get_native_profile("other")
    with pytest.raises(NativeExportError, match="unsupported native export platform"):
        NativeCSVExportAdapter("other")
