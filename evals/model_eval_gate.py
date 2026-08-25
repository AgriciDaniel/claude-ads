#!/usr/bin/env python3
"""Build and assess the fail-closed Claude Ads canonical model-eval gate.

This tool never invokes a model and never manufactures model-run evidence. The
``plan`` command emits immutable task packets for an external Claude Code
runner. The ``assess`` command consumes two independently evaluated, private
run artifacts and emits only a deterministic, machine-readable gate summary.
Raw responses are required for hash and excerpt checks but are never copied to
the summary.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence

try:
    from evals.model_evidence_auth import (
        ModelEvidenceAuthError,
        load_external_trust,
        sha256_json,
        verify_envelope,
    )
except ModuleNotFoundError:  # direct ``python evals/model_eval_gate.py`` execution
    _evals_dir = str(Path(__file__).resolve().parent)
    sys.path.insert(0, _evals_dir)
    try:
        from model_evidence_auth import (  # type: ignore[no-redef]
            ModelEvidenceAuthError,
            load_external_trust,
            sha256_json,
            verify_envelope,
        )
    finally:
        sys.path.remove(_evals_dir)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "evals" / "model-eval-contract.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")


class EvaluationContractError(ValueError):
    """Raised when an evaluation artifact is missing or invalid."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationContractError(f"cannot read JSON {path}: {exc}") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise EvaluationContractError(f"cannot hash {path}: {exc}") from exc


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvaluationContractError(f"{path} must be an object")
    return value


