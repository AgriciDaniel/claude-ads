from __future__ import annotations

import json
from pathlib import Path

import pytest

import claude_ads_core
from claude_ads_core.contracts import CONTRACT_NAMES, ContractError, schema_path, validate_contract
from claude_ads_core.control_registry import (
    ControlRegistry,
    RegistryEntry,
    ScoringProfile,
    load_control_registry,
)
from claude_ads_core import (
    AccountSnapshot,
    AuditWorkerResult,
    ControlDefinition,
    Finding,
    ReportBundle,
    RunManifest,
)


def data_lifecycle(classification: str = "confidential") -> dict:
    return {
        "schema_version": "1.0.0",
        "lifecycle_id": "test-lifecycle",
        "classification": classification,
        "retention": {
            "minimum_seconds": 0,
            "mode": "operator-defined",
            "delete_after": "2026-07-12T16:00:00Z" if classification != "public" else None,
            "purpose": "Complete and verify the sanitized test run",
            "exception_reason": None,
        },
        "encryption": {
            "at_rest": "verified" if classification != "public" else "not-applicable",
            "in_transit": "verified" if classification != "public" else "not-applicable",
            "evidence_refs": ["operator-attestation:test-encryption"] if classification != "public" else [],
        },
        "access": {"owner": "test-owner", "authorized_roles": ["test-operator"], "access_log_locator": None},
        "deletion": {"status": "scheduled", "method": "Operator-defined deletion", "verification_required": True, "verification_artifact_locator": None},
        "incident": {"owner": "test-owner", "reporting_channel": "Private security channel", "status": "not-triggered", "record_locator": None},
    }


def account_snapshot() -> dict:
    return {
        "schema_version": "1.0.0",
        "account": {"platform": "google", "account_id": "acct-1"},
        "window": {"start": "2026-06-01", "end": "2026-06-30"},
        "currency": "USD",
        "spend": 250.5,
        "campaigns": [],
        "creatives": [],
        "conversions": [],
        "budgets": [],
    }


def run_manifest() -> dict:
    return {
        "schema_version": "1.0.0",
        "run_id": "run-20260711-001",
        "started_at": "2026-07-11T16:00:00Z",
        "scopes": ["audit", "google"],
        "adapters": [{"platform": "google", "mode": "export"}],
        "sources": ["export.csv"],
        "privacy_class": "confidential",
        "data_lifecycle": data_lifecycle(),
        "worker_status": {"google": "completed"},
        "completeness": "complete",
    }


def control(control_id: str = "G-1") -> dict:
    return {
        "schema_version": "1.0.0",
        "control_id": control_id,
        "category": "tracking",
        "severity": "critical",
        "required_inputs": ["conversions"],
        "source_ids": ["google-help-1"],
        "maturity": "source-grounded",
        "geographies": ["global"],
        "expires_at": "2026-08-01",
        "scoring_behavior": "health",
        "stability": "stable",
    }


def finding(control_id: str = "G-1") -> dict:
    return {
        "schema_version": "1.0.0",
        "control_id": control_id,
        "status": "pass",
        "evidence": [{"path": "conversions[0]"}],
        "confidence": "high",
        "observation": "Conversion action is active.",
        "diagnosis": "No fault found.",
        "recommendation": "Keep monitoring.",
    }


def report_bundle() -> dict:
    return {
        "schema_version": "1.0.0",
        "run_manifest": run_manifest(),
        "account_snapshot": account_snapshot(),
        "control_definitions": [control()],
        "findings": [finding()],
        "scoring": {
            "health_score": 100.0,
            "evidence_coverage": 100.0,
            "status": "normal",
            "categories": [],
        },
    }


def audit_worker_result() -> dict:
    return {
        "schema_version": "1.0.0",
        "status": "needs_input",
        "platform": "google",
        "scope": ["tracking"],
        "findings": [
            {
                **finding("G01"),
                "status": "unknown",
                "evidence": [],
                "confidence": "none",
            }
        ],
        "contradictions": [],
        "missing_inputs": ["conversion action configuration"],
        "stale_sources": [],
        "recovery_hints": ["Export configuration for the same reporting window."],
    }


def registry_report_bundle(repo_root: Path, platform: str = "google") -> dict:
    registry = load_control_registry(repo_root)
    entry = registry.entries_for(platform)[0]
    payload = report_bundle()
    payload["account_snapshot"]["account"]["platform"] = platform
    payload["run_manifest"]["adapters"] = [{"platform": platform, "mode": "export"}]
    payload["control_definitions"] = [dict(entry.control_definition)]
    payload["findings"] = [
        {
            "schema_version": "1.0.0",
            "control_id": entry.control_id,
            "status": "unknown",
            "evidence": [],
            "confidence": "none",
            "observation": "The sanitized fixture does not resolve this control.",
            "diagnosis": "More account evidence is required.",
            "recommendation": "Supply the required inputs for the same window.",
        }
    ]
    payload["scoring"] = registry.score_platform(platform, payload["findings"]).to_dict()
    return payload


