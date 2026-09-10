"""Canonical Claude model-evaluation and retained-v1 gate tests."""

from __future__ import annotations

from copy import deepcopy
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from evals.model_eval_gate import (
    EvaluationContractError,
    assess,
    build_plan,
    verify_release_report,
    _evaluator_binding,
    _runner_binding,
)
from evals.model_evidence_auth import canonical_bytes


CANDIDATE_COMMIT = "1" * 40
CANDIDATE_TREE = "2" * 40
BASELINE_COMMIT = "86690b668e2cc616e03bdb2f1a28aa951d6c29ad"
BASELINE_TREE = "92680a710c5366ba875aad92b12cb129369ab6b3"
NOW = datetime(2026, 7, 11, 13, 0, tzinfo=timezone.utc)
RUNNER_KEY = Ed25519PrivateKey.generate()
EVALUATOR_KEY = Ed25519PrivateKey.generate()


def _public_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


TRUST = json.dumps(
    {
        "schema_version": "1.0.0",
        "evidence_class": "external_model_eval_trust_bundle",
        "provenance": "external-release-operator",
        "issued_at": "2026-07-11T09:00:00Z",
        "keys": [
            {
                "signer_id": "external-runner",
                "key_id": "runner-key",
                "public_key_b64url": _public_b64(RUNNER_KEY),
                "role": "runner",
                "evidence_roles": ["candidate", "retained-v1"],
                "valid_from": "2026-07-11T00:00:00Z",
                "valid_until": "2026-07-25T00:00:00Z",
            },
            {
                "signer_id": "external-evaluator",
                "key_id": "evaluator-key",
                "public_key_b64url": _public_b64(EVALUATOR_KEY),
                "role": "evaluator",
                "evidence_roles": ["candidate", "retained-v1"],
                "valid_from": "2026-07-11T00:00:00Z",
                "valid_until": "2026-07-25T00:00:00Z",
            },
        ],
    }
)
PRINCIPALS = json.dumps(["implementation-agent"])


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _suite(repo_root: Path) -> list[dict]:
    return json.loads((repo_root / "evals" / "v2-behavior-evals.json").read_text())


def _case_evidence(case: dict, *, passed: bool = True) -> dict:
    response_parts = [f"Required: {behavior}" for behavior in case["required_behaviors"]]
    response = "\n".join(response_parts) + "\nNo account mutation was performed."
    required_results = []
    for index, behavior in enumerate(case["required_behaviors"]):
        observed = passed or index > 0
        result = {
            "behavior": behavior,
            "observed": observed,
            "rationale": "The observable response was graded against this exact rubric item.",
        }
        if observed:
            result["evidence_excerpt"] = f"Required: {behavior}"
        required_results.append(result)
    return {
        "case_id": case["id"],
        "invocation_id": f"invocation-{case['id']}",
        "prompt_sha256": _sha(case["prompt"]),
        "response_sha256": _sha(response),
        "response": response,
        "skill_invocation": {
            "entrypoint": "/claude-ads:ads",
            "mode": "explicit-plugin-skill",
        },
        "required_behavior_results": required_results,
        "forbidden_behavior_results": [
            {
                "behavior": behavior,
                "observed": False,
                "rationale": "The independent evaluator did not observe this behavior.",
            }
            for behavior in case["forbidden_behaviors"]
        ],
    }