def _array(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise EvaluationContractError(f"{path} must be an array")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationContractError(f"{path} must be a non-empty string")
    return value


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise EvaluationContractError(f"{path} must be a boolean")
    return value


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise EvaluationContractError(f"{path} must be an integer >= {minimum}")
    return value


def _exact_keys(
    payload: Mapping[str, Any], required: set[str], path: str, optional: set[str] | None = None
) -> None:
    optional = optional or set()
    missing = sorted(required - payload.keys())
    extra = sorted(payload.keys() - required - optional)
    if missing:
        raise EvaluationContractError(f"{path} missing fields: {', '.join(missing)}")
    if extra:
        raise EvaluationContractError(f"{path} has unexpected fields: {', '.join(extra)}")


def _digest(value: Any, path: str, pattern: re.Pattern[str] = SHA256_RE) -> str:
    text = _string(value, path)
    if not pattern.fullmatch(text):
        raise EvaluationContractError(f"{path} has an invalid digest")
    return text


def _timestamp(value: Any, path: str) -> datetime:
    text = _string(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvaluationContractError(f"{path} must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        raise EvaluationContractError(f"{path} must include a UTC offset")
    return parsed


def _load_contract(path: Path) -> dict[str, Any]:
    value = _object(_read_json(path), "contract")
    required = {
        "schema_version",
        "contract_id",
        "schemas",
        "suite",
        "result_path",
        "subjects",
        "runtime",
        "evaluation",
        "thresholds",
        "evidence_policy",
        "authentication_policy",
    }
    _exact_keys(value, required, "contract")
    if value["schema_version"] != "2.0.0":
        raise EvaluationContractError("contract.schema_version must equal '2.0.0'")
    if value["contract_id"] != "claude-ads-v2-canonical-model-gate":
        raise EvaluationContractError("unexpected contract.contract_id")
    schemas = _object(value["schemas"], "contract.schemas")
    _exact_keys(schemas, {"external_run", "gate_report", "trust_bundle"}, "contract.schemas")
    for field in ("external_run", "gate_report", "trust_bundle"):
        schema = _object(schemas[field], f"contract.schemas.{field}")
        _exact_keys(schema, {"path", "sha256"}, f"contract.schemas.{field}")
        _string(schema["path"], f"contract.schemas.{field}.path")
        _digest(schema["sha256"], f"contract.schemas.{field}.sha256")
    suite = _object(value["suite"], "contract.suite")
    _exact_keys(suite, {"path", "sha256", "case_count"}, "contract.suite")
    _string(suite["path"], "contract.suite.path")
    _digest(suite["sha256"], "contract.suite.sha256")
    _integer(suite["case_count"], "contract.suite.case_count", minimum=1)
    _string(value["result_path"], "contract.result_path")
    subjects = _object(value["subjects"], "contract.subjects")
    _exact_keys(subjects, {"candidate", "retained_v1"}, "contract.subjects")
    candidate = _object(subjects["candidate"], "contract.subjects.candidate")
    _exact_keys(candidate, {"role", "product_version", "required_ref"}, "contract.subjects.candidate")
    if candidate["role"] != "candidate":
        raise EvaluationContractError("contract candidate role is invalid")
    baseline = _object(subjects["retained_v1"], "contract.subjects.retained_v1")
    _exact_keys(
        baseline,
        {"role", "product_version", "required_ref", "git_commit", "git_tree"},
        "contract.subjects.retained_v1",
    )
    if baseline["role"] != "retained-v1":
        raise EvaluationContractError("contract retained-v1 role is invalid")
    _digest(baseline["git_commit"], "contract baseline commit", GIT_RE)
    _digest(baseline["git_tree"], "contract baseline tree", GIT_RE)
    runtime = _object(value["runtime"], "contract.runtime")
    _exact_keys(
        runtime,
        {
            "family",
            "skill_entrypoint",
            "invocation_mode",
            "fresh_process_per_case",
            "conversation_reuse",
            "mutation_authority",
        },
        "contract.runtime",
    )
    if runtime != {
        "family": "claude-code",
        "skill_entrypoint": "/claude-ads:ads",
        "invocation_mode": "explicit-plugin-skill",
        "fresh_process_per_case": True,
        "conversation_reuse": False,
        "mutation_authority": "none",
    }:
        raise EvaluationContractError("contract runtime must preserve canonical isolation")
    evaluation = _object(value["evaluation"], "contract.evaluation")
    _exact_keys(
        evaluation,
        {"rubric_id", "independent_evaluator_required", "accepted_evaluator_kinds"},
        "contract.evaluation",
    )
    if evaluation["independent_evaluator_required"] is not True:
        raise EvaluationContractError("contract must require an independent evaluator")
    kinds = _array(evaluation["accepted_evaluator_kinds"], "contract evaluator kinds")
    if set(kinds) != {"human", "independent-model"}:
        raise EvaluationContractError("contract evaluator kinds are invalid")
    thresholds = _object(value["thresholds"], "contract.thresholds")
    _exact_keys(
        thresholds,
        {
            "minimum_candidate_score_percent",
            "maximum_p0_failures",
            "maximum_regressions_against_retained_v1",
        },
        "contract.thresholds",
    )
    minimum = thresholds["minimum_candidate_score_percent"]
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or not 0 <= minimum <= 100:
        raise EvaluationContractError("candidate score threshold must be between 0 and 100")
    _integer(thresholds["maximum_p0_failures"], "maximum_p0_failures")
    _integer(
        thresholds["maximum_regressions_against_retained_v1"],
        "maximum_regressions_against_retained_v1",
    )
    policy = _object(value["evidence_policy"], "contract.evidence_policy")
    _exact_keys(
        policy,
        {
            "required_evidence_class",
            "raw_responses_required_for_assessment",
            "raw_responses_must_not_be_packaged",
            "local_checks_do_not_substitute_for_external_runs",
        },
        "contract.evidence_policy",
    )
    if policy != {
        "required_evidence_class": "external_model_run",
        "raw_responses_required_for_assessment": True,
        "raw_responses_must_not_be_packaged": True,
        "local_checks_do_not_substitute_for_external_runs": True,
    }:
        raise EvaluationContractError("contract evidence policy is not fail-closed")
    authentication = _object(value["authentication_policy"], "contract.authentication_policy")
    _exact_keys(
        authentication,
        {
            "algorithm",
            "maximum_age_days",
            "separate_runner_evaluator_keys",
            "external_trust_bundle_env",
            "implementation_principals_env",
            "repository_trust_roots_allowed",
        },
        "contract.authentication_policy",
    )
    if authentication != {
        "algorithm": "Ed25519",
        "maximum_age_days": 14,
        "separate_runner_evaluator_keys": True,
        "external_trust_bundle_env": "CLAUDE_ADS_MODEL_EVAL_TRUST_BUNDLE_JSON",
        "implementation_principals_env": "CLAUDE_ADS_MODEL_EVAL_IMPLEMENTATION_PRINCIPALS_JSON",
        "repository_trust_roots_allowed": False,
    }:
        raise EvaluationContractError("contract authentication policy is not fail-closed")
    return dict(value)


def _load_schemas(root: Path, contract: Mapping[str, Any]) -> None:
    for schema_id, schema_meta in contract["schemas"].items():
        relative = _string(schema_meta["path"], f"contract.schemas.{schema_id}.path")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or "\\" in relative or any(part in {"", ".", ".."} for part in pure.parts):
            raise EvaluationContractError(f"contract schema path is unsafe: {relative!r}")
        path = root / relative
        if _sha256_file(path) != schema_meta["sha256"]:
            raise EvaluationContractError(f"{schema_id} schema SHA-256 does not match the contract")
        schema = _object(_read_json(path), f"{schema_id} schema")
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise EvaluationContractError(f"{schema_id} is not a JSON Schema Draft 2020-12 contract")
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            raise EvaluationContractError(f"{schema_id} schema must be a strict object contract")


def _load_suite(root: Path, contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    suite_meta = contract["suite"]
    suite_path = root / suite_meta["path"]
    if _sha256_file(suite_path) != suite_meta["sha256"]:
        raise EvaluationContractError("behavior suite SHA-256 does not match the contract")
    raw_cases = _array(_read_json(suite_path), "suite")
    if len(raw_cases) != suite_meta["case_count"]:
        raise EvaluationContractError("behavior suite case count does not match the contract")
    cases: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, raw in enumerate(raw_cases):
        case = _object(raw, f"suite[{index}]")
        required = {
            "id",
            "prompt",
            "expected_skill",
            "risk",
            "comparison",
            "required_behaviors",
            "forbidden_behaviors",
        }
        _exact_keys(case, required, f"suite[{index}]")
        case_id = _string(case["id"], f"suite[{index}].id")
        if case_id in ids:
            raise EvaluationContractError(f"duplicate suite case ID: {case_id}")
        ids.add(case_id)
        if case["risk"] not in {"P0", "P1", "P2", "normal"}:
            raise EvaluationContractError(f"suite case {case_id} has invalid risk")
        if case["comparison"] != "with_skill_vs_baseline":
            raise EvaluationContractError(f"suite case {case_id} is not comparative")
        for field in ("required_behaviors", "forbidden_behaviors"):
            behaviors = _array(case[field], f"suite case {case_id}.{field}")
            if not behaviors:
                raise EvaluationContractError(f"suite case {case_id}.{field} is empty")
            for behavior in behaviors:
                _string(behavior, f"suite case {case_id}.{field}")
            if len(behaviors) != len(set(behaviors)):
                raise EvaluationContractError(f"suite case {case_id}.{field} has duplicates")
        if set(case["required_behaviors"]) & set(case["forbidden_behaviors"]):
            raise EvaluationContractError(f"suite case {case_id} has contradictory behaviors")
        cases.append(dict(case))
    return cases


def _validate_judgments(
    values: Any,
    expected: Sequence[str],
    response: str,
    path: str,
    *,
    required_kind: bool,
) -> list[dict[str, Any]]:
    judgments = _array(values, path)
    if len(judgments) != len(expected):
        raise EvaluationContractError(f"{path} must contain exactly {len(expected)} judgments")
    by_behavior: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(judgments):
        judgment = _object(raw, f"{path}[{index}]")
        _exact_keys(
            judgment,
            {"behavior", "observed", "rationale"},
            f"{path}[{index}]",
            {"evidence_excerpt"},
        )
        behavior = _string(judgment["behavior"], f"{path}[{index}].behavior")
        if behavior in by_behavior:
            raise EvaluationContractError(f"{path} repeats behavior {behavior!r}")
        observed = _boolean(judgment["observed"], f"{path}[{index}].observed")
        _string(judgment["rationale"], f"{path}[{index}].rationale")
        excerpt = judgment.get("evidence_excerpt")
        needs_excerpt = observed if required_kind else observed
        if needs_excerpt:
            excerpt_text = _string(excerpt, f"{path}[{index}].evidence_excerpt")
            if excerpt_text not in response:
                raise EvaluationContractError(
                    f"{path}[{index}].evidence_excerpt is not present in the raw response"
                )
        elif excerpt is not None:
            excerpt_text = _string(excerpt, f"{path}[{index}].evidence_excerpt")
            if excerpt_text not in response:
                raise EvaluationContractError(
                    f"{path}[{index}].evidence_excerpt is not present in the raw response"
                )
        by_behavior[behavior] = dict(judgment)
    if set(by_behavior) != set(expected):
        missing = sorted(set(expected) - set(by_behavior))
        extra = sorted(set(by_behavior) - set(expected))
        raise EvaluationContractError(
            f"{path} does not match suite rubric; missing={missing}, extra={extra}"
        )
    return [by_behavior[behavior] for behavior in expected]


def _runner_binding(run: Mapping[str, Any]) -> dict[str, Any]:
    execution = run["execution"]
    runtime = run["runtime"]
    subject = run["subject"]
    case_receipts = [
        {
            "case_id": case["case_id"],
            "invocation_id": case["invocation_id"],
            "prompt_sha256": case["prompt_sha256"],
            "response_sha256": case["response_sha256"],
            "skill_invocation": case["skill_invocation"],
        }
        for case in run["cases"]
    ]
    return {
        "contract_id": run["contract_id"],
        "evidence_role": run["role"],
        "run_id_sha256": _sha256_text(run["run_id"]),
        "suite_sha256": run["suite"]["sha256"],
        "subject": {
            "git_commit": subject["git_commit"],
            "git_tree": subject["git_tree"],
            "artifact_sha256": subject["artifact_sha256"],
        },
        "runtime": dict(runtime),
        "execution": {
            "started_at": execution["started_at"],
            "finished_at": execution["finished_at"],
            "executor_identity": execution["executor_identity"],
            "environment_id": execution["environment_id"],
            "clean_checkout": execution["clean_checkout"],
            "mutation_authority": execution["mutation_authority"],
            "receipt_sha256": _sha256_text(execution["receipt"]),
        },
        "case_receipts_sha256": sha256_json(case_receipts),
        "case_count": len(case_receipts),
        "explicit_invocation_case_count": sum(
            case["skill_invocation"]
            == {"entrypoint": "/claude-ads:ads", "mode": "explicit-plugin-skill"}
            for case in run["cases"]
        ),
    }


def _evaluator_binding(run: Mapping[str, Any], result_summary: Mapping[str, Any]) -> dict[str, Any]:
    evaluator = run["evaluator"]
    judgments = [
        {
            "case_id": case["case_id"],
            "response_sha256": case["response_sha256"],
            "required_behavior_results": case["required_behavior_results"],
            "forbidden_behavior_results": case["forbidden_behavior_results"],
        }
        for case in run["cases"]
    ]
    return {
        "contract_id": run["contract_id"],
        "evidence_role": run["role"],
        "run_id_sha256": _sha256_text(run["run_id"]),
        "runner_binding_sha256": sha256_json(_runner_binding(run)),
        "rubric_id": evaluator["rubric_id"],
        "evaluator": {
            "kind": evaluator["kind"],
            "identity": evaluator["identity"],
            "independent_from_subject_run": evaluator["independent_from_subject_run"],
            "evaluated_at": evaluator["evaluated_at"],
            "receipt_sha256": _sha256_text(evaluator["receipt"]),
        },
        "judgments_sha256": sha256_json(judgments),
        "result": dict(result_summary),
    }


def _validate_external_run(
    payload: Any,
    role: str,
    contract: Mapping[str, Any],
    suite: Sequence[Mapping[str, Any]],
    expected_candidate_commit: str,
    expected_candidate_tree: str,
    auth_context: tuple[Mapping[tuple[str, str], Mapping[str, Any]], set[str], datetime, str],
) -> dict[str, Any]:
    run = _object(payload, role)
    _exact_keys(
        run,
        {
            "schema_version",
            "evidence_class",
            "contract_id",
            "run_id",
            "role",
            "suite",
            "subject",
            "runtime",
            "execution",
            "evaluator",
            "cases",
            "authentication",
        },
        role,
    )
    if run["schema_version"] != "2.0.0":
        raise EvaluationContractError(f"{role}.schema_version must equal '2.0.0'")
    if run["evidence_class"] != "external_model_run":
        raise EvaluationContractError(f"{role} is not external model-run evidence")
    if run["contract_id"] != contract["contract_id"]:
        raise EvaluationContractError(f"{role}.contract_id does not match")
    _string(run["run_id"], f"{role}.run_id")
    expected_role = "candidate" if role == "candidate" else "retained-v1"
    if run["role"] != expected_role:
        raise EvaluationContractError(f"{role}.role must equal {expected_role!r}")

    run_suite = _object(run["suite"], f"{role}.suite")
    _exact_keys(run_suite, {"path", "sha256", "case_count"}, f"{role}.suite")
    if dict(run_suite) != dict(contract["suite"]):
        raise EvaluationContractError(f"{role}.suite does not match the pinned suite")

    subject = _object(run["subject"], f"{role}.subject")
    _exact_keys(
        subject,
        {"product_version", "git_ref", "git_commit", "git_tree", "artifact_sha256"},
        f"{role}.subject",
    )
    subject_contract = contract["subjects"]["candidate" if role == "candidate" else "retained_v1"]
    if subject["product_version"] != subject_contract["product_version"]:
        raise EvaluationContractError(f"{role}.subject.product_version does not match")
    if subject["git_ref"] != subject_contract["required_ref"]:
        raise EvaluationContractError(f"{role}.subject.git_ref does not match")
    commit = _digest(subject["git_commit"], f"{role}.subject.git_commit", GIT_RE)
    tree = _digest(subject["git_tree"], f"{role}.subject.git_tree", GIT_RE)
    _digest(subject["artifact_sha256"], f"{role}.subject.artifact_sha256")
    if role == "candidate":
        if commit != expected_candidate_commit or tree != expected_candidate_tree:
            raise EvaluationContractError(
                "candidate evidence is stale: commit/tree do not match the assessed candidate"
            )
    else:
        if commit != subject_contract["git_commit"] or tree != subject_contract["git_tree"]:
            raise EvaluationContractError("retained-v1 evidence does not use the pinned baseline")

    runtime = _object(run["runtime"], f"{role}.runtime")
    _exact_keys(
        runtime,
        {
            "family",
            "cli_version",
            "provider",
            "model_id",
            "model_snapshot",
            "fresh_process_per_case",
            "conversation_reuse",
            "skill_loaded",
            "skill_entrypoint",
            "invocation_mode",
        },
        f"{role}.runtime",
    )
    if runtime["family"] != "claude-code" or runtime["provider"] != "anthropic":
        raise EvaluationContractError(f"{role} did not run in canonical Claude Code")
    for field in ("cli_version", "model_id", "model_snapshot"):
        _string(runtime[field], f"{role}.runtime.{field}")
    if runtime["fresh_process_per_case"] is not True:
        raise EvaluationContractError(f"{role} reused a process between cases")
    if runtime["conversation_reuse"] is not False:
        raise EvaluationContractError(f"{role} reused conversation context")
    if runtime["skill_loaded"] is not True:
        raise EvaluationContractError(f"{role} did not load its subject skill")
    if (
        runtime["skill_entrypoint"] != contract["runtime"]["skill_entrypoint"]
        or runtime["invocation_mode"] != contract["runtime"]["invocation_mode"]
    ):
        raise EvaluationContractError(f"{role} did not use the canonical explicit plugin entrypoint")

    execution = _object(run["execution"], f"{role}.execution")
    _exact_keys(
        execution,
        {
            "started_at",
            "finished_at",
            "executor_identity",
            "environment_id",
            "clean_checkout",
            "mutation_authority",
            "receipt",
        },
        f"{role}.execution",
    )
    started = _timestamp(execution["started_at"], f"{role}.execution.started_at")
    finished = _timestamp(execution["finished_at"], f"{role}.execution.finished_at")
    if finished < started:
        raise EvaluationContractError(f"{role}.execution.finished_at precedes started_at")
    for field in ("executor_identity", "environment_id", "receipt"):
        _string(execution[field], f"{role}.execution.{field}")
    if execution["clean_checkout"] is not True:
        raise EvaluationContractError(f"{role} did not use a clean checkout")
    if execution["mutation_authority"] != "none":
        raise EvaluationContractError(f"{role} had mutation authority")

    evaluator = _object(run["evaluator"], f"{role}.evaluator")
    _exact_keys(
        evaluator,
        {"kind", "identity", "rubric_id", "independent_from_subject_run", "evaluated_at", "receipt"},
        f"{role}.evaluator",
    )
    if evaluator["kind"] not in contract["evaluation"]["accepted_evaluator_kinds"]:
        raise EvaluationContractError(f"{role}.evaluator.kind is not accepted")
    for field in ("identity", "receipt"):
        _string(evaluator[field], f"{role}.evaluator.{field}")
    if evaluator["identity"] == execution["executor_identity"]:
        raise EvaluationContractError(f"{role} was graded by its own executor")
    if evaluator["receipt"] == execution["receipt"]:
        raise EvaluationContractError(f"{role} evaluator receipt is not independent")
    if evaluator["rubric_id"] != contract["evaluation"]["rubric_id"]:
        raise EvaluationContractError(f"{role}.evaluator.rubric_id does not match")
    if evaluator["independent_from_subject_run"] is not True:
        raise EvaluationContractError(f"{role} evaluator is not independent")
    evaluated_at = _timestamp(evaluator["evaluated_at"], f"{role}.evaluator.evaluated_at")
    if evaluated_at < finished:
        raise EvaluationContractError(f"{role} was graded before execution finished")

    case_payloads = _array(run["cases"], f"{role}.cases")
    if len(case_payloads) != len(suite):
        raise EvaluationContractError(f"{role}.cases does not cover the complete suite")
    by_id: dict[str, Mapping[str, Any]] = {}
    invocation_ids: set[str] = set()
    for index, raw_case in enumerate(case_payloads):
        case = _object(raw_case, f"{role}.cases[{index}]")
        _exact_keys(
            case,
            {
                "case_id",
                "invocation_id",
                "prompt_sha256",
                "response_sha256",
                "response",
                "skill_invocation",
                "required_behavior_results",
                "forbidden_behavior_results",
            },
            f"{role}.cases[{index}]",
        )
        case_id = _string(case["case_id"], f"{role}.cases[{index}].case_id")
        if case_id in by_id:
            raise EvaluationContractError(f"{role} repeats case {case_id}")
        invocation_id = _string(case["invocation_id"], f"{role}.cases[{index}].invocation_id")
        if invocation_id in invocation_ids:
            raise EvaluationContractError(f"{role} repeats invocation ID {invocation_id}")
        invocation_ids.add(invocation_id)
        skill_invocation = _object(
            case["skill_invocation"], f"{role}.cases[{index}].skill_invocation"
        )
        _exact_keys(
            skill_invocation,
            {"entrypoint", "mode"},
            f"{role}.cases[{index}].skill_invocation",
        )
        if dict(skill_invocation) != {
            "entrypoint": contract["runtime"]["skill_entrypoint"],
            "mode": contract["runtime"]["invocation_mode"],
        }:
            raise EvaluationContractError(
                f"{role} case {case_id} did not explicitly invoke /claude-ads:ads"
            )
        by_id[case_id] = case

    expected_ids = {case["id"] for case in suite}
    if set(by_id) != expected_ids:
        raise EvaluationContractError(f"{role}.cases IDs do not match the suite")

    results: dict[str, dict[str, Any]] = {}
    for suite_case in suite:
        case_id = suite_case["id"]
        case = by_id[case_id]
        if case["prompt_sha256"] != _sha256_text(suite_case["prompt"]):
            raise EvaluationContractError(f"{role} case {case_id} prompt hash does not match")
        response = _string(case["response"], f"{role} case {case_id}.response")
        if case["response_sha256"] != _sha256_text(response):
            raise EvaluationContractError(f"{role} case {case_id} response hash does not match")
        required_results = _validate_judgments(
            case["required_behavior_results"],
            suite_case["required_behaviors"],
            response,
            f"{role} case {case_id}.required_behavior_results",
            required_kind=True,
        )
        forbidden_results = _validate_judgments(
            case["forbidden_behavior_results"],
            suite_case["forbidden_behaviors"],
            response,
            f"{role} case {case_id}.forbidden_behavior_results",
            required_kind=False,
        )
        passed = all(item["observed"] for item in required_results) and not any(
            item["observed"] for item in forbidden_results
        )
        results[case_id] = {"passed": passed, "risk": suite_case["risk"]}

    passed_count = sum(result["passed"] for result in results.values())
    failed_ids = [case["id"] for case in suite if not results[case["id"]]["passed"]]
    p0_failures = sum(results[case_id]["risk"] == "P0" for case_id in failed_ids)
    result_summary = {
        "case_count": len(suite),
        "passed": passed_count,
        "failed": len(suite) - passed_count,
        "score_percent": round(100 * passed_count / len(suite), 2),
        "p0_failures": p0_failures,
        "failed_case_ids": failed_ids,
    }
    authentication = _object(run["authentication"], f"{role}.authentication")
    _exact_keys(authentication, {"runner", "evaluator"}, f"{role}.authentication")
    runner_envelope = _object(authentication["runner"], f"{role}.authentication.runner")
    evaluator_envelope = _object(authentication["evaluator"], f"{role}.authentication.evaluator")
    expected_runner_binding = _runner_binding(run)
    expected_evaluator_binding = _evaluator_binding(run, result_summary)
    if runner_envelope.get("binding") != expected_runner_binding:
        raise EvaluationContractError(f"{role} runner signature binding does not match the exact run")
    if evaluator_envelope.get("binding") != expected_evaluator_binding:
        raise EvaluationContractError(f"{role} evaluator signature binding does not match rubric/results")
    trusted_keys, principals, now, trust_bundle_sha256 = auth_context
    try:
        verified_runner = verify_envelope(
            runner_envelope,
            expected_role="runner",
            evidence_role=run["role"],
            trusted_keys=trusted_keys,
            implementation_principals=principals,
            now=now,
        )
        verified_evaluator = verify_envelope(
            evaluator_envelope,
            expected_role="evaluator",
            evidence_role=run["role"],
            trusted_keys=trusted_keys,
            implementation_principals=principals,
            now=now,
        )
    except ModelEvidenceAuthError as exc:
        raise EvaluationContractError(f"{role} authentication invalid: {exc}") from exc
    if verified_runner["signer_id"] != execution["executor_identity"]:
        raise EvaluationContractError(f"{role} runner signer does not match executor identity")
    if verified_evaluator["signer_id"] != evaluator["identity"]:
        raise EvaluationContractError(f"{role} evaluator signer does not match evaluator identity")
    if (
        verified_runner["signer_id"] == verified_evaluator["signer_id"]
        or verified_runner["key_id"] == verified_evaluator["key_id"]
    ):
        raise EvaluationContractError(f"{role} runner and evaluator must use separate identities and keys")
    runner_signed = _timestamp(verified_runner["signed_at"], f"{role}.runner.signed_at")
    evaluator_signed = _timestamp(verified_evaluator["signed_at"], f"{role}.evaluator.signed_at")
    if runner_signed < finished or evaluator_signed < evaluated_at or evaluator_signed < runner_signed:
        raise EvaluationContractError(f"{role} authentication signatures are out of sequence")
    authentication_summary = {
        "trust_bundle_sha256": trust_bundle_sha256,
        "runner": verified_runner,
        "evaluator": verified_evaluator,
    }
    return {
        "payload": dict(run),
        "results": results,
        "finished_at": execution["finished_at"],
        "evaluated_at": evaluator["evaluated_at"],
        "summary": {
            "status": "verified",
            "evidence_class": "external_model_run",
            "run_id_sha256": _sha256_text(run["run_id"]),
            "role": run["role"],
            "git_commit": subject["git_commit"],
            "git_tree": subject["git_tree"],
            "artifact_sha256": subject["artifact_sha256"],
            "runtime": runtime["family"],
            "cli_version": runtime["cli_version"],
            "provider": runtime["provider"],
            "model_id": runtime["model_id"],
            "model_snapshot": runtime["model_snapshot"],
            "skill_entrypoint": runtime["skill_entrypoint"],
            "invocation_mode": runtime["invocation_mode"],
            "explicit_invocation_case_count": len(suite),
            "fresh_process_per_case": runtime["fresh_process_per_case"],
            "conversation_reuse": runtime["conversation_reuse"],
            "mutation_authority": execution["mutation_authority"],
            **result_summary,
            "receipt_sha256": _sha256_text(execution["receipt"]),
            "authentication": authentication_summary,
        },
    }


def _missing_summary(role: str, status: str, error: str) -> dict[str, Any]:
    return {
        "status": status,
        "evidence_class": None,
        "run_id_sha256": None,
        "role": None,
        "git_commit": None,
        "git_tree": None,
        "artifact_sha256": None,
        "runtime": None,
        "cli_version": None,
        "provider": None,
        "model_id": None,
        "model_snapshot": None,
        "skill_entrypoint": None,
        "invocation_mode": None,
        "explicit_invocation_case_count": None,
        "fresh_process_per_case": None,
        "conversation_reuse": None,
        "mutation_authority": None,
        "case_count": None,
        "passed": None,
        "failed": None,
        "score_percent": None,
        "p0_failures": None,
        "failed_case_ids": [],
        "receipt_sha256": None,
        "authentication": None,
        "error": f"{role}: {error}",
    }


def _git_identity(root: Path, ref: str) -> tuple[str, str]:
    values: list[str] = []
    for suffix in ("^{commit}", "^{tree}"):
        result = subprocess.run(
            ["git", "rev-parse", f"{ref}{suffix}"],
            cwd=root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode:
            raise EvaluationContractError(
                f"cannot resolve candidate {ref}{suffix}: {result.stderr.strip()}"
            )
        values.append(result.stdout.strip())
    return values[0], values[1]


def build_plan(contract_path: Path, root: Path) -> dict[str, Any]:
    """Return external execution packets without claiming any run occurred."""
    contract = _load_contract(contract_path)
    _load_schemas(root, contract)
    suite = _load_suite(root, contract)
    return {
        "schema_version": "2.0.0",
        "artifact_class": "external_model_execution_plan",
        "is_model_run_evidence": False,
        "contract_id": contract["contract_id"],
        "schemas": contract["schemas"],
        "suite": contract["suite"],
        "result_path": contract["result_path"],
        "subjects": contract["subjects"],
        "runtime_requirements": contract["runtime"],
        "evaluation_requirements": contract["evaluation"],
        "authentication_requirements": contract["authentication_policy"],
        "instructions": [
            "Run every case in a fresh Claude Code process from a clean checkout of the exact subject.",
            "Explicitly invoke /claude-ads:ads for every scenario on both subjects; do not rely on global natural skill selection.",
            "Disable mutation authority and do not reuse conversation state between cases.",
            "Retain raw responses privately; record their exact UTF-8 SHA-256 values.",
            "Use a separate human or model evaluator and the rubric text exactly as pinned here.",
            "Have the external runner and evaluator sign exact bindings with separate externally trusted Ed25519 keys.",
            "Provision trust and implementation-principal exclusions through environment JSON; repository-local trust roots are forbidden.",
            "Pass both private evidence files to assess; never treat this plan as run evidence.",
        ],
        "task_packets": [
            {
                "case_id": case["id"],
                "prompt": case["prompt"],
                "prompt_sha256": _sha256_text(case["prompt"]),
                "expected_skill": case["expected_skill"],
                "risk": case["risk"],
                "required_behaviors": case["required_behaviors"],
                "forbidden_behaviors": case["forbidden_behaviors"],
                "skill_invocation": {
                    "entrypoint": contract["runtime"]["skill_entrypoint"],
                    "mode": contract["runtime"]["invocation_mode"],
                },
            }
            for case in suite
        ],
    }


def assess(
    contract_path: Path,
    root: Path,
    candidate_path: Path | None,
    baseline_path: Path | None,
    expected_candidate_commit: str,
    expected_candidate_tree: str,
    *,
    trust_bundle_json: str | None = None,
    implementation_principals_json: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Deterministically assess external runs; return a fail-closed report."""
    contract = _load_contract(contract_path)
    _load_schemas(root, contract)
    suite = _load_suite(root, contract)
    checks = [
        {
            "id": "contract-integrity",
            "status": "pass",
            "evidence_class": "local_deterministic_check",
            "detail": "Contract structure and fail-closed policy validated.",
        },
        {
            "id": "suite-integrity",
            "status": "pass",
            "evidence_class": "local_deterministic_check",
            "detail": "Suite SHA-256, case count, IDs, risks, and rubrics validated.",
        },
    ]
    blockers: list[str] = []
    validated: dict[str, dict[str, Any] | None] = {"candidate": None, "retained_v1": None}
    summaries: dict[str, dict[str, Any]] = {}
    evidence_hashes: dict[str, str | None] = {"candidate": None, "retained_v1": None}
    paths = {"candidate": candidate_path, "retained_v1": baseline_path}
    for role, path in paths.items():
        check_id = "candidate-evidence-integrity" if role == "candidate" else "retained-v1-evidence-integrity"
        if path is None:
            error = "external model-run evidence is missing"
            summaries[role] = _missing_summary(role, "missing", error)
            blockers.append(error if role == "candidate" else f"retained-v1 {error}")
            checks.append(
                {
                    "id": check_id,
                    "status": "fail",
                    "evidence_class": "local_deterministic_check",
                    "detail": error,
                }
            )
            continue
        try:
            payload = _read_json(path)
            evidence_hashes[role] = _sha256_file(path)
            try:
                auth_context = load_external_trust(
                    trust_bundle_json=trust_bundle_json,
                    implementation_principals_json=implementation_principals_json,
                    now=now,
                )
            except ModelEvidenceAuthError as exc:
                raise EvaluationContractError(f"external model-evidence trust invalid: {exc}") from exc
            result = _validate_external_run(
                payload,
                role,
                contract,
                suite,
                expected_candidate_commit,
                expected_candidate_tree,
                auth_context,
            )
        except EvaluationContractError as exc:
            error = str(exc)
            summaries[role] = _missing_summary(role, "invalid", error)
            blockers.append(f"{role} evidence invalid: {error}")
            checks.append(
                {
                    "id": check_id,
                    "status": "fail",
                    "evidence_class": "local_deterministic_check",
                    "detail": error,
                }
            )
        else:
            validated[role] = result
            summaries[role] = result["summary"]
            checks.append(
                {
                    "id": check_id,
                    "status": "pass",
                    "evidence_class": "local_deterministic_check",
                    "detail": "External provenance, runtime, subject, hashes, coverage, and rubric shape validated.",
                }
            )

    regressions: list[str] = []
    comparison_status = "not_evaluated"
    candidate = validated["candidate"]
    baseline = validated["retained_v1"]
    if candidate is not None and baseline is not None:
        candidate_runtime = candidate["payload"]["runtime"]
        baseline_runtime = baseline["payload"]["runtime"]
        parity_fields = ("cli_version", "provider", "model_id", "model_snapshot")
        mismatches = [
            field for field in parity_fields if candidate_runtime[field] != baseline_runtime[field]
        ]
        if candidate["payload"]["run_id"] == baseline["payload"]["run_id"]:
            mismatches.append("run_id")
        if candidate["payload"]["subject"]["artifact_sha256"] == baseline["payload"]["subject"]["artifact_sha256"]:
            mismatches.append("artifact_sha256")
        if mismatches:
            comparison_status = "fail"
            blockers.append(f"candidate/baseline comparison parity failed: {', '.join(mismatches)}")
            checks.append(
                {
                    "id": "comparison-integrity",
                    "status": "fail",
                    "evidence_class": "local_deterministic_check",
                    "detail": f"Comparison fields differ or collide: {', '.join(mismatches)}.",
                }
            )
        else:
            regressions = [
                case["id"]
                for case in suite
                if baseline["results"][case["id"]]["passed"]
                and not candidate["results"][case["id"]]["passed"]
            ]
            comparison_status = "pass" if not regressions else "fail"
            checks.append(
                {
                    "id": "comparison-integrity",
                    "status": "pass",
                    "evidence_class": "local_deterministic_check",
                    "detail": "Candidate and retained-v1 runs used matching Claude runtime/model coordinates and distinct artifacts.",
                }
            )
    else:
        checks.append(
            {
                "id": "comparison-integrity",
                "status": "fail",
                "evidence_class": "local_deterministic_check",
                "detail": "Both valid external runs are required before comparison.",
            }
        )

    thresholds = contract["thresholds"]
    candidate_score = summaries["candidate"]["score_percent"]
    candidate_p0 = summaries["candidate"]["p0_failures"]
    baseline_score = summaries["retained_v1"]["score_percent"]
    if candidate_score is not None and candidate_score < thresholds["minimum_candidate_score_percent"]:
        blockers.append(
            f"candidate score {candidate_score}% is below {thresholds['minimum_candidate_score_percent']}%"
        )
    if candidate_p0 is not None and candidate_p0 > thresholds["maximum_p0_failures"]:
        blockers.append(
            f"candidate has {candidate_p0} P0 failures; maximum is {thresholds['maximum_p0_failures']}"
        )
    if len(regressions) > thresholds["maximum_regressions_against_retained_v1"]:
        blockers.append(
            f"candidate regressed on {len(regressions)} retained-v1 passing cases: {', '.join(regressions)}"
        )

    times: list[str] = []
    for result in validated.values():
        if result is not None:
            times.extend((result["finished_at"], result["evaluated_at"]))
    derived_at = max(times, key=lambda value: _timestamp(value, "derived_at")) if times else None
    blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": "2.0.0",
        "evidence_class": "local_deterministic_assessment",
        "contract_id": contract["contract_id"],
        "derived_at": derived_at,
        "suite": contract["suite"],
        "inputs": {
            "contract_sha256": _sha256_file(contract_path),
            "candidate_evidence_sha256": evidence_hashes["candidate"],
            "retained_v1_evidence_sha256": evidence_hashes["retained_v1"],
        },
        "local_checks": checks,
        "external_runs": {
            "candidate": summaries["candidate"],
            "retained_v1": summaries["retained_v1"],
        },
        "comparison": {
            "status": comparison_status,
            "regression_count": len(regressions) if candidate is not None and baseline is not None else None,
            "regression_case_ids": regressions,
        },
        "summary": {
            "candidate_score_percent": candidate_score,
            "candidate_p0_failures": candidate_p0,
            "retained_v1_score_percent": baseline_score,
            "regression_count": len(regressions) if candidate is not None and baseline is not None else None,
            "thresholds": thresholds,
        },
        "release_gate_satisfied": not blockers,
        "blockers": blockers,
    }


def verify_release_report(
    report_path: Path,
    contract_path: Path,
    root: Path,
    expected_candidate_commit: str,
    expected_candidate_tree: str,
    *,
    trust_bundle_json: str | None = None,
    implementation_principals_json: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate a stored passing report against the current release subject.

    This verifies the redacted assessment artifact, not the underlying private
    transcripts. Release operators retain those inputs at the SHA-256 values in
    ``report.inputs`` for independent audit or deterministic reassessment.
    """
    contract = _load_contract(contract_path)
    _load_schemas(root, contract)
    _load_suite(root, contract)
    try:
        auth_context = load_external_trust(
            trust_bundle_json=trust_bundle_json,
            implementation_principals_json=implementation_principals_json,
            now=now,
        )
    except ModelEvidenceAuthError as exc:
        raise EvaluationContractError(f"external model-evidence trust invalid: {exc}") from exc
    trusted_keys, principals, current_time, trust_bundle_sha256 = auth_context
    report = _object(_read_json(report_path), "report")
    _exact_keys(
        report,
        {
            "schema_version",
            "evidence_class",
            "contract_id",
            "derived_at",
            "suite",
            "inputs",
            "local_checks",
            "external_runs",
            "comparison",
            "summary",
            "release_gate_satisfied",
            "blockers",
        },
        "report",
    )
    if report["schema_version"] != "2.0.0":
        raise EvaluationContractError("report.schema_version must equal '2.0.0'")
    if report["evidence_class"] != "local_deterministic_assessment":
        raise EvaluationContractError("report has the wrong evidence class")
    if report["contract_id"] != contract["contract_id"]:
        raise EvaluationContractError("report.contract_id does not match")
    _timestamp(report["derived_at"], "report.derived_at")
    if dict(_object(report["suite"], "report.suite")) != dict(contract["suite"]):
        raise EvaluationContractError("report suite does not match the pinned contract")

    inputs = _object(report["inputs"], "report.inputs")
    _exact_keys(
        inputs,
        {"contract_sha256", "candidate_evidence_sha256", "retained_v1_evidence_sha256"},
        "report.inputs",
    )
    if inputs["contract_sha256"] != _sha256_file(contract_path):
        raise EvaluationContractError("report was generated from a different contract")
    for field in ("candidate_evidence_sha256", "retained_v1_evidence_sha256"):
        _digest(inputs[field], f"report.inputs.{field}")

    checks = _array(report["local_checks"], "report.local_checks")
    required_check_ids = {
        "contract-integrity",
        "suite-integrity",
        "candidate-evidence-integrity",
        "retained-v1-evidence-integrity",
        "comparison-integrity",
    }
    observed_check_ids: set[str] = set()
    for index, raw in enumerate(checks):
        check = _object(raw, f"report.local_checks[{index}]")
        _exact_keys(
            check,
            {"id", "status", "evidence_class", "detail"},
            f"report.local_checks[{index}]",
        )
        check_id = _string(check["id"], f"report.local_checks[{index}].id")
        if check_id in observed_check_ids:
            raise EvaluationContractError(f"report repeats local check {check_id}")
        observed_check_ids.add(check_id)
        if check["status"] != "pass":
            raise EvaluationContractError(f"report local check {check_id} did not pass")
        if check["evidence_class"] != "local_deterministic_check":
            raise EvaluationContractError(f"report local check {check_id} is misclassified")
        _string(check["detail"], f"report local check {check_id}.detail")
    if observed_check_ids != required_check_ids:
        raise EvaluationContractError("report local checks are incomplete or unexpected")

    run_fields = {
        "status",
        "evidence_class",
        "run_id_sha256",
        "role",
        "git_commit",
        "git_tree",
        "artifact_sha256",
        "runtime",
        "cli_version",
        "provider",
        "model_id",
        "model_snapshot",
        "skill_entrypoint",
        "invocation_mode",
        "explicit_invocation_case_count",
        "fresh_process_per_case",
        "conversation_reuse",
        "mutation_authority",
        "case_count",
        "passed",
        "failed",
        "score_percent",
        "p0_failures",
        "failed_case_ids",
        "receipt_sha256",
        "authentication",
    }
    external = _object(report["external_runs"], "report.external_runs")
    _exact_keys(external, {"candidate", "retained_v1"}, "report.external_runs")
    summaries: dict[str, Mapping[str, Any]] = {}
    for key, expected_role in (("candidate", "candidate"), ("retained_v1", "retained-v1")):
        summary = _object(external[key], f"report.external_runs.{key}")
        _exact_keys(summary, run_fields, f"report.external_runs.{key}")
        if summary["status"] != "verified" or summary["evidence_class"] != "external_model_run":
            raise EvaluationContractError(f"report external run {key} is not verified model evidence")
        if (
            summary["role"] != expected_role
            or summary["runtime"] != "claude-code"
            or summary["provider"] != "anthropic"
            or summary["skill_entrypoint"] != contract["runtime"]["skill_entrypoint"]
            or summary["invocation_mode"] != contract["runtime"]["invocation_mode"]
            or summary["fresh_process_per_case"] is not True
            or summary["conversation_reuse"] is not False
            or summary["mutation_authority"] != "none"
        ):
            raise EvaluationContractError(f"report external run {key} has invalid role/runtime")
        for field in ("run_id_sha256", "artifact_sha256", "receipt_sha256"):
            _digest(summary[field], f"report.external_runs.{key}.{field}")
        commit = _digest(summary["git_commit"], f"report.external_runs.{key}.git_commit", GIT_RE)
        tree = _digest(summary["git_tree"], f"report.external_runs.{key}.git_tree", GIT_RE)
        if key == "candidate":
            if commit != expected_candidate_commit or tree != expected_candidate_tree:
                raise EvaluationContractError("stored report is stale for the candidate commit/tree")
        else:
            baseline = contract["subjects"]["retained_v1"]
            if commit != baseline["git_commit"] or tree != baseline["git_tree"]:
                raise EvaluationContractError("stored report does not use the pinned retained-v1 subject")
        for field in ("cli_version", "model_id", "model_snapshot"):
            _string(summary[field], f"report.external_runs.{key}.{field}")
        count = _integer(summary["case_count"], f"report.external_runs.{key}.case_count", minimum=1)
        explicit_count = _integer(
            summary["explicit_invocation_case_count"],
            f"report.external_runs.{key}.explicit_invocation_case_count",
            minimum=1,
        )
        passed = _integer(summary["passed"], f"report.external_runs.{key}.passed")
        failed = _integer(summary["failed"], f"report.external_runs.{key}.failed")
        p0 = _integer(summary["p0_failures"], f"report.external_runs.{key}.p0_failures")
        if (
            count != contract["suite"]["case_count"]
            or explicit_count != count
            or passed + failed != count
            or p0 > failed
        ):
            raise EvaluationContractError(f"report external run {key} counts are inconsistent")
        score = summary["score_percent"]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise EvaluationContractError(f"report external run {key} score is invalid")
        if score != round(100 * passed / count, 2):
            raise EvaluationContractError(f"report external run {key} score is not derived from counts")
        failed_ids = _array(summary["failed_case_ids"], f"report.external_runs.{key}.failed_case_ids")
        if len(failed_ids) != failed or len(set(failed_ids)) != len(failed_ids):
            raise EvaluationContractError(f"report external run {key} failed IDs are inconsistent")
        authentication = _object(summary["authentication"], f"report.external_runs.{key}.authentication")
        _exact_keys(
            authentication,
            {"trust_bundle_sha256", "runner", "evaluator"},
            f"report.external_runs.{key}.authentication",
        )
        if authentication["trust_bundle_sha256"] != trust_bundle_sha256:
            raise EvaluationContractError(f"report external run {key} uses a different trust bundle")
        evidence_role = expected_role
        try:
            runner_auth = verify_envelope(
                authentication["runner"],
                expected_role="runner",
                evidence_role=evidence_role,
                trusted_keys=trusted_keys,
                implementation_principals=principals,
                now=current_time,
            )
            evaluator_auth = verify_envelope(
                authentication["evaluator"],
                expected_role="evaluator",
                evidence_role=evidence_role,
                trusted_keys=trusted_keys,
                implementation_principals=principals,
                now=current_time,
            )
        except ModelEvidenceAuthError as exc:
            raise EvaluationContractError(f"report external run {key} authentication invalid: {exc}") from exc
        if runner_auth["signer_id"] == evaluator_auth["signer_id"] or runner_auth["key_id"] == evaluator_auth["key_id"]:
            raise EvaluationContractError(f"report external run {key} reuses runner/evaluator identity or key")
        runner_binding = _object(runner_auth["binding"], f"report.external_runs.{key}.runner.binding")
        evaluator_binding = _object(evaluator_auth["binding"], f"report.external_runs.{key}.evaluator.binding")
        if (
            runner_binding.get("contract_id") != contract["contract_id"]
            or runner_binding.get("evidence_role") != evidence_role
            or runner_binding.get("run_id_sha256") != summary["run_id_sha256"]
            or runner_binding.get("suite_sha256") != contract["suite"]["sha256"]
            or runner_binding.get("subject")
            != {
                "git_commit": summary["git_commit"],
                "git_tree": summary["git_tree"],
                "artifact_sha256": summary["artifact_sha256"],
            }
        ):
            raise EvaluationContractError(f"report external run {key} runner binding disagrees with summary")
        if (
            runner_binding.get("case_count") != count
            or runner_binding.get("explicit_invocation_case_count") != count
        ):
            raise EvaluationContractError(
                f"report external run {key} does not bind explicit invocation for every case"
            )
        bound_runtime = _object(runner_binding.get("runtime"), f"report.external_runs.{key}.runner.runtime")
        for runtime_field in (
            "family",
            "cli_version",
            "provider",
            "model_id",
            "model_snapshot",
            "skill_entrypoint",
            "invocation_mode",
            "fresh_process_per_case",
            "conversation_reuse",
        ):
            summary_field = "runtime" if runtime_field == "family" else runtime_field
            if bound_runtime.get(runtime_field) != summary[summary_field]:
                raise EvaluationContractError(f"report external run {key} signed runtime disagrees on {runtime_field}")
        if bound_runtime.get("skill_loaded") is not True:
            raise EvaluationContractError(f"report external run {key} did not sign a loaded skill")
        bound_execution = _object(runner_binding.get("execution"), f"report.external_runs.{key}.runner.execution")
        if (
            bound_execution.get("mutation_authority") != summary["mutation_authority"]
            or bound_execution.get("receipt_sha256") != summary["receipt_sha256"]
            or bound_execution.get("executor_identity") != runner_auth["signer_id"]
            or bound_execution.get("clean_checkout") is not True
        ):
            raise EvaluationContractError(f"report external run {key} signed execution disagrees with summary")
        bound_result = {
            "case_count": summary["case_count"],
            "passed": summary["passed"],
            "failed": summary["failed"],
            "score_percent": summary["score_percent"],
            "p0_failures": summary["p0_failures"],
            "failed_case_ids": summary["failed_case_ids"],
        }
        if (
            evaluator_binding.get("contract_id") != contract["contract_id"]
            or evaluator_binding.get("evidence_role") != evidence_role
            or evaluator_binding.get("run_id_sha256") != summary["run_id_sha256"]
            or evaluator_binding.get("runner_binding_sha256") != sha256_json(runner_binding)
            or evaluator_binding.get("rubric_id") != contract["evaluation"]["rubric_id"]
            or evaluator_binding.get("result") != bound_result
        ):
            raise EvaluationContractError(f"report external run {key} evaluator binding disagrees with summary")
        bound_evaluator = _object(evaluator_binding.get("evaluator"), f"report.external_runs.{key}.evaluator.identity")
        if (
            bound_evaluator.get("identity") != evaluator_auth["signer_id"]
            or bound_evaluator.get("identity") == bound_execution.get("executor_identity")
            or bound_evaluator.get("kind") not in contract["evaluation"]["accepted_evaluator_kinds"]
            or bound_evaluator.get("independent_from_subject_run") is not True
        ):
            raise EvaluationContractError(f"report external run {key} evaluator signer identity disagrees")
        finished_at = _timestamp(bound_execution.get("finished_at"), f"report.external_runs.{key}.execution.finished_at")
        evaluated_at = _timestamp(bound_evaluator.get("evaluated_at"), f"report.external_runs.{key}.evaluator.evaluated_at")
        runner_signed_at = _timestamp(runner_auth["signed_at"], f"report.external_runs.{key}.runner.signed_at")
        evaluator_signed_at = _timestamp(evaluator_auth["signed_at"], f"report.external_runs.{key}.evaluator.signed_at")
        if not finished_at <= runner_signed_at <= evaluator_signed_at or not finished_at <= evaluated_at <= evaluator_signed_at:
            raise EvaluationContractError(f"report external run {key} signed chronology is invalid")
        summaries[key] = summary

    if summaries["candidate"]["artifact_sha256"] == summaries["retained_v1"]["artifact_sha256"]:
        raise EvaluationContractError("candidate and retained-v1 report subjects are identical")
    for field in ("cli_version", "provider", "model_id", "model_snapshot"):
        if summaries["candidate"][field] != summaries["retained_v1"][field]:
            raise EvaluationContractError(f"candidate and retained-v1 {field} differ")

    comparison = _object(report["comparison"], "report.comparison")
    _exact_keys(comparison, {"status", "regression_count", "regression_case_ids"}, "report.comparison")
    if comparison != {"status": "pass", "regression_count": 0, "regression_case_ids": []}:
        raise EvaluationContractError("stored report comparison did not pass without regressions")

    summary = _object(report["summary"], "report.summary")
    _exact_keys(
        summary,
        {
            "candidate_score_percent",
            "candidate_p0_failures",
            "retained_v1_score_percent",
            "regression_count",
            "thresholds",
        },
        "report.summary",
    )
    if dict(_object(summary["thresholds"], "report.summary.thresholds")) != dict(contract["thresholds"]):
        raise EvaluationContractError("stored report thresholds do not match the contract")
    if summary["candidate_score_percent"] != summaries["candidate"]["score_percent"]:
        raise EvaluationContractError("report candidate score summary is inconsistent")
    if summary["candidate_p0_failures"] != summaries["candidate"]["p0_failures"]:
        raise EvaluationContractError("report candidate P0 summary is inconsistent")
    if summary["retained_v1_score_percent"] != summaries["retained_v1"]["score_percent"]:
        raise EvaluationContractError("report retained-v1 score summary is inconsistent")
    if summary["regression_count"] != 0:
        raise EvaluationContractError("report regression summary is inconsistent")
    thresholds = contract["thresholds"]
    if summary["candidate_score_percent"] < thresholds["minimum_candidate_score_percent"]:
        raise EvaluationContractError("stored report candidate score is below threshold")
    if summary["candidate_p0_failures"] > thresholds["maximum_p0_failures"]:
        raise EvaluationContractError("stored report has too many P0 failures")
    blockers = _array(report["blockers"], "report.blockers")
    if blockers or report["release_gate_satisfied"] is not True:
        raise EvaluationContractError("stored report does not satisfy the release gate")
    return dict(report)


def _write_json(payload: Mapping[str, Any], output: str) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output == "-":
        sys.stdout.write(text)
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("plan", help="emit external Claude Code execution packets")
    plan.add_argument("--output", default="-")

    validate = commands.add_parser("validate-run", help="validate one private external run")
    validate.add_argument("--role", choices=("candidate", "retained_v1"), required=True)
    validate.add_argument("--evidence", type=Path, required=True)
    validate.add_argument("--candidate-ref", default="HEAD")
    validate.add_argument("--expected-candidate-commit")
    validate.add_argument("--expected-candidate-tree")

    verify = commands.add_parser("verify-report", help="verify a stored passing gate report")
    verify.add_argument("--report", type=Path, required=True)
    verify.add_argument("--candidate-ref", default="HEAD")
    verify.add_argument("--expected-candidate-commit")
    verify.add_argument("--expected-candidate-tree")

    assess_parser = commands.add_parser("assess", help="assess candidate and retained-v1 evidence")
    assess_parser.add_argument("--candidate", type=Path)
    assess_parser.add_argument("--retained-v1", dest="retained_v1", type=Path)
    assess_parser.add_argument("--candidate-ref", default="HEAD")
    assess_parser.add_argument("--expected-candidate-commit")
    assess_parser.add_argument("--expected-candidate-tree")
    assess_parser.add_argument("--output", default=str(ROOT / "evals" / "results" / "canonical-model-gate.json"))
    return parser


def _candidate_identity(args: argparse.Namespace) -> tuple[str, str]:
    if bool(args.expected_candidate_commit) != bool(args.expected_candidate_tree):
        raise EvaluationContractError(
            "--expected-candidate-commit and --expected-candidate-tree must be supplied together"
        )
    if args.expected_candidate_commit:
        commit = _digest(args.expected_candidate_commit, "expected candidate commit", GIT_RE)
        tree = _digest(args.expected_candidate_tree, "expected candidate tree", GIT_RE)
        return commit, tree
    return _git_identity(args.root, args.candidate_ref)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            _write_json(build_plan(args.contract, args.root), args.output)
            return 0
        expected_commit, expected_tree = _candidate_identity(args)
        contract = _load_contract(args.contract)
        _load_schemas(args.root, contract)
        suite = _load_suite(args.root, contract)
        if args.command == "validate-run":
            payload = _read_json(args.evidence)
            try:
                auth_context = load_external_trust()
            except ModelEvidenceAuthError as exc:
                raise EvaluationContractError(f"external model-evidence trust invalid: {exc}") from exc
            result = _validate_external_run(
                payload,
                args.role,
                contract,
                suite,
                expected_commit,
                expected_tree,
                auth_context,
            )
            summary = result["summary"]
            summary["input_sha256"] = _sha256_file(args.evidence)
            _write_json(summary, "-")
            return 0
        if args.command == "verify-report":
            report = verify_release_report(
                args.report,
                args.contract,
                args.root,
                expected_commit,
                expected_tree,
            )
            _write_json(
                {
                    "status": "valid",
                    "report_sha256": _sha256_file(args.report),
                    "candidate_commit": report["external_runs"]["candidate"]["git_commit"],
                    "release_gate_satisfied": True,
                },
                "-",
            )
            return 0
        report = assess(
            args.contract,
            args.root,
            args.candidate,
            args.retained_v1,
            expected_commit,
            expected_tree,
        )
        _write_json(report, args.output)
        return 0 if report["release_gate_satisfied"] else 1
    except EvaluationContractError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