def synthetic_report_registry(bundle: dict) -> ControlRegistry:
    platform = bundle["account_snapshot"]["account"]["platform"]
    entries = tuple(
        RegistryEntry(
            platform=platform,
            control_id=control["control_id"],
            intent="sanitized report fixture",
            disposition="health",
            source_claim_ids=(),
            control_definition=control,
        )
        for control in bundle["control_definitions"]
    )
    health_ids = tuple(
        entry.control_id
        for entry in entries
        if entry.control_definition["scoring_behavior"] == "health"
        and entry.control_definition["stability"] == "stable"
    )
    categories = {
        category["category"]: category["category_weight"]
        for category in bundle["scoring"]["categories"]
    }
    if not categories:
        category_names = {
            entry.control_definition["category"]
            for entry in entries
            if entry.control_id in health_ids
        }
        if len(category_names) != 1:
            raise AssertionError("synthetic report requires explicit category weights")
        categories = {next(iter(category_names)): 100.0}
    profile = ScoringProfile(
        profile_id=f"{platform}-synthetic-test-v1",
        platform=platform,
        status="enabled",
        category_weights=categories,
        health_control_ids=health_ids,
        disabled_reason=None,
    )
    return ControlRegistry(entries=entries, profiles=(profile,))


def test_named_contract_types_are_public_interfaces():
    assert {
        item.__name__
        for item in (
            AccountSnapshot,
            AuditWorkerResult,
            RunManifest,
            ControlDefinition,
            Finding,
            ReportBundle,
        )
    } == {
        "AccountSnapshot",
        "AuditWorkerResult",
        "RunManifest",
        "ControlDefinition",
        "Finding",
        "ReportBundle",
    }
    assert "AuditWorkerResult" in claude_ads_core.__all__


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("account-snapshot", account_snapshot()),
        ("audit-worker-result", audit_worker_result()),
        ("run-manifest", run_manifest()),
        ("control-definition", control()),
        ("finding", finding()),
        ("report-bundle", report_bundle()),
    ],
)
def test_v1_contracts_accept_valid_payloads(name: str, payload: dict):
    validate_contract(name, payload)


def test_all_packaged_schemas_are_valid_json_and_versioned():
    for name in CONTRACT_NAMES:
        path = schema_path(name)
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == (
            f"urn:ai-marketing-hub:claude-ads:schema:core:v1:{name}.schema.json"
        )


def test_every_cross_file_schema_reference_is_absolute_and_registered(repo_root: Path):
    schema_roots = (
        repo_root / "claude_ads_core/schemas/v1",
        repo_root / "control-plane/schemas",
        repo_root / "evals/schemas",
    )
    documents = []
    registered_ids = set()
    for schema_root in schema_roots:
        for path in schema_root.glob("*.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            documents.append((path, document))
            registered_ids.add(document["$id"])

    def references(value):
        if isinstance(value, dict):
            if "$ref" in value:
                yield value["$ref"]
            for child in value.values():
                yield from references(child)
        elif isinstance(value, list):
            for child in value:
                yield from references(child)

    for path, document in documents:
        for reference in references(document):
            if reference.startswith("#"):
                continue
            target = reference.split("#", 1)[0]
            assert target.startswith("urn:ai-marketing-hub:claude-ads:schema:"), (
                path,
                reference,
            )
            assert target in registered_ids, (path, reference)


def test_audit_worker_result_fixture_has_schema_validator_parity(repo_root: Path):
    jsonschema = pytest.importorskip("jsonschema")
    referencing = pytest.importorskip("referencing")
    fixture_path = repo_root / "tests/fixtures/audit-worker-results/valid.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    validate_contract("audit-worker-result", payload)

    schema_root = repo_root / "claude_ads_core/schemas/v1"
    schemas = [json.loads(path.read_text(encoding="utf-8")) for path in schema_root.glob("*.json")]
    registry = referencing.Registry().with_resources(
        [(schema["$id"], referencing.Resource.from_contents(schema)) for schema in schemas]
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_path("audit-worker-result").read_text(encoding="utf-8")),
        registry=registry,
    )
    assert list(validator.iter_errors(payload)) == []
    invalid = json.loads(json.dumps(payload))
    invalid["findings"][0]["severity"] = "high"
    assert list(validator.iter_errors(invalid))

    invalid = json.loads(json.dumps(payload))
    invalid["findings"][0].update(status="fail", evidence=[], confidence="high")
    with pytest.raises(ContractError, match="evidence"):
        validate_contract("audit-worker-result", invalid)
    assert list(validator.iter_errors(invalid))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2.0.0"),
        ("control_id", ""),
        ("status", "maybe"),
        ("evidence", ["not-an-object"]),
        ("confidence", "certain"),
        ("source_classification", "official"),
        ("observation", 1),
        ("diagnosis", None),
        ("recommendation", []),
        ("score_contribution", "one"),
    ],
)
def test_audit_worker_finding_schema_and_semantic_validator_reject_same_constraints(
    repo_root: Path, field: str, value
):
    jsonschema = pytest.importorskip("jsonschema")
    referencing = pytest.importorskip("referencing")
    schema_root = repo_root / "claude_ads_core/schemas/v1"
    schemas = [json.loads(path.read_text(encoding="utf-8")) for path in schema_root.glob("*.json")]
    registry = referencing.Registry().with_resources(
        [(schema["$id"], referencing.Resource.from_contents(schema)) for schema in schemas]
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_path("audit-worker-result").read_text(encoding="utf-8")),
        registry=registry,
    )
    payload = audit_worker_result()
    payload["findings"][0][field] = value
    with pytest.raises(ContractError):
        validate_contract("audit-worker-result", payload)
    assert list(validator.iter_errors(payload)), field


