from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from claude_ads_core.contracts import PLATFORMS
from claude_ads_core.control_registry import RegistryError, load_control_registry


def test_registry_covers_every_catalog_id_exactly_once(check_catalog, repo_root: Path):
    registry = load_control_registry(repo_root)
    expected = {
        (platform, control_id)
        for platform, data in check_catalog["platforms"].items()
        for control_id in data["check_ids"]
    }
    actual = {(entry.platform, entry.control_id) for entry in registry.entries}
    assert actual == expected
    assert len(actual) == sum(data["total_checks"] for data in check_catalog["platforms"].values())


def test_registry_is_reproducibly_generated(repo_root: Path):
    build = runpy.run_path(str(repo_root / "scripts" / "build_control_registry.py"))["build"]
    expected_registry, expected_profiles = build(repo_root)
    manifests = repo_root / "control-plane" / "manifests"
    assert json.loads((manifests / "control-registry.json").read_text(encoding="utf-8")) == expected_registry
    assert json.loads((manifests / "scoring-profiles.json").read_text(encoding="utf-8")) == expected_profiles


def test_current_catalog_is_explicitly_unscored_without_invented_severity(repo_root: Path):
    registry = load_control_registry(repo_root)
    assert registry.entries
    assert all(entry.disposition != "health" for entry in registry.entries)
    assert all(entry.control_definition["severity"] == "informational" for entry in registry.entries)
    assert all(entry.control_definition["scoring_behavior"] in {"watchlist", "opportunity"} for entry in registry.entries)
    assert all(entry.control_definition["required_inputs"] for entry in registry.entries)


def test_all_twelve_profiles_are_versioned_disabled_and_fail_closed(repo_root: Path):
    registry = load_control_registry(repo_root)
    assert {profile.platform for profile in registry.profiles} == PLATFORMS
    for platform in PLATFORMS:
        profile = registry.profile_for(platform)
        assert profile.status == "disabled"
        assert "invent" in (profile.disabled_reason or "")
        with pytest.raises(RegistryError, match="is disabled"):
            registry.scoring_inputs(platform)
        result = registry.score_platform(platform, [])
        assert result.health_score is None
        assert result.evidence_coverage == 0.0
        assert result.status == "insufficient_evidence"


def test_disabled_profile_still_rejects_noncanonical_findings(repo_root: Path):
    registry = load_control_registry(repo_root)
    finding = {
        "schema_version": "1.0.0",
        "control_id": "invented",
        "status": "unknown",
        "evidence": [],
        "confidence": "none",
        "observation": "",
        "diagnosis": "",
        "recommendation": "",
    }
    with pytest.raises(RegistryError, match="non-canonical"):
        registry.score_platform("google", [finding])


def test_source_grounded_watchlists_resolve_to_verified_load_bearing_claims(repo_root: Path):
    registry = load_control_registry(repo_root)
    claims = json.loads(
        (repo_root / "control-plane/manifests/claim-ledger.json").read_text(encoding="utf-8")
    )["claims"]
    by_id = {claim["id"]: claim for claim in claims}
    grounded = [entry for entry in registry.entries if entry.source_claim_ids]
    assert grounded
    for entry in grounded:
        assert entry.control_definition["maturity"] == "source-grounded"
        assert entry.control_definition["source_ids"]
        for claim_id in entry.source_claim_ids:
            assert by_id[claim_id]["verdict"] == "verified"
            assert by_id[claim_id]["load_bearing"] is True
            assert set(entry.control_definition["source_ids"]) <= set(by_id[claim_id]["source_ids"])


def test_loader_rejects_enabling_a_watchlist_profile(tmp_path: Path, repo_root: Path):
    target = tmp_path / "control-plane" / "manifests"
    target.mkdir(parents=True)
    source = repo_root / "control-plane" / "manifests"
    for name in ("control-registry.json", "claim-ledger.json", "source-ledger.json"):
        (target / name).write_bytes((source / name).read_bytes())
    profiles = json.loads((source / "scoring-profiles.json").read_text(encoding="utf-8"))
    profiles["profiles"][0].update(
        status="enabled",
        category_weights={"measurement": 100},
        health_control_ids=["AMZ-M01"],
    )
    profiles["profiles"][0].pop("disabled_reason")
    (target / "scoring-profiles.json").write_text(json.dumps(profiles), encoding="utf-8")
    with pytest.raises(RegistryError, match="references unscored control"):
        load_control_registry(tmp_path)


def test_loader_rejects_health_control_without_verified_claim_grounding(
    tmp_path: Path, repo_root: Path
):
    target = tmp_path / "control-plane" / "manifests"
    target.mkdir(parents=True)
    source = repo_root / "control-plane" / "manifests"
    for name in ("control-registry.json", "scoring-profiles.json", "claim-ledger.json", "source-ledger.json"):
        (target / name).write_bytes((source / name).read_bytes())
    registry = json.loads((target / "control-registry.json").read_text(encoding="utf-8"))
    entry = next(item for item in registry["controls"] if not item["source_claim_ids"])
    entry["disposition"] = "health"
    entry["control_definition"].update(
        severity="high",
        maturity="source-grounded",
        scoring_behavior="health",
        stability="stable",
    )
    (target / "control-registry.json").write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(RegistryError, match="lacks typed evidence grounding"):
        load_control_registry(tmp_path)
