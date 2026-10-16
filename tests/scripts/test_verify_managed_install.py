from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "verify_managed_install", ROOT / "scripts/verify_managed_install.py"
)
assert SPEC is not None and SPEC.loader is not None
verify_managed_install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_managed_install)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _component() -> dict[str, object]:
    return {
        "name": "alpha",
        "version": "1.0",
        "direct": True,
        "purl": "pkg:pypi/alpha@1.0",
        "artifact": {
            "filename": "alpha-1.0-py3-none-any.whl",
            "url": "https://files.pythonhosted.org/packages/alpha-1.0.whl",
            "sha256": "a" * 64,
        },
    }


def _receipt_component(component: dict[str, object]) -> dict[str, object]:
    return {
        "name": component["name"],
        "version": component["version"],
        "artifact": component["artifact"],
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    skill_dir = tmp_path / "skill"
    evidence = repository / "control-plane/dependency-evidence/runtime-linux-cp312.json"
    inventory = repository / "control-plane/manifests/dependency-inventory.json"
    lock = repository / "requirements.lock"
    python = skill_dir / ".venv/bin/python"
    report_path = skill_dir / ".venv/install-report.json"
    probe_path = skill_dir / ".venv/probe.json"
    installed_core = skill_dir / "scripts/claude_ads_core/__init__.py"
    evidence.parent.mkdir(parents=True)
    inventory.parent.mkdir(parents=True)
    python.parent.mkdir(parents=True)
    installed_core.parent.mkdir(parents=True)
    evidence.write_text("{}\n", encoding="utf-8")
    lock.write_text("alpha==1.0 --hash=sha256:" + "a" * 64 + "\n", encoding="utf-8")
    installed_core.write_text('__version__ = "2.0.1"\n', encoding="utf-8")
    component = _component()
    target = {
        "id": "runtime-linux-cp312",
        "profile": "runtime",
        "python_version": "3.12",
        "implementation": "CPython",
        "os": "linux",
        "arch": "x86_64",
        "abi": "cp312",
        "resolver": "pip / PyPI",
        "platform_policy": "test target",
        "resolution_evidence_sha256": _sha256(evidence),
        "components": [component],
    }
    _write_json(inventory, {"targets": [target]})
    report = {
        "version": "1",
        "pip_version": "26.0",
        "install": [
            {
                "download_info": {
                    "url": component["artifact"]["url"],
                    "archive_info": {"hashes": {"sha256": component["artifact"]["sha256"]}},
                },
                "metadata": {"name": "alpha", "version": "1.0"},
            }
        ],
    }
    _write_json(report_path, report)
    probe = {
        "python_full_version": "3.12.9",
        "python_version": "3.12",
        "implementation": "CPython",
        "system": "Linux",
        "machine": "x86_64",
        "abi": "cp312",
        "pip_version": "26.0",
        "claude_ads_core_version": "2.0.1",
        "claude_ads_core_file": str(installed_core.resolve()),
        "installed": [
            {"name": "alpha", "version": "1.0"},
            {"name": "pip", "version": "26.0"},
        ],
    }
    _write_json(probe_path, probe)
    python.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-I\" ] && [ \"$2\" = \"-c\" ]; then cat \"$(dirname \"$0\")/../probe.json\"; exit 0; fi\n"
        "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"pip\" ] && [ \"$3\" = \"check\" ]; then exit 0; fi\n"
        "exit 9\n",
        encoding="utf-8",
    )
    python.chmod(0o755)
    receipt = {
        "schema_version": "1.0.0",
        "receipt_class": "managed-python-runtime-install",
        "target_id": "runtime-linux-cp312",
        "target": {
            field: target[field] for field in verify_managed_install.TARGET_FIELDS
        },
        "resolver": "pip / PyPI",
        "python_full_version": "3.12.9",
        "pip_version": "26.0",
        "requirements_lock_sha256": _sha256(lock),
        "dependency_inventory_sha256": _sha256(inventory),
        "target_evidence_sha256": _sha256(evidence),
        "pip_install_report_sha256": _sha256(report_path),
        "components": [_receipt_component(component)],
    }
    _write_json(skill_dir / "managed-runtime-receipt.json", receipt)
    return repository, skill_dir


def _mutate_json(path: Path, mutate) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    _write_json(path, value)


@pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX executable shim")
def test_verifier_binds_complete_receipt_to_inventory_report_and_interpreter(tmp_path: Path) -> None:
    repository, skill_dir = _fixture(tmp_path)

    receipt = verify_managed_install.verify(repository, skill_dir)

    assert receipt["target_id"] == "runtime-linux-cp312"
    assert receipt["components"] == [_receipt_component(_component())]


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Linux", "x86_64", ("linux", "linux", "x86_64")),
        ("Darwin", "x86_64", ("macos-x86", "macos", "x86_64")),
        ("Darwin", "arm64", ("macos-arm", "macos", "arm64")),
        ("Windows", "AMD64", ("windows", "windows", "amd64")),
    ],
)
def test_native_platform_identity_matches_inventory_vocabulary(
    monkeypatch, system: str, machine: str, expected: tuple[str, str, str]
) -> None:
    monkeypatch.setattr(verify_managed_install.platform, "system", lambda: system)
    monkeypatch.setattr(verify_managed_install.platform, "machine", lambda: machine)

    assert verify_managed_install._native_platform() == expected
    assert verify_managed_install._target_id("3.12") == f"runtime-{expected[0]}-cp312"


@pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX executable shim")
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "target",
            {
                "python_version": "3.12",
                "implementation": "CPython",
                "os": "windows",
                "arch": "arm64",
                "abi": "cp312",
            },
            "target metadata mismatch",
        ),
        ("python_full_version", "0.0.0", "Python version mismatch"),
        ("pip_version", "0.0.0", "pip version mismatch"),
        ("pip_install_report_sha256", "f" * 64, "pip report binding mismatch"),
    ],
)
def test_verifier_rejects_forged_receipt_attestations(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    repository, skill_dir = _fixture(tmp_path)
    receipt_path = skill_dir / "managed-runtime-receipt.json"
    _mutate_json(receipt_path, lambda receipt: receipt.__setitem__(field, value))

    with pytest.raises(ValueError, match=message):
        verify_managed_install.verify(repository, skill_dir)


@pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX executable shim")
@pytest.mark.parametrize(
    "mutation",
    ["name", "version", "filename", "url", "sha256", "extra-field"],
)
def test_verifier_rejects_every_forged_component_attestation(
    tmp_path: Path, mutation: str
) -> None:
    repository, skill_dir = _fixture(tmp_path)
    receipt_path = skill_dir / "managed-runtime-receipt.json"

    def forge(receipt: dict[str, object]) -> None:
        component = receipt["components"][0]
        if mutation in {"name", "version"}:
            component[mutation] = "forged"
        elif mutation == "extra-field":
            component["evidence"] = "forged"
        else:
            component["artifact"][mutation] = "forged"

    _mutate_json(receipt_path, forge)
    with pytest.raises(ValueError, match="closure mismatch"):
        verify_managed_install.verify(repository, skill_dir)


@pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX executable shim")
def test_verifier_validates_retained_report_contents_after_hash_binding(tmp_path: Path) -> None:
    repository, skill_dir = _fixture(tmp_path)
    report_path = skill_dir / ".venv/install-report.json"
    receipt_path = skill_dir / "managed-runtime-receipt.json"
    _mutate_json(
        report_path,
        lambda report: report["install"][0]["download_info"].__setitem__(
            "url", "https://files.pythonhosted.org/packages/forged.whl"
        ),
    )
    _mutate_json(
        receipt_path,
        lambda receipt: receipt.__setitem__("pip_install_report_sha256", _sha256(report_path)),
    )

    with pytest.raises(ValueError, match="pip report artifact mismatch"):
        verify_managed_install.verify(repository, skill_dir)


@pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX executable shim")
def test_verifier_binds_target_evidence_to_inventory_and_receipt(tmp_path: Path) -> None:
    repository, skill_dir = _fixture(tmp_path)
    inventory_path = repository / "control-plane/manifests/dependency-inventory.json"
    receipt_path = skill_dir / "managed-runtime-receipt.json"
    _mutate_json(
        inventory_path,
        lambda inventory: inventory["targets"][0].__setitem__(
            "resolution_evidence_sha256", "f" * 64
        ),
    )
    _mutate_json(
        receipt_path,
        lambda receipt: receipt.__setitem__(
            "dependency_inventory_sha256", _sha256(inventory_path)
        ),
    )

    with pytest.raises(ValueError, match="inventory target evidence binding mismatch"):
        verify_managed_install.verify(repository, skill_dir)


@pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX executable shim")
def test_verifier_fails_clearly_when_retained_report_is_missing(tmp_path: Path) -> None:
    repository, skill_dir = _fixture(tmp_path)
    (skill_dir / ".venv/install-report.json").unlink()

    with pytest.raises(ValueError, match="pip install report is missing"):
        verify_managed_install.verify(repository, skill_dir)


@pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX executable shim")
def test_verifier_rejects_managed_interpreter_closure_drift(tmp_path: Path) -> None:
    repository, skill_dir = _fixture(tmp_path)
    probe_path = skill_dir / ".venv/probe.json"
    _mutate_json(
        probe_path,
        lambda probe: probe["installed"][0].__setitem__("version", "9.9"),
    )

    with pytest.raises(ValueError, match="interpreter closure mismatch"):
        verify_managed_install.verify(repository, skill_dir)


@pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX executable shim")
def test_verifier_rejects_core_imported_outside_installed_skill(tmp_path: Path) -> None:
    repository, skill_dir = _fixture(tmp_path)
    probe_path = skill_dir / ".venv/probe.json"
    _mutate_json(
        probe_path,
        lambda probe: probe.__setitem__(
            "claude_ads_core_file", str(repository / "claude_ads_core/__init__.py")
        ),
    )

    with pytest.raises(ValueError, match="imported core outside the installed skill"):
        verify_managed_install.verify(repository, skill_dir)


@pytest.mark.skipif(os.name == "nt", reason="fixture uses a POSIX executable shim")
def test_zero_exit_interpreter_shim_without_structured_probe_is_rejected(tmp_path: Path) -> None:
    repository, skill_dir = _fixture(tmp_path)
    python = skill_dir / ".venv/bin/python"
    python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python.chmod(0o755)

    with pytest.raises(ValueError, match="did not return JSON"):
        verify_managed_install.verify(repository, skill_dir)


def test_cli_requires_explicit_source_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/verify_managed_install.py"),
            "--skill-dir",
            str(tmp_path / "skill"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--repository" in result.stderr


def test_native_ci_verifier_calls_supply_the_required_source_repository() -> None:
    import yaml

    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    calls = [
        shlex.split(line.strip())
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        for line in step.get("run", "").splitlines()
        if "scripts/verify_managed_install.py" in line
    ]
    assert calls, "native CI must verify the installed managed runtime"
    for arguments in calls:
        assert "--repository" in arguments, "CI verifier invocation lacks its required checkout root"
        assert arguments[arguments.index("--repository") + 1] == "."
