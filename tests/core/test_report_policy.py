from __future__ import annotations

import copy
from pathlib import Path

import pytest

from claude_ads_core.control_registry import RegistryError, load_control_registry
from claude_ads_core.report_policy import validate_report_bundle_policy
from tests.core.test_contracts import registry_report_bundle


def test_policy_valid_report_bundle_accepts_disabled_profile_output(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    validate_report_bundle_policy(bundle, load_control_registry(repo_root))
    assert bundle["scoring"]["health_score"] is None
    assert bundle["scoring"]["evidence_coverage"] == 0.0


def test_report_policy_rejects_forged_control_definition(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["control_definitions"][0]["severity"] = "critical"
    with pytest.raises(RegistryError, match="not canonical"):
        validate_report_bundle_policy(bundle, load_control_registry(repo_root))


def test_report_policy_rejects_cross_platform_control(repo_root: Path):
    registry = load_control_registry(repo_root)
    bundle = registry_report_bundle(repo_root)
    other = registry.entries_for("meta")[0]
    bundle["control_definitions"] = [copy.deepcopy(other.control_definition)]
    bundle["findings"][0]["control_id"] = other.control_id
    with pytest.raises(RegistryError, match="not canonical"):
        validate_report_bundle_policy(bundle, registry)


def test_report_policy_requires_canonical_account_platform(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["account_snapshot"]["account"]["platform"] = "Google"
    with pytest.raises(RegistryError, match="canonical lowercase"):
        validate_report_bundle_policy(bundle, load_control_registry(repo_root))


def test_report_policy_rejects_recomputed_score_mismatch(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["scoring"] = {
        "health_score": 100.0,
        "evidence_coverage": 100.0,
        "status": "normal",
        "categories": [],
    }
    with pytest.raises(RegistryError, match="does not match canonical"):
        validate_report_bundle_policy(bundle, load_control_registry(repo_root))


@pytest.mark.parametrize("status", ["failed", "pending", "running"])
def test_complete_report_rejects_unfinished_or_failed_workers(
    repo_root: Path, status: str
):
    bundle = registry_report_bundle(repo_root)
    bundle["run_manifest"]["worker_status"] = {"google": status}
    with pytest.raises(RegistryError, match="unfinished or failed"):
        validate_report_bundle_policy(bundle, load_control_registry(repo_root))


def test_complete_report_rejects_empty_worker_status(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["run_manifest"]["worker_status"] = {}
    with pytest.raises(RegistryError, match="matching worker status"):
        validate_report_bundle_policy(bundle, load_control_registry(repo_root))


def test_complete_report_rejects_unfinished_additional_recorded_worker(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["run_manifest"]["worker_status"] = {
        "google": "completed",
        "tracking": "pending",
    }
    with pytest.raises(RegistryError, match="tracking"):
        validate_report_bundle_policy(bundle, load_control_registry(repo_root))


def test_complete_report_accepts_completed_and_skipped_recorded_workers(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["run_manifest"]["worker_status"] = {
        "google": "completed",
        "optional-policy": "skipped",
    }
    validate_report_bundle_policy(bundle, load_control_registry(repo_root))


def test_report_rejects_cross_platform_adapter_and_worker_provenance(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["run_manifest"]["adapters"] = [{"platform": "meta", "mode": "export"}]
    bundle["run_manifest"]["worker_status"] = {"meta": "completed"}
    with pytest.raises(RegistryError, match="matching run-manifest adapter"):
        validate_report_bundle_policy(bundle, load_control_registry(repo_root))


def test_partial_report_permits_recorded_platform_failure(repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["run_manifest"]["completeness"] = "partial"
    bundle["run_manifest"]["worker_status"] = {"google": "failed"}
    validate_report_bundle_policy(bundle, load_control_registry(repo_root))
