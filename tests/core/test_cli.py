from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_ads_core.cli import main
from claude_ads_core.contracts import PLATFORMS
from tests.core.test_contracts import account_snapshot, registry_report_bundle


def write_json(tmp_path, name: str, payload) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_validate_command_emits_machine_readable_success(tmp_path, capsys):
    path = write_json(tmp_path, "snapshot.json", account_snapshot())
    assert main(["validate", "account-snapshot", path]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "contract": "account-snapshot",
        "path": path,
        "status": "valid",
        "validation": "structural",
    }


def test_validate_command_returns_two_and_json_error(tmp_path, capsys):
    path = write_json(tmp_path, "snapshot.json", {"schema_version": "1.0.0"})
    assert main(["validate", "account-snapshot", path]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["status"] == "invalid"
    assert "missing required" in error["error"]


def test_validate_command_dispatches_audit_worker_result(repo_root: Path, capsys):
    path = repo_root / "tests/fixtures/audit-worker-results/valid.json"
    assert main(["validate", "audit-worker-result", str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["contract"] == "audit-worker-result"
    assert output["validation"] == "structural"


def test_status_command_reports_registry_validated_bundle_status(
    tmp_path, capsys, repo_root: Path
):
    path = write_json(tmp_path, "report.json", registry_report_bundle(repo_root))
    assert main(["status", path, "--policy-root", str(repo_root)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "run_id": "run-20260711-001",
        "completeness": "complete",
        "health_score": None,
        "evidence_coverage": 0.0,
        "status": "insufficient_evidence",
    }


def test_score_command_uses_disabled_registry_profile(tmp_path, capsys, repo_root: Path):
    findings = write_json(tmp_path, "findings.json", [])
    controls = write_json(tmp_path, "controls.json", [])
    weights = write_json(tmp_path, "weights.json", {})
    assert (
        main(
            [
                "score",
                "--platform",
                "google",
                "--controls",
                controls,
                "--findings",
                findings,
                "--weights",
                weights,
                "--policy-root",
                str(repo_root),
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "categories": [],
        "evidence_coverage": 0.0,
        "health_score": None,
        "status": "insufficient_evidence",
    }


@pytest.mark.parametrize("platform", sorted(PLATFORMS))
def test_public_score_fails_closed_for_every_production_profile(
    tmp_path, capsys, repo_root: Path, platform: str
):
    findings = write_json(tmp_path, f"{platform}-findings.json", [])
    assert (
        main(
            [
                "score",
                "--platform",
                platform,
                "--findings",
                findings,
                "--policy-root",
                str(repo_root),
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["health_score"] is None
    assert output["evidence_coverage"] == 0.0


def test_score_command_rejects_custom_compatibility_inputs(
    tmp_path, capsys, repo_root: Path
):
    findings = write_json(tmp_path, "findings.json", [])
    controls = write_json(tmp_path, "controls.json", [{"control_id": "invented"}])
    assert (
        main(
            [
                "score",
                "--platform",
                "google",
                "--controls",
                controls,
                "--findings",
                findings,
                "--policy-root",
                str(repo_root),
            ]
        )
        == 2
    )
    error = json.loads(capsys.readouterr().err)
    assert "must exactly match" in error["error"]


def test_legacy_score_flags_without_platform_return_json_error(
    tmp_path, capsys, repo_root: Path
):
    findings = write_json(tmp_path, "findings.json", [])
    controls = write_json(tmp_path, "controls.json", [])
    weights = write_json(tmp_path, "weights.json", {})
    assert (
        main(
            [
                "score",
                "--controls",
                controls,
                "--findings",
                findings,
                "--weights",
                weights,
                "--policy-root",
                str(repo_root),
            ]
        )
        == 2
    )
    error = json.loads(capsys.readouterr().err)
    assert error["status"] == "invalid"
    assert "--platform is required" in error["error"]


def test_score_command_rejects_noncanonical_finding(tmp_path, capsys, repo_root: Path):
    from tests.core.test_scoring_engine import finding

    findings = write_json(tmp_path, "findings.json", [finding("invented", "pass")])
    assert (
        main(
            [
                "score",
                "--platform",
                "google",
                "--findings",
                findings,
                "--policy-root",
                str(repo_root),
            ]
        )
        == 2
    )
    assert "non-canonical" in json.loads(capsys.readouterr().err)["error"]


def test_portfolio_recomputes_registry_scores(tmp_path, capsys, repo_root: Path):
    path = write_json(
        tmp_path,
        "portfolio.json",
        [
            {
                "account_id": "acct-1",
                "platform": "google",
                "findings": [],
                "spend": 100,
                "window": {"start": "2026-06-01", "end": "2026-06-30"},
            }
        ],
    )
    assert main(["portfolio", path, "--policy-root", str(repo_root)]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "accounts": [],
        "health_score": None,
        "status": "insufficient_evidence",
        "weighting": "none",
    }


def test_portfolio_rejects_caller_supplied_health(tmp_path, capsys, repo_root: Path):
    path = write_json(
        tmp_path,
        "portfolio.json",
        [
            {
                "account_id": "acct-1",
                "platform": "google",
                "findings": [],
                "health_score": 100,
            }
        ],
    )
    assert main(["portfolio", path, "--policy-root", str(repo_root)]) == 2
    assert "unverifiable caller fields" in json.loads(capsys.readouterr().err)["error"]


def test_status_rejects_forged_non_null_health(tmp_path, capsys, repo_root: Path):
    bundle = registry_report_bundle(repo_root)
    bundle["scoring"]["health_score"] = 100.0
    path = write_json(tmp_path, "forged-report.json", bundle)
    assert main(["status", path, "--policy-root", str(repo_root)]) == 2
    assert "does not match canonical" in json.loads(capsys.readouterr().err)["error"]


def test_status_rejects_complete_bundle_with_failed_platform_worker(
    tmp_path, capsys, repo_root: Path
):
    bundle = registry_report_bundle(repo_root)
    bundle["run_manifest"]["worker_status"] = {"google": "failed"}
    path = write_json(tmp_path, "contradictory-report.json", bundle)
    assert main(["status", path, "--policy-root", str(repo_root)]) == 2
    assert "unfinished or failed" in json.loads(capsys.readouterr().err)["error"]


def test_ingest_export_command_emits_normalized_snapshot(capsys):
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "exports" / "google.csv"
    assert main(["ingest-export", "--platform", "google", str(fixture)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["schema_version"] == "1.0.0"
    assert output["account"]["platform"] == "google"
    assert output["spend"] == 42.5
