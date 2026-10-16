from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from claude_ads_core.cli import main
from claude_ads_core.product_status import (
    LEGACY_RELEASE_CHECK_IDS,
    ProductStatusError,
    RELEASE_CHECK_IDS,
    evaluate_product_status,
)


def _artifact_root(tmp_path: Path, repo_root: Path) -> Path:
    root = tmp_path / "repo"
    target = root / "control-plane" / "manifests"
    target.parent.mkdir(parents=True)
    shutil.copytree(repo_root / "control-plane" / "manifests", target)
    return root


def _release_report(
    repo_root: Path,
    version: str = "2.0.0",
    *,
    failed: tuple[str, ...] = (),
) -> dict:
    check_ids = LEGACY_RELEASE_CHECK_IDS if version == "1.0.0" else RELEASE_CHECK_IDS
    checks = [
        (
            {"id": check_id, "status": "fail", "error": f"{check_id} failed"}
            if check_id in failed
            else {"id": check_id, "status": "pass", "evidence": {}}
        )
        for check_id in check_ids
    ]
    subject_values = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD", "HEAD^{tree}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return {
        "schema_version": version,
        "evidence_class": "release-gate-assessment",
        "evaluated_at": "2026-07-11T00:00:00Z",
        "subject": {"commit_sha": subject_values[0], "tree_sha": subject_values[1]},
        "checks": checks,
        "release_gate_satisfied": not failed,
    }


def _write_gate(tmp_path: Path, report: dict) -> Path:
    path = tmp_path / "gate.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_current_repository_status_has_one_declared_next_blocker(repo_root: Path):
    result = evaluate_product_status(repo_root, as_of=datetime.now(timezone.utc).date())
    assert result["maturity"]["current"] == "domain-integrated"
    assert result["evidence"]["stale_load_bearing_claims"] == []
    assert result["evidence"]["unverified_load_bearing_claims"] == []
    assert len(result["scoring_profiles"]["disabled"]) == 12
    assert result["next_blocker"]["kind"] == "maturity-blocker"
    assert result["next_blocker"]["id"] == "maturity-blocker-001"
    assert result["next_blocker"]["evidence_paths"] == [
        "control-plane/manifests/maturity-status.json",
    ]


def test_stale_load_bearing_claim_deterministically_overrides_declared_blocker(
    tmp_path: Path, repo_root: Path
):
    root = _artifact_root(tmp_path, repo_root)
    path = root / "control-plane" / "manifests" / "claim-ledger.json"
    claims = json.loads(path.read_text(encoding="utf-8"))
    load_bearing = [claim for claim in claims["claims"] if claim["load_bearing"]]
    for claim in load_bearing:
        claim["verdict"] = "verified"
    load_bearing[0]["refresh_due"] = "2026-07-10"
    path.write_text(json.dumps(claims), encoding="utf-8")
    result = evaluate_product_status(root, as_of=date(2026, 7, 11))
    assert result["next_blocker"]["kind"] == "stale-load-bearing-claim"
    assert result["next_blocker"]["id"] == load_bearing[0]["id"]


def test_missing_required_maturity_input_fails_closed(tmp_path: Path, repo_root: Path):
    root = _artifact_root(tmp_path, repo_root)
    path = root / "control-plane" / "manifests" / "maturity-status.json"
    maturity = json.loads(path.read_text(encoding="utf-8"))
    maturity.pop("blockers")
    path.write_text(json.dumps(maturity), encoding="utf-8")
    with pytest.raises(ProductStatusError, match="unsupported or missing fields"):
        evaluate_product_status(root, as_of=date(2026, 7, 11))


def test_optional_release_gate_is_validated_and_summarized(tmp_path: Path, repo_root: Path):
    report = _release_report(repo_root, failed=("canonical-model-evaluation",))
    report["checks"][-3]["error"] = "model evidence missing"
    path = _write_gate(tmp_path, report)
    result = evaluate_product_status(repo_root, as_of=date(2026, 7, 11), release_gate_path=path)
    assert result["release_gate"]["failed_checks"] == [
        {"id": "canonical-model-evaluation", "error": "model evidence missing"}
    ]
    assert result["release_gate"]["evidence_path"] == "external-release-gate-report"


def test_historical_v1_release_gate_remains_readable(tmp_path: Path, repo_root: Path):
    report = _release_report(repo_root, "1.0.0", failed=("ecosystem-dispositions",))
    result = evaluate_product_status(
        repo_root,
        as_of=date(2026, 7, 11),
        release_gate_path=_write_gate(tmp_path, report),
    )
    assert result["release_gate"]["failed_checks"] == [
        {"id": "ecosystem-dispositions", "error": "ecosystem-dispositions failed"}
    ]


