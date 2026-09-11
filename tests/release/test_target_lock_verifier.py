from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("target_lock_verifier", ROOT / "scripts/verify_target_lock.py")
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


@pytest.fixture
def target_case(tmp_path, monkeypatch):
    inventory = verifier.release._load_dependency_inventory(ROOT)
    target = next(item for item in inventory["targets"] if item["id"] == "runtime-linux-cp311")
    monkeypatch.setattr(verifier.release, "_load_dependency_inventory", lambda root: inventory)
    monkeypatch.setattr(verifier, "native_target_id", lambda profile: "runtime-linux-cp311")
    real_run = verifier.subprocess.run

    def run_with_commit_fixture(*args, **kwargs):
        command = args[0] if args else kwargs.get("args")
        if command == ["git", "rev-parse", "HEAD"]:
            return SimpleNamespace(returncode=0, stdout="a" * 40 + "\n")
        return real_run(*args, **kwargs)

    monkeypatch.setattr(verifier.subprocess, "run", run_with_commit_fixture)
    report = {"pip_version": __import__("pip").__version__, "install": []}
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    expected_hashes = {}
    for component in target["components"]:
        artifact = component["artifact"]
        report["install"].append({"metadata": {"name": component["name"], "version": component["version"]}, "download_info": {"url": artifact["url"], "archive_info": {"hashes": {"sha256": artifact["sha256"]}}}})
        (wheels / artifact["filename"]).write_bytes(b"fixture")
        expected_hashes[artifact["filename"]] = artifact["sha256"]
    original_sha = verifier.sha256
    monkeypatch.setattr(verifier, "sha256", lambda path: expected_hashes[path.name] if path.suffix == ".whl" else original_sha(path))
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report, report_path, wheels, tmp_path / "attestation.json"


def test_valid_native_report_writes_commit_lock_inventory_resolver_and_runner_bindings(target_case, monkeypatch):
    report, report_path, wheels, output = target_case
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.setenv("RUNNER_ARCH", "X64")
    verifier.verify(ROOT, "runtime", report_path, wheels, output)
    result = json.loads(output.read_text())
    assert result["source_commit"] == "a" * 40
    assert result["pip_version"] == report["pip_version"]
    assert result["dependency_inventory_sha256"] and result["requirements_lock_sha256"]
    runner = result["environment"]["runner"]
    assert runner["RUNNER_ARCH"] == "X64"
    assert runner["RUNNER_OS"] == "Linux"
    assert set(runner).issubset({"ImageOS", "ImageVersion", "RUNNER_ARCH", "RUNNER_OS"})


@pytest.mark.parametrize("mutation", ["url", "hash", "missing", "extra"])
def test_native_report_rejects_wrong_or_incomplete_closure(target_case, mutation):
    report, report_path, wheels, output = target_case
    if mutation == "url":
        report["install"][0]["download_info"]["url"] = (
            "https://files.pythonhosted.org/wrong.whl"
        )
    elif mutation == "hash":
        report["install"][0]["download_info"]["archive_info"]["hashes"][
            "sha256"
        ] = "0" * 64
    elif mutation == "missing":
        report["install"].pop()
    else:
        report["install"].append(copy.deepcopy(report["install"][0]))
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(verifier.release.ReleaseError):
        verifier.verify(ROOT, "runtime", report_path, wheels, output)


def test_native_report_rejects_wrong_wheel_set(target_case):
    _report, report_path, wheels, output = target_case
    next(wheels.glob("*.whl")).unlink()
    with pytest.raises(verifier.release.ReleaseError, match="wheel"):
        verifier.verify(ROOT, "runtime", report_path, wheels, output)


def test_native_target_rejects_unsupported_interpreter(monkeypatch):
    monkeypatch.setattr(verifier.sys, "version_info", (3, 14, 0))
    with pytest.raises(verifier.release.ReleaseError, match="3.11 or 3.12"):
        verifier.native_target_id("runtime")
