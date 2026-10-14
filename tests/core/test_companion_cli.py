"""Public CLI integration for the separately enabled local workbench."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from claude_ads_core import cli
from claude_ads_core.control_registry import RegistryError
from claude_ads_core.contracts import validate_contract


ROOT = Path(__file__).resolve().parents[2]


def invoke(cwd, *args):
    # Bind exact candidate source even when cwd and environment are unrelated.
    loader = "import sys;sys.path.insert(0,sys.argv.pop(1));from claude_ads_core.cli import main;raise SystemExit(main())"
    return subprocess.run([sys.executable, "-I", "-c", loader, str(ROOT), *args], cwd=cwd, capture_output=True, text=True, timeout=30)


@pytest.mark.skipif(os.name != "posix", reason="Secure client IO requires POSIX descriptor APIs")
def test_cockpit_cli_complete_isolated_flow_from_unrelated_directory(tmp_path):
    root = tmp_path / "synthetic"
    demo = invoke(tmp_path, "cockpit", "demo", "--policy-root", str(ROOT), "--runs-root", str(root))
    assert demo.returncode == 0, demo.stderr
    setup = json.loads(demo.stdout)
    assert setup["interface_version"] == "1.0.0"
    policy = setup["policy_root"]
    doctor = invoke(tmp_path, "cockpit", "doctor", "--policy-root", policy, "--runs-root", str(root))
    assert doctor.returncode == 0
    assert len(json.loads(doctor.stdout)["profiles"]) == 12
    snapshot = invoke(tmp_path, "cockpit", "snapshot", "--policy-root", policy, "--runs-root", str(root), "--run-id", "demo-current")
    assert snapshot.returncode == 0, snapshot.stderr
    state = json.loads(snapshot.stdout)
    validate_contract("cockpit-snapshot", state)
    assert all(p["health_score"] is None and p["evidence_coverage"] == 0 for p in state["scoring"])
    compare = invoke(tmp_path, "cockpit", "compare", "--policy-root", policy, "--runs-root", str(root), "--run-id", "demo-current", "--baseline-id", "demo-baseline")
    assert compare.returncode == 0, compare.stderr
    validate_contract("cockpit-snapshot", json.loads(compare.stdout))
    render = invoke(tmp_path, "cockpit", "action", "--policy-root", policy, "--runs-root", str(root), "--run-id", "demo-current", "--operation", "render-report", "--format", "html", "--expected-fingerprint", state["fingerprint"])
    assert render.returncode == 0, render.stderr
    receipt = json.loads(render.stdout)
    validate_contract("cockpit-action-receipt", receipt)
    assert receipt["outcome"] == "succeeded"
    assert (root / "demo-current" / receipt["outputs"][0]["path"]).is_file()


@pytest.mark.parametrize("bad_date", ["20261008", "2026-99-01", "bad-date"])
def test_cockpit_cli_requires_canonical_evaluation_date(capsys, bad_date):
    assert cli.main(["cockpit", "snapshot", "--policy-root", str(ROOT), "--runs-root", "unused", "--run-id", "r", "--as-of", bad_date]) == 2
    reply = json.loads(capsys.readouterr().err)
    assert reply["error"] == "--as-of must be an ISO 8601 date."


@pytest.mark.parametrize("error_type", [RegistryError, OSError, RecursionError])
def test_cockpit_cli_all_error_routes_are_bounded(monkeypatch, capsys, error_type):
    from claude_ads_core import cockpit
    def fail(*args):
        raise error_type("SENSITIVE-CLIENT-PAYLOAD /private/customer/config")
    monkeypatch.setattr(cockpit, "doctor", fail)
    assert cli.main(["cockpit", "doctor", "--policy-root", str(ROOT)]) == 2
    reply = capsys.readouterr()
    assert "SENSITIVE" not in reply.err and "/private" not in reply.err
    assert not reply.out
    assert json.loads(reply.err)["status"] == "invalid"


def test_cockpit_invalid_policy_does_not_select_unrelated_cwd(tmp_path):
    result = invoke(tmp_path, "cockpit", "doctor", "--policy-root", str(tmp_path / "missing"))
    assert result.returncode == 2
    assert json.loads(result.stderr)["error"] == "Cannot resolve Cockpit policy resources; supply a valid --policy-root."
    assert str(tmp_path) not in result.stderr


def test_new_contracts_are_public_validate_choices():
    parser = cli.build_parser()
    for name in ("cockpit-index", "cockpit-snapshot", "cockpit-action-receipt"):
        args = parser.parse_args(["validate", name, "fixture.json"])
        assert args.contract == name


def test_canonical_numeric_validation_bounds_huge_integer():
    from claude_ads_core.contracts import ContractError, _require_number
    with pytest.raises(ContractError, match="must be finite"):
        _require_number(10 ** 400, "$.spend")


@pytest.mark.skipif(os.name != "posix", reason="Secure client IO requires POSIX descriptor APIs")
def test_cockpit_action_exit_zero_means_a_receipt_and_the_outcome_field_carries_the_result(tmp_path):
    root = tmp_path / "synthetic"
    setup = json.loads(invoke(tmp_path, "cockpit", "demo", "--policy-root", str(ROOT), "--runs-root", str(root)).stdout)
    policy = setup["policy_root"]

    def act(run, operation, fingerprint, *extra):
        return invoke(tmp_path, "cockpit", "action", "--policy-root", policy, "--runs-root", str(root), "--run-id", run, "--operation", operation, "--expected-fingerprint", fingerprint, *extra)

    # blocked: a stale fingerprint on a readable run still produces a receipt
    stale = act("demo-current", "validate-run", "0" * 64)
    assert stale.returncode == 0, stale.stderr
    blocked = json.loads(stale.stdout)
    validate_contract("cockpit-action-receipt", blocked)
    assert blocked["outcome"] == "blocked"
    # failed: the requested check ran and the input did not validate
    state = json.loads(invoke(tmp_path, "cockpit", "snapshot", "--policy-root", policy, "--runs-root", str(root), "--run-id", "demo-needs-input").stdout)
    failed = act("demo-needs-input", "validate-input", state["fingerprint"], "--input-id", "keyword-evidence")
    assert failed.returncode == 0, failed.stderr
    receipt = json.loads(failed.stdout)
    validate_contract("cockpit-action-receipt", receipt)
    assert receipt["outcome"] == "failed"
    # Requests rejected before any receipt exists exit 2 with no stdout.
    rejected = act("../escape", "validate-run", "0" * 64)
    assert rejected.returncode == 2 and not rejected.stdout
    assert json.loads(rejected.stderr)["status"] == "invalid"


@pytest.mark.skipif(os.name != "posix", reason="Secure client IO requires POSIX descriptor APIs")
def test_cockpit_cli_refuses_a_lifecycle_expired_run_without_writing(tmp_path):
    root = tmp_path / "synthetic"
    setup = json.loads(invoke(tmp_path, "cockpit", "demo", "--policy-root", str(ROOT), "--runs-root", str(root)).stdout)
    manifest = root / "demo-current" / "manifest.json"
    value = json.loads(manifest.read_text())
    value["data_lifecycle"]["retention"]["delete_after"] = "2000-01-01T00:00:00Z"
    value["data_lifecycle"]["retention"]["minimum_seconds"] = 0
    value["started_at"] = "1999-01-01T00:00:00Z"
    manifest.write_text(json.dumps(value))
    result = invoke(tmp_path, "cockpit", "action", "--policy-root", setup["policy_root"], "--runs-root", str(root), "--run-id", "demo-current", "--operation", "validate-run", "--expected-fingerprint", "0" * 64)
    assert result.returncode == 2 and not result.stdout
    assert not (root / "demo-current" / ".cockpit.lock").exists() and not (root / "demo-current" / "cockpit").exists()
