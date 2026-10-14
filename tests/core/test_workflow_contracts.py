"""Fail-closed tests for typed workflow artifacts and immutable orchestration."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from claude_ads_core.contracts import CONTRACT_NAMES, ContractError, schema_path, validate_contract
from claude_ads_core.orchestration import OrchestrationError, OrchestrationStore, evaluate_artifact_gate
from claude_ads_core.workflow_contracts import WORKFLOW_CONTRACT_NAMES


@pytest.fixture()
def workflow_fixtures(repo_root: Path) -> dict[str, dict]:
    path = repo_root / "tests/fixtures/workflows/valid-artifacts.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_name(fixture_name: str) -> str:
    if fixture_name.startswith("experiment-"):
        return "experiment-artifact"
    return fixture_name


INTEGER_SCHEMA_FIELDS = (
    ("data-lifecycle", ("retention", "minimum_seconds"), 0),
    ("generation-manifest", ("outputs", 0, "width"), 1),
    ("generation-manifest", ("outputs", 0, "height"), 1),
)
DATA_LIFECYCLE_REFERENCE_CONTRACTS = {
    "run-manifest",
    "setup-profile",
    "brand-profile",
    "media-plan",
    "creative-brief",
    "generation-manifest",
    "monitoring-bundle",
    "experiment-artifact",
    "mutation-plan",
    "orchestration-run",
}


def _set_path(payload: dict, path: tuple[str | int, ...], value) -> None:
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


def _declared_integer_fields(repo_root: Path) -> set[tuple[str, tuple[str | int, ...], int]]:
    declared: set[tuple[str, tuple[str | int, ...], int]] = set()
    # This inventory is backed by workflow fixtures. Optional companion
    # contracts have their own boundary and parity tests.
    for contract in WORKFLOW_CONTRACT_NAMES:
        schema = json.loads(schema_path(contract).read_text(encoding="utf-8"))

        def walk(node, path=()):
            if not isinstance(node, dict):
                return
            if node.get("type") == "integer":
                declared.add((contract, path, node.get("minimum")))
            properties = node.get("properties", {})
            if isinstance(properties, dict):
                for name, child in properties.items():
                    walk(child, (*path, name))
            items = node.get("items")
            if isinstance(items, dict):
                walk(items, (*path, 0))

        walk(schema)
    return declared


def test_all_workflow_fixtures_validate_and_have_strict_schemas(workflow_fixtures):
    for fixture_name, payload in workflow_fixtures.items():
        contract = _contract_name(fixture_name)
        assert contract in CONTRACT_NAMES
        validate_contract(contract, payload)
        schema = json.loads(schema_path(contract).read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])


def test_integer_parity_inventory_covers_every_workflow_orchestration_schema_field(repo_root):
    assert _declared_integer_fields(repo_root) == set(INTEGER_SCHEMA_FIELDS)
    lifecycle_refs = set()
    for contract in CONTRACT_NAMES:
        schema = json.loads(schema_path(contract).read_text(encoding="utf-8"))
        lifecycle = schema.get("properties", {}).get("data_lifecycle", {})
        if lifecycle.get("$ref") == (
            "urn:ai-marketing-hub:claude-ads:schema:core:v1:data-lifecycle.schema.json"
        ):
            lifecycle_refs.add(contract)
    assert lifecycle_refs == DATA_LIFECYCLE_REFERENCE_CONTRACTS


@pytest.mark.parametrize(("fixture_name", "path", "minimum"), INTEGER_SCHEMA_FIELDS)
@pytest.mark.parametrize("invalid_kind", ("bool-true", "bool-false", "fraction", "float", "string", "null", "below-minimum"))
def test_every_schema_integer_field_rejects_non_integer_or_below_minimum(
    workflow_fixtures, fixture_name, path, minimum, invalid_kind
):
    payload = copy.deepcopy(workflow_fixtures[fixture_name])
    values = {
        "bool-true": True,
        "bool-false": False,
        "fraction": minimum + 0.5,
        "float": float(minimum),
        "string": str(minimum),
        "null": None,
        "below-minimum": minimum - 1,
    }
    _set_path(payload, path, values[invalid_kind])
    with pytest.raises(ContractError, match="integer|must be >="):
        validate_contract(fixture_name, payload)


@pytest.mark.parametrize(("fixture_name", "path", "minimum"), INTEGER_SCHEMA_FIELDS)
@pytest.mark.parametrize("offset", (0, 1, 10_000))
def test_every_schema_integer_field_accepts_integer_values_at_or_above_minimum(
    workflow_fixtures, fixture_name, path, minimum, offset
):
    payload = copy.deepcopy(workflow_fixtures[fixture_name])
    _set_path(payload, path, minimum + offset)
    validate_contract(fixture_name, payload)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "setup-profile",
        "brand-profile",
        "media-plan",
        "creative-brief",
        "generation-manifest",
        "monitoring-bundle",
        "experiment-setup",
        "experiment-readout",
        "mutation-plan",
        "orchestration-run",
    ],
)
def test_embedded_data_lifecycle_integer_validation_is_identical_across_contracts(
    workflow_fixtures, fixture_name
):
    payload = copy.deepcopy(workflow_fixtures[fixture_name])
    payload["data_lifecycle"]["retention"]["minimum_seconds"] = 0.5
    with pytest.raises(ContractError, match="minimum_seconds must be an integer"):
        validate_contract(_contract_name(fixture_name), payload)


def test_schema_number_fields_still_accept_fractional_values(workflow_fixtures):
    media_plan = copy.deepcopy(workflow_fixtures["media-plan"])
    media_plan["channels"][0]["budget_amount"] = 0.5
    validate_contract("media-plan", media_plan)

    generation = copy.deepcopy(workflow_fixtures["generation-manifest"])
    generation["outputs"][0]["cost"] = {"currency": "USD", "amount": 0.5}
    validate_contract("generation-manifest", generation)

    mutation = copy.deepcopy(workflow_fixtures["mutation-plan"])
    mutation["ceilings"][0]["value"] = 0.5
    validate_contract("mutation-plan", mutation)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "data-lifecycle", "setup-profile", "brand-profile", "media-plan", "creative-brief",
        "generation-manifest", "monitoring-bundle", "experiment-setup",
        "experiment-readout", "mutation-plan", "orchestration-run",
        "orchestration-task", "orchestration-result", "orchestration-gate",
    ],
)
def test_contracts_reject_unknown_fields(workflow_fixtures, fixture_name):
    payload = copy.deepcopy(workflow_fixtures[fixture_name])
    payload["unreviewed_extension"] = True
    with pytest.raises(ContractError, match="unknown field"):
        validate_contract(_contract_name(fixture_name), payload)


def test_experiment_setup_and_readout_are_distinct(workflow_fixtures):
    setup = copy.deepcopy(workflow_fixtures["experiment-setup"])
    setup["decision"] = "peeked early"
    with pytest.raises(ContractError, match="must not contain result or decision"):
        validate_contract("experiment-artifact", setup)

    readout = copy.deepcopy(workflow_fixtures["experiment-readout"])
    readout["result"] = None
    with pytest.raises(ContractError, match="must be an object"):
        validate_contract("experiment-artifact", readout)


def test_mutation_plan_never_authorizes_itself(workflow_fixtures):
    plan = copy.deepcopy(workflow_fixtures["mutation-plan"])
    plan["status"] = "applied"
    with pytest.raises(ContractError, match="approval is required"):
        validate_contract("mutation-plan", plan)

    deletion = copy.deepcopy(workflow_fixtures["mutation-plan"])
    deletion["operation"] = "permanent-delete"
    with pytest.raises(ContractError, match="deletion is outside"):
        validate_contract("mutation-plan", deletion)

    traversal = copy.deepcopy(workflow_fixtures["mutation-plan"])
    traversal["audit_destination"] = "../outside.json"
    with pytest.raises(ContractError, match="contained POSIX relative path"):
        validate_contract("mutation-plan", traversal)


def test_creative_copy_requires_current_specification_evidence(workflow_fixtures):
    brief = copy.deepcopy(workflow_fixtures["creative-brief"])
    brief["specification_source_ids"] = []
    with pytest.raises(ContractError, match="required when copy_deck is present"):
        validate_contract("creative-brief", brief)


def test_monitoring_bundle_cannot_hide_missing_inputs(workflow_fixtures):
    bundle = copy.deepcopy(workflow_fixtures["monitoring-bundle"])
    bundle["completeness"] = "complete"
    with pytest.raises(ContractError, match="cannot be complete"):
        validate_contract("monitoring-bundle", bundle)


def test_non_public_lifecycle_requires_encryption_and_deletion_deadline(workflow_fixtures):
    lifecycle = copy.deepcopy(workflow_fixtures["data-lifecycle"])
    lifecycle["encryption"]["at_rest"] = "not-applicable"
    with pytest.raises(ContractError, match="verified at-rest and in-transit"):
        validate_contract("data-lifecycle", lifecycle)

    lifecycle = copy.deepcopy(workflow_fixtures["data-lifecycle"])
    lifecycle["retention"]["delete_after"] = None
    with pytest.raises(ContractError, match="delete_after is required"):
        validate_contract("data-lifecycle", lifecycle)


def test_store_is_append_only_and_result_reruns_require_supersedes(tmp_path, workflow_fixtures):
    store = OrchestrationStore(tmp_path / "orchestration")
    run = workflow_fixtures["orchestration-run"]
    task = workflow_fixtures["orchestration-task"]
    result = workflow_fixtures["orchestration-result"]
    store.write("run", run)
    store.write("task", task)
    first_path = store.write("result", result)
    assert first_path.stat().st_mode & 0o777 == 0o600

    with pytest.raises(OrchestrationError, match="already exists"):
        store.write("result", result)

    repeated = copy.deepcopy(result)
    repeated["result_id"] = "unlinked-repeat"
    repeated["created_at"] = "2026-07-11T10:20:00Z"
    with pytest.raises(OrchestrationError, match="must supersede"):
        store.write("result", repeated)


def test_supersedes_uses_real_instants_not_timestamp_text_order(tmp_path, workflow_fixtures):
    store = OrchestrationStore(tmp_path / "orchestration")
    first = copy.deepcopy(workflow_fixtures["orchestration-result"])
    first["created_at"] = "2026-07-11T11:00:00+02:00"
    store.write("result", first)

    later = copy.deepcopy(first)
    later["result_id"] = "build-plan-result-two"
    later["created_at"] = "2026-07-11T09:30:00Z"
    later["supersedes"] = first["result_id"]
    store.write("result", later)

    branch = copy.deepcopy(later)
    branch["result_id"] = "build-plan-result-branch"
    branch["created_at"] = "2026-07-11T09:45:00Z"
    with pytest.raises(OrchestrationError, match="superseded only once"):
        store.write("result", branch)


def test_store_rejects_symlinked_root_and_intermediate_directory(tmp_path, workflow_fixtures):
    real = tmp_path / "real"
    real.mkdir()
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(real, target_is_directory=True)
    with pytest.raises(OrchestrationError, match="contains a symlink"):
        OrchestrationStore(linked_root).write("run", workflow_fixtures["orchestration-run"])

    root = tmp_path / "root"
    root.mkdir()
    (root / "tasks").symlink_to(real, target_is_directory=True)
    with pytest.raises(OrchestrationError, match="contains a symlink"):
        OrchestrationStore(root).write("task", workflow_fixtures["orchestration-task"])


def test_artifact_only_gate_passes_and_fails_from_latest_packets(workflow_fixtures):
    run = workflow_fixtures["orchestration-run"]
    task = workflow_fixtures["orchestration-task"]
    result = workflow_fixtures["orchestration-result"]
    passing = evaluate_artifact_gate(
        run, [task], [result], gate_id="planning-gate-generated", stage="planning",
        required_task_ids=["build-plan"], evaluated_at="2026-07-11T10:12:00Z",
    )
    assert passing["decision"] == "pass"
    assert passing["evaluated_result_ids"] == ["build-plan-result-one"]

    failing = evaluate_artifact_gate(
        run, [task], [], gate_id="planning-gate-missing", stage="planning",
        required_task_ids=["build-plan"], evaluated_at="2026-07-11T10:12:00Z",
    )
    assert failing["decision"] == "fail"
    assert "required result packet is missing" in failing["blockers"][0]


def test_artifact_gate_rejects_cross_run_or_role_mismatch(workflow_fixtures):
    run = workflow_fixtures["orchestration-run"]
    task = workflow_fixtures["orchestration-task"]
    result = copy.deepcopy(workflow_fixtures["orchestration-result"])
    result["role"] = "different-role"
    with pytest.raises(OrchestrationError, match="declared task and role"):
        evaluate_artifact_gate(
            run, [task], [result], gate_id="bad-gate", stage="planning",
            required_task_ids=["build-plan"], evaluated_at="2026-07-11T10:12:00Z",
        )