def _run_evidence(
    repo_root: Path,
    role: str,
    *,
    failed_ids: set[str] | None = None,
    model_snapshot: str = "claude-model-snapshot-2026-07-01",
) -> dict:
    failed_ids = failed_ids or set()
    candidate = role == "candidate"
    run = {
        "schema_version": "2.0.0",
        "evidence_class": "external_model_run",
        "contract_id": "claude-ads-v2-canonical-model-gate",
        "run_id": f"canonical-{role}-run",
        "role": role,
        "suite": {
            "path": "evals/v2-behavior-evals.json",
            "sha256": "c535b471fa862a14518e0a86cd39a1081969cb208443af01fbcce1046f36d052",
            "case_count": 24,
        },
        "subject": {
            "product_version": "2.0.0" if candidate else "1.8.1",
            "git_ref": "v2" if candidate else "v1.8.1",
            "git_commit": CANDIDATE_COMMIT if candidate else BASELINE_COMMIT,
            "git_tree": CANDIDATE_TREE if candidate else BASELINE_TREE,
            "artifact_sha256": ("a" if candidate else "b") * 64,
        },
        "runtime": {
            "family": "claude-code",
            "cli_version": "2.1.207",
            "provider": "anthropic",
            "model_id": "claude-model",
            "model_snapshot": model_snapshot,
            "skill_entrypoint": "/claude-ads:ads",
            "invocation_mode": "explicit-plugin-skill",
            "fresh_process_per_case": True,
            "conversation_reuse": False,
            "skill_loaded": True,
        },
        "execution": {
            "started_at": "2026-07-11T10:00:00Z",
            "finished_at": "2026-07-11T11:00:00Z",
            "executor_identity": "external-runner",
            "environment_id": f"isolated-{role}",
            "clean_checkout": True,
            "mutation_authority": "none",
            "receipt": f"private-run-receipt-{role}",
        },
        "evaluator": {
            "kind": "human",
            "identity": "external-evaluator",
            "rubric_id": "claude-ads-observable-behavior-v1",
            "independent_from_subject_run": True,
            "evaluated_at": "2026-07-11T12:00:00Z",
            "receipt": f"private-review-receipt-{role}",
        },
        "cases": [
            _case_evidence(case, passed=case["id"] not in failed_ids)
            for case in _suite(repo_root)
        ],
    }
    passed_count = 24 - len(failed_ids)
    result = {
        "case_count": 24,
        "passed": passed_count,
        "failed": len(failed_ids),
        "score_percent": round(100 * passed_count / 24, 2),
        "p0_failures": sum(
            case["risk"] == "P0" and case["id"] in failed_ids for case in _suite(repo_root)
        ),
        "failed_case_ids": [case["id"] for case in _suite(repo_root) if case["id"] in failed_ids],
    }
    runner_unsigned = {
        "signer_id": "external-runner",
        "key_id": "runner-key",
        "role": "runner",
        "signed_at": "2026-07-11T11:05:00Z",
        "binding": _runner_binding(run),
    }
    evaluator_unsigned = {
        "signer_id": "external-evaluator",
        "key_id": "evaluator-key",
        "role": "evaluator",
        "signed_at": "2026-07-11T12:05:00Z",
        "binding": _evaluator_binding(run, result),
    }
    run["authentication"] = {
        "runner": {
            **runner_unsigned,
            "signature_b64url": base64.urlsafe_b64encode(
                RUNNER_KEY.sign(canonical_bytes(runner_unsigned))
            ).decode().rstrip("="),
        },
        "evaluator": {
            **evaluator_unsigned,
            "signature_b64url": base64.urlsafe_b64encode(
                EVALUATOR_KEY.sign(canonical_bytes(evaluator_unsigned))
            ).decode().rstrip("="),
        },
    }
    return run


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _assess(repo_root: Path, tmp_path: Path, candidate: dict, baseline: dict) -> dict:
    return assess(
        repo_root / "evals" / "model-eval-contract.json",
        repo_root,
        _write(tmp_path / "candidate-private.json", candidate),
        _write(tmp_path / "baseline-private.json", baseline),
        CANDIDATE_COMMIT,
        CANDIDATE_TREE,
        trust_bundle_json=TRUST,
        implementation_principals_json=PRINCIPALS,
        now=NOW,
    )


def _assess_with_auth(
    repo_root: Path,
    tmp_path: Path,
    candidate: dict,
    *,
    trust: str | None = TRUST,
    principals: str | None = PRINCIPALS,
    now: datetime = NOW,
) -> dict:
    return assess(
        repo_root / "evals" / "model-eval-contract.json",
        repo_root,
        _write(tmp_path / "candidate-auth.json", candidate),
        _write(tmp_path / "baseline-auth.json", _run_evidence(repo_root, "retained-v1")),
        CANDIDATE_COMMIT,
        CANDIDATE_TREE,
        trust_bundle_json=trust,
        implementation_principals_json=principals,
        now=now,
    )


def test_execution_plan_is_pinned_and_explicitly_not_run_evidence(repo_root):
    plan = build_plan(repo_root / "evals" / "model-eval-contract.json", repo_root)
    candidate_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD^{commit}"], cwd=repo_root, text=True
    ).strip()
    candidate_tree = subprocess.check_output(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root, text=True
    ).strip()
    assert plan["artifact_class"] == "external_model_execution_plan"
    assert plan["is_model_run_evidence"] is False
    assert plan["subjects"]["candidate"]["git_commit"] == candidate_commit
    assert plan["subjects"]["candidate"]["git_tree"] == candidate_tree
    assert plan["subjects"]["retained_v1"]["git_commit"] == BASELINE_COMMIT
    assert plan["subjects"]["retained_v1"]["git_tree"] == BASELINE_TREE
    assert len(plan["task_packets"]) == 24
    assert plan["suite"]["sha256"] == _sha(
        (repo_root / "evals" / "v2-behavior-evals.json").read_text(encoding="utf-8")
    )
    for packet, case in zip(plan["task_packets"], _suite(repo_root), strict=True):
        assert packet["case_id"] == case["id"]
        assert packet["prompt_sha256"] == _sha(case["prompt"])
        assert packet["required_behaviors"] == case["required_behaviors"]
        assert packet["forbidden_behaviors"] == case["forbidden_behaviors"]
        assert packet["skill_invocation"] == {
            "entrypoint": "/claude-ads:ads",
            "mode": "explicit-plugin-skill",
        }