@pytest.mark.parametrize("forbidden", ["severity", "result", "evidence_refs"])
def test_audit_worker_result_rejects_alternate_finding_vocabulary(forbidden: str):
    payload = audit_worker_result()
    payload["findings"][0][forbidden] = "high" if forbidden == "severity" else []
    with pytest.raises(ContractError, match="unsupported field"):
        validate_contract("audit-worker-result", payload)


def test_audit_worker_result_requires_exact_envelope():
    payload = audit_worker_result()
    payload["extra"] = []
    with pytest.raises(ContractError, match="unsupported field"):
        validate_contract("audit-worker-result", payload)


def test_audit_worker_result_requires_canonical_platform_id():
    payload = audit_worker_result()
    payload["platform"] = "Google"
    with pytest.raises(ContractError, match="platform"):
        validate_contract("audit-worker-result", payload)


def test_snapshot_rejects_reversed_window():
    payload = account_snapshot()
    payload["window"] = {"start": "2026-07-01", "end": "2026-06-01"}
    with pytest.raises(ContractError, match="on or after"):
        validate_contract("account-snapshot", payload)


def test_snapshot_rejects_non_finite_spend():
    payload = account_snapshot()
    payload["spend"] = float("nan")
    with pytest.raises(ContractError, match="finite"):
        validate_contract("account-snapshot", payload)


def test_manifest_requires_timezone_aware_started_at():
    payload = run_manifest()
    payload["started_at"] = "2026-07-11T16:00:00"
    with pytest.raises(ContractError, match="UTC offset"):
        validate_contract("run-manifest", payload)


def test_manifest_requires_matching_data_lifecycle_classification():
    payload = run_manifest()
    payload["data_lifecycle"]["classification"] = "internal"
    with pytest.raises(ContractError, match="must match"):
        validate_contract("run-manifest", payload)


@pytest.mark.parametrize("invalid", [0.5, 0.0, True, False, "0", None, -1])
def test_run_manifest_embedded_lifecycle_requires_strict_nonnegative_integer_retention(
    invalid
):
    payload = run_manifest()
    payload["data_lifecycle"]["retention"]["minimum_seconds"] = invalid
    with pytest.raises(ContractError, match="integer|must be >="):
        validate_contract("run-manifest", payload)


def test_pass_or_fail_requires_evidence():
    payload = finding()
    payload["evidence"] = []
    with pytest.raises(ContractError, match="must not be empty"):
        validate_contract("finding", payload)


def test_unknown_may_have_no_evidence():
    payload = finding()
    payload.update(status="unknown", evidence=[], confidence="none")
    validate_contract("finding", payload)


@pytest.mark.parametrize("classification", ["evidence_based", "practitioner", "contested", "folklore"])
def test_finding_accepts_source_classification_independently_of_confidence(classification: str):
    payload = finding()
    payload["source_classification"] = classification
    payload["confidence"] = "low"
    validate_contract("finding", payload)


def test_finding_rejects_unknown_source_classification():
    payload = finding()
    payload["source_classification"] = "high"
    with pytest.raises(ContractError, match="source_classification"):
        validate_contract("finding", payload)


def test_report_bundle_recursively_validates_nested_contracts():
    payload = report_bundle()
    payload["account_snapshot"]["account"]["platform"] = "unsupported"
    with pytest.raises(ContractError, match="platform"):
        validate_contract("report-bundle", payload)