def test_historical_v1_release_gate_cannot_satisfy_current_gate(
    tmp_path: Path, repo_root: Path
):
    report = _release_report(repo_root, "1.0.0")
    result = evaluate_product_status(
        repo_root,
        as_of=date(2026, 7, 11),
        release_gate_path=_write_gate(tmp_path, report),
    )
    assert result["release_gate"]["release_gate_satisfied"] is False
    assert set(result["release_gate"]) == {
        "evaluated_at",
        "subject",
        "release_gate_satisfied",
        "failed_checks",
        "evidence_path",
    }


def test_current_v2_release_gate_binds_and_satisfies_exact_repository_subject(
    tmp_path: Path, repo_root: Path
):
    report = _release_report(repo_root)
    result = evaluate_product_status(
        repo_root,
        as_of=date(2026, 7, 11),
        release_gate_path=_write_gate(tmp_path, report),
    )
    assert result["release_gate"]["release_gate_satisfied"] is True
    assert result["release_gate"]["subject"] == report["subject"]


@pytest.mark.parametrize("field", ["commit_sha", "tree_sha"])
def test_release_gate_rejects_a_different_repository_subject(
    tmp_path: Path, repo_root: Path, field: str
):
    report = _release_report(repo_root)
    report["subject"][field] = "f" * 40
    with pytest.raises(ProductStatusError, match="does not match"):
        evaluate_product_status(
            repo_root,
            as_of=date(2026, 7, 11),
            release_gate_path=_write_gate(tmp_path, report),
        )


def test_release_gate_failed_check_order_is_version_canonical(
    tmp_path: Path, repo_root: Path
):
    report = _release_report(
        repo_root,
        failed=("remote-ci", "vulnerability-exception-integrity"),
    )
    report["checks"].reverse()
    result = evaluate_product_status(
        repo_root,
        as_of=date(2026, 7, 11),
        release_gate_path=_write_gate(tmp_path, report),
    )
    assert [item["id"] for item in result["release_gate"]["failed_checks"]] == [
        "vulnerability-exception-integrity",
        "remote-ci",
    ]


@pytest.mark.parametrize("version", ["0.9.0", "3.0.0"])
def test_release_gate_rejects_unknown_versions(
    tmp_path: Path, repo_root: Path, version: str
):
    report = _release_report(repo_root)
    report["schema_version"] = version
    with pytest.raises(ProductStatusError, match="schema_version"):
        evaluate_product_status(
            repo_root,
            as_of=date(2026, 7, 11),
            release_gate_path=_write_gate(tmp_path, report),
        )


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "extra"])
def test_release_gate_rejects_noncanonical_checksets(
    tmp_path: Path, repo_root: Path, mutation: str
):
    report = _release_report(repo_root)
    if mutation == "duplicate":
        report["checks"][-1] = dict(report["checks"][0])
    elif mutation == "missing":
        report["checks"].pop()
    else:
        report["checks"].append(
            {"id": "future-check", "status": "pass", "evidence": {}}
        )
    with pytest.raises(ProductStatusError, match="exactly|invalid or duplicate|coverage"):
        evaluate_product_status(
            repo_root,
            as_of=date(2026, 7, 11),
            release_gate_path=_write_gate(tmp_path, report),
        )


def test_release_gate_rejects_aggregate_disagreement(tmp_path: Path, repo_root: Path):
    report = _release_report(repo_root, failed=("remote-ci",))
    report["release_gate_satisfied"] = True
    with pytest.raises(ProductStatusError, match="disagrees"):
        evaluate_product_status(
            repo_root,
            as_of=date(2026, 7, 11),
            release_gate_path=_write_gate(tmp_path, report),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("evaluated_at", "2026-07-11T00:00:00", "offset"),
        ("subject", {"commit_sha": "bad", "tree_sha": "b" * 40}, "hashes"),
    ],
)
def test_release_gate_rejects_invalid_timestamp_or_subject(
    tmp_path: Path, repo_root: Path, field: str, value, message: str
):
    report = _release_report(repo_root)
    report[field] = value
    with pytest.raises(ProductStatusError, match=message):
        evaluate_product_status(
            repo_root,
            as_of=date(2026, 7, 11),
            release_gate_path=_write_gate(tmp_path, report),
        )


def test_repository_status_and_next_cli_are_machine_readable(repo_root: Path, capsys):
    assert main(["status", "--root", str(repo_root), "--as-of", "2026-07-11"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["evidence_class"] == "repository-artifact-status"
    assert main(["next", "--root", str(repo_root), "--as-of", "2026-07-11"]) == 0
    next_output = json.loads(capsys.readouterr().out)
    assert set(next_output) == {"schema_version", "as_of", "selection_policy", "next_blocker"}
    assert next_output["next_blocker"] == status["next_blocker"]