def test_every_case_requires_explicit_namespaced_plugin_entrypoint(repo_root, tmp_path):
    candidate = _run_evidence(repo_root, "candidate")
    candidate["cases"][0]["skill_invocation"] = {
        "entrypoint": "/ads",
        "mode": "natural-skill-selection",
    }
    report = _assess_with_auth(repo_root, tmp_path, candidate)
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert "explicitly invoke /claude-ads:ads" in report["external_runs"]["candidate"]["error"]


def test_missing_external_runs_fail_closed_without_local_substitution(repo_root):
    report = assess(
        repo_root / "evals" / "model-eval-contract.json",
        repo_root,
        None,
        None,
        CANDIDATE_COMMIT,
        CANDIDATE_TREE,
    )
    assert report["evidence_class"] == "local_deterministic_assessment"
    assert report["release_gate_satisfied"] is False
    assert report["external_runs"]["candidate"]["status"] == "missing"
    assert report["external_runs"]["retained_v1"]["status"] == "missing"
    assert report["comparison"]["status"] == "not_evaluated"
    assert report["summary"]["candidate_score_percent"] is None
    assert any(check["status"] == "fail" for check in report["local_checks"])


def test_complete_canonical_runs_pass_and_summary_excludes_raw_responses(repo_root, tmp_path):
    report = _assess(
        repo_root,
        tmp_path,
        _run_evidence(repo_root, "candidate"),
        _run_evidence(repo_root, "retained-v1"),
    )
    assert report["release_gate_satisfied"] is True
    assert report["blockers"] == []
    assert report["summary"] == {
        "candidate_score_percent": 100.0,
        "candidate_p0_failures": 0,
        "retained_v1_score_percent": 100.0,
        "regression_count": 0,
        "thresholds": {
            "minimum_candidate_score_percent": 90,
            "maximum_p0_failures": 0,
            "maximum_regressions_against_retained_v1": 0,
        },
    }
    assert report["comparison"] == {
        "status": "pass",
        "regression_count": 0,
        "regression_case_ids": [],
    }
    serialized = json.dumps(report)
    assert "No account mutation was performed" not in serialized
    assert '"response"' not in serialized
    assert "private-run-receipt" not in serialized
    assert "canonical-candidate-run" not in serialized
    assert len(report["external_runs"]["candidate"]["receipt_sha256"]) == 64
    assert len(report["external_runs"]["candidate"]["run_id_sha256"]) == 64


def test_candidate_regression_against_passing_v1_blocks_gate(repo_root, tmp_path):
    report = _assess(
        repo_root,
        tmp_path,
        _run_evidence(repo_root, "candidate", failed_ids={"partial-audit"}),
        _run_evidence(repo_root, "retained-v1"),
    )
    assert report["summary"]["candidate_score_percent"] == 95.83
    assert report["comparison"]["regression_case_ids"] == ["partial-audit"]
    assert report["release_gate_satisfied"] is False
    assert any("regressed" in blocker for blocker in report["blockers"])


def test_p0_failure_blocks_even_when_v1_failed_same_case_and_score_exceeds_threshold(
    repo_root, tmp_path
):
    failed = {"safety-delete"}
    report = _assess(
        repo_root,
        tmp_path,
        _run_evidence(repo_root, "candidate", failed_ids=failed),
        _run_evidence(repo_root, "retained-v1", failed_ids=failed),
    )
    assert report["comparison"]["regression_count"] == 0
    assert report["summary"]["candidate_score_percent"] == 95.83
    assert report["summary"]["candidate_p0_failures"] == 1
    assert report["release_gate_satisfied"] is False
    assert any("P0 failures" in blocker for blocker in report["blockers"])


def test_non_claude_runtime_is_invalid_external_evidence(repo_root, tmp_path):
    candidate = _run_evidence(repo_root, "candidate")
    candidate["runtime"]["family"] = "codex"
    report = _assess(
        repo_root,
        tmp_path,
        candidate,
        _run_evidence(repo_root, "retained-v1"),
    )
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert report["release_gate_satisfied"] is False
    assert any("canonical Claude Code" in blocker for blocker in report["blockers"])


def test_stale_candidate_or_unpinned_baseline_is_rejected(repo_root, tmp_path):
    candidate = _run_evidence(repo_root, "candidate")
    candidate["subject"]["git_commit"] = "3" * 40
    baseline = _run_evidence(repo_root, "retained-v1")
    baseline["subject"]["git_tree"] = "4" * 40
    report = _assess(repo_root, tmp_path, candidate, baseline)
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert report["external_runs"]["retained_v1"]["status"] == "invalid"
    assert report["release_gate_satisfied"] is False


def test_response_hash_and_evidence_excerpt_are_verified(repo_root, tmp_path):
    candidate = _run_evidence(repo_root, "candidate")
    candidate["cases"][0]["response"] += " tampered"
    report = _assess(
        repo_root,
        tmp_path,
        candidate,
        _run_evidence(repo_root, "retained-v1"),
    )
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert "response hash" in report["external_runs"]["candidate"]["error"]

    candidate = _run_evidence(repo_root, "candidate")
    candidate["cases"][0]["required_behavior_results"][0]["evidence_excerpt"] = "not in output"
    report = _assess(
        repo_root,
        tmp_path,
        candidate,
        _run_evidence(repo_root, "retained-v1"),
    )
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert "not present" in report["external_runs"]["candidate"]["error"]


def test_self_grading_and_runtime_parity_mismatch_fail_closed(repo_root, tmp_path):
    candidate = _run_evidence(repo_root, "candidate")
    candidate["evaluator"]["identity"] = candidate["execution"]["executor_identity"]
    report = _assess(
        repo_root,
        tmp_path,
        candidate,
        _run_evidence(repo_root, "retained-v1"),
    )
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert "own executor" in report["external_runs"]["candidate"]["error"]

    report = _assess(
        repo_root,
        tmp_path,
        _run_evidence(repo_root, "candidate"),
        _run_evidence(repo_root, "retained-v1", model_snapshot="different-snapshot"),
    )
    assert report["comparison"]["status"] == "fail"
    assert report["release_gate_satisfied"] is False
    assert any("model_snapshot" in blocker for blocker in report["blockers"])


def test_cli_writes_deterministic_failing_report_and_nonzero_status(repo_root, tmp_path):
    output = tmp_path / "gate.json"
    command = [
        sys.executable,
        str(repo_root / "evals" / "model_eval_gate.py"),
        "--root",
        str(repo_root),
        "assess",
        "--expected-candidate-commit",
        CANDIDATE_COMMIT,
        "--expected-candidate-tree",
        CANDIDATE_TREE,
        "--output",
        str(output),
    ]
    first = subprocess.run(command, cwd=repo_root, check=False, capture_output=True, text=True)
    first_bytes = output.read_bytes()
    second = subprocess.run(command, cwd=repo_root, check=False, capture_output=True, text=True)
    assert first.returncode == second.returncode == 1
    assert output.read_bytes() == first_bytes
    assert json.loads(first_bytes)["release_gate_satisfied"] is False


def test_stored_release_report_verification_rejects_tampering(
    repo_root, tmp_path, monkeypatch
):
    report = _assess(
        repo_root,
        tmp_path,
        _run_evidence(repo_root, "candidate"),
        _run_evidence(repo_root, "retained-v1"),
    )
    report_path = _write(tmp_path / "gate.json", report)
    monkeypatch.delenv("CLAUDE_ADS_MODEL_EVAL_TRUST_BUNDLE_JSON", raising=False)
    monkeypatch.delenv("CLAUDE_ADS_MODEL_EVAL_IMPLEMENTATION_PRINCIPALS_JSON", raising=False)
    with pytest.raises(EvaluationContractError, match="external trust input"):
        verify_release_report(
            report_path,
            repo_root / "evals" / "model-eval-contract.json",
            repo_root,
            CANDIDATE_COMMIT,
            CANDIDATE_TREE,
        )
    verified = verify_release_report(
        report_path,
        repo_root / "evals" / "model-eval-contract.json",
        repo_root,
        CANDIDATE_COMMIT,
        CANDIDATE_TREE,
        trust_bundle_json=TRUST,
        implementation_principals_json=PRINCIPALS,
        now=NOW,
    )
    assert verified["release_gate_satisfied"] is True

    tampered = deepcopy(report)
    tampered["external_runs"]["candidate"]["passed"] = 23
    tampered_path = _write(tmp_path / "tampered.json", tampered)
    try:
        verify_release_report(
            tampered_path,
            repo_root / "evals" / "model-eval-contract.json",
            repo_root,
            CANDIDATE_COMMIT,
            CANDIDATE_TREE,
            trust_bundle_json=TRUST,
            implementation_principals_json=PRINCIPALS,
            now=NOW,
        )
    except EvaluationContractError as exc:
        assert "counts" in str(exc) or "score" in str(exc)
    else:  # pragma: no cover - explicit fail-closed assertion
        raise AssertionError("tampered report unexpectedly verified")


def test_contract_schemas_are_strict_and_machine_readable(repo_root):
    run_schema = json.loads(
        (repo_root / "evals" / "schemas" / "model-run-evidence.v2.schema.json").read_text()
    )
    report_schema = json.loads(
        (repo_root / "evals" / "schemas" / "model-gate-report.v2.schema.json").read_text()
    )
    trust_schema = json.loads(
        (repo_root / "evals" / "schemas" / "model-eval-trust-bundle.v1.schema.json").read_text()
    )
    assert run_schema["additionalProperties"] is False
    assert run_schema["properties"]["evidence_class"]["const"] == "external_model_run"
    assert "authentication" in run_schema["required"]
    assert report_schema["additionalProperties"] is False
    assert report_schema["properties"]["evidence_class"]["const"] == (
        "local_deterministic_assessment"
    )
    assert "response" not in report_schema["$defs"]["runSummary"]["properties"]
    assert trust_schema["additionalProperties"] is False
    assert trust_schema["properties"]["provenance"]["const"] == "external-release-operator"


def test_forged_and_self_signed_runner_evidence_fail(repo_root, tmp_path):
    forged = _run_evidence(repo_root, "candidate")
    signature = forged["authentication"]["runner"]["signature_b64url"]
    forged["authentication"]["runner"]["signature_b64url"] = (
        ("A" if signature[0] != "A" else "B") + signature[1:]
    )
    report = _assess_with_auth(repo_root, tmp_path, forged)
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert "signature verification failed" in report["external_runs"]["candidate"]["error"]

    self_signed = _run_evidence(repo_root, "candidate")
    rogue = Ed25519PrivateKey.generate()
    envelope = self_signed["authentication"]["runner"]
    unsigned = {key: value for key, value in envelope.items() if key != "signature_b64url"}
    envelope["signature_b64url"] = base64.urlsafe_b64encode(
        rogue.sign(canonical_bytes(unsigned))
    ).decode().rstrip("=")
    report = _assess_with_auth(repo_root, tmp_path, self_signed)
    assert report["external_runs"]["candidate"]["status"] == "invalid"


def test_repo_local_missing_external_trust_and_mis_scoped_key_fail(
    repo_root, tmp_path, monkeypatch
):
    monkeypatch.delenv("CLAUDE_ADS_MODEL_EVAL_TRUST_BUNDLE_JSON", raising=False)
    monkeypatch.delenv("CLAUDE_ADS_MODEL_EVAL_IMPLEMENTATION_PRINCIPALS_JSON", raising=False)
    (tmp_path / "repo-local-trust.json").write_text(TRUST, encoding="utf-8")
    report = _assess_with_auth(
        repo_root,
        tmp_path,
        _run_evidence(repo_root, "candidate"),
        trust=None,
        principals=None,
    )
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert "external trust input" in report["external_runs"]["candidate"]["error"]

    mis_scoped = json.loads(TRUST)
    mis_scoped["keys"][0]["role"] = "evaluator"
    report = _assess_with_auth(
        repo_root,
        tmp_path,
        _run_evidence(repo_root, "candidate"),
        trust=json.dumps(mis_scoped),
    )
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert "key scope" in report["external_runs"]["candidate"]["error"]


def test_stale_signatures_and_implementation_principal_self_review_fail(repo_root, tmp_path):
    report = _assess_with_auth(
        repo_root,
        tmp_path,
        _run_evidence(repo_root, "candidate"),
        now=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert "stale" in report["external_runs"]["candidate"]["error"]

    report = _assess_with_auth(
        repo_root,
        tmp_path,
        _run_evidence(repo_root, "candidate"),
        principals=json.dumps(["implementation-agent", "external-evaluator"]),
    )
    assert report["external_runs"]["candidate"]["status"] == "invalid"
    assert "implementation principal" in report["external_runs"]["candidate"]["error"]
