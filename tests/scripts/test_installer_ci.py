"""Regression tests for deterministic native installer CI sharding."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / ".github/scripts/run_installer_ci.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_installer_ci", RUNNER)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
runner = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = runner
RUNNER_SPEC.loader.exec_module(runner)


def test_round_robin_shards_are_sorted_disjoint_and_complete() -> None:
    nodeids = [
        "tests/scripts/test_privacy_outputs.py::test_z",
        "tests/scripts/test_installer_security.py::test_b",
        "tests/scripts/test_privacy_outputs.py::test_a",
        "tests/scripts/test_installer_security.py::test_a",
        "tests/scripts/test_installer_security.py::test_c",
    ]

    first = runner.build_shard_plan(nodeids, shard_index=0, shard_count=2)
    second = runner.build_shard_plan(nodeids, shard_index=1, shard_count=2)

    expected = tuple(sorted(nodeids))
    assert first.collected == expected
    assert second.collected == expected
    assert first.selected == expected[0::2]
    assert second.selected == expected[1::2]
    assert set(first.selected).isdisjoint(second.selected)
    assert set(first.selected).union(second.selected) == set(expected)
    assert set(first.selected).union(first.deselected) == set(expected)
    assert set(second.selected).union(second.deselected) == set(expected)


@pytest.mark.parametrize(
    ("shard_index", "shard_count", "message"),
    [
        (0, 0, "positive integer"),
        (-1, 2, "between 0 and 1"),
        (2, 2, "between 0 and 1"),
    ],
)
def test_invalid_shard_configuration_fails(
    shard_index: int, shard_count: int, message: str
) -> None:
    with pytest.raises(runner.ShardConfigurationError, match=message):
        runner.build_shard_plan(
            ["tests/scripts/test_installer_security.py::test_one"],
            shard_index=shard_index,
            shard_count=shard_count,
        )


def test_empty_collection_empty_selection_and_duplicates_fail() -> None:
    with pytest.raises(runner.ShardConfigurationError, match="collected no"):
        runner.build_shard_plan([], shard_index=0, shard_count=1)

    with pytest.raises(runner.ShardConfigurationError, match="selected no"):
        runner.build_shard_plan(
            ["tests/scripts/test_installer_security.py::test_one"],
            shard_index=1,
            shard_count=2,
        )

    duplicate = "tests/scripts/test_installer_security.py::test_one"
    with pytest.raises(runner.ShardConfigurationError, match="duplicate"):
        runner.build_shard_plan(
            [duplicate, duplicate], shard_index=0, shard_count=1
        )


def test_nodeids_must_remain_in_the_exact_native_test_inventory() -> None:
    assert runner.canonical_nodeid(
        r"tests\scripts\test_installer_security.py::test_one"
    ) == "tests/scripts/test_installer_security.py::test_one"

    with pytest.raises(runner.ShardConfigurationError, match="outside"):
        runner.canonical_nodeid("tests/scripts/test_installer_ci.py::test_one")
    with pytest.raises(runner.ShardConfigurationError, match="unsafe"):
        runner.canonical_nodeid("../test_installer_security.py::test_one")


def test_plugin_preserves_original_order_and_reports_deselection(tmp_path) -> None:
    class FakeItem:
        def __init__(self, nodeid: str) -> None:
            self.nodeid = nodeid

    class FakeHook:
        def __init__(self) -> None:
            self.deselected: list[FakeItem] = []

        def pytest_deselected(self, *, items: list[FakeItem]) -> None:
            self.deselected.extend(items)

    class FakeConfig:
        def __init__(self) -> None:
            self.hook = FakeHook()

    original = [
        FakeItem("tests/scripts/test_privacy_outputs.py::test_z"),
        FakeItem("tests/scripts/test_installer_security.py::test_b"),
        FakeItem("tests/scripts/test_privacy_outputs.py::test_a"),
        FakeItem("tests/scripts/test_installer_security.py::test_a"),
    ]
    items = list(original)
    config = FakeConfig()
    plugin = runner.InstallerShardPlugin(
        shard_index=0,
        shard_count=2,
        output=tmp_path / "manifest.json",
        collect_only=False,
        pytest_module=pytest,
    )

    plugin.pytest_collection_modifyitems(config, items)

    assert plugin.plan is not None
    selected = set(plugin.plan.selected)
    assert items == [
        item for item in original if runner.canonical_nodeid(item.nodeid) in selected
    ]
    assert config.hook.deselected == [
        item for item in original if runner.canonical_nodeid(item.nodeid) not in selected
    ]


def test_main_preserves_pytest_exit_code(monkeypatch, tmp_path) -> None:
    observed: dict[str, object] = {}

    def fake_pytest_main(arguments, *, plugins):
        observed["arguments"] = arguments
        observed["plugins"] = plugins
        return pytest.ExitCode.TESTS_FAILED

    monkeypatch.setattr(
        runner,
        "load_pytest",
        lambda: SimpleNamespace(main=fake_pytest_main),
    )

    result = runner.main(
        [
            "--shard-index",
            "0",
            "--shard-count",
            "2",
            "--output",
            str(tmp_path / "manifest.json"),
        ]
    )

    assert result == int(pytest.ExitCode.TESTS_FAILED)
    assert observed["arguments"][:2] == list(runner.NATIVE_TEST_PATHS)
    assert len(observed["plugins"]) == 1


def test_standalone_copy_requires_complete_source_checkout(tmp_path) -> None:
    standalone = tmp_path / "standalone" / "run_installer_ci.py"
    standalone.parent.mkdir()
    shutil.copy2(RUNNER, standalone)
    output = tmp_path / "manifest.json"

    result = subprocess.run(
        [
            sys.executable,
            str(standalone),
            "--shard-index",
            "0",
            "--shard-count",
            "2",
            "--output",
            str(output),
            "--collect-only",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "complete repository source checkout required" in result.stderr
    assert not output.exists()


def test_missing_pytest_reports_reviewed_ci_dependency(monkeypatch, tmp_path, capsys) -> None:
    def missing_pytest(name: str):
        raise ModuleNotFoundError("No module named 'pytest'", name="pytest")

    monkeypatch.setattr(runner.importlib, "import_module", missing_pytest)

    result = runner.main(
        [
            "--shard-index",
            "0",
            "--shard-count",
            "2",
            "--output",
            str(tmp_path / "manifest.json"),
            "--collect-only",
        ]
    )

    assert result == 2
    error = capsys.readouterr().err
    assert "pytest is required for native installer CI" in error
    assert "requirements-dev.lock" in error


def test_collect_only_shards_match_the_live_native_inventory(tmp_path) -> None:
    manifests = []
    for shard_index in range(2):
        output = tmp_path / f"shard-{shard_index}.json"
        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--shard-index",
                str(shard_index),
                "--shard-count",
                "2",
                "--output",
                output.name,
                "--collect-only",
            ],
            cwd=tmp_path,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        manifests.append(json.loads(output.read_text(encoding="utf-8")))

    first, second = manifests
    full = first["collected_nodeids"]
    assert full
    assert second["collected_nodeids"] == full
    assert first["selected_nodeids"] == full[0::2]
    assert second["selected_nodeids"] == full[1::2]
    assert set(first["selected_nodeids"]).isdisjoint(second["selected_nodeids"])
    assert set(first["selected_nodeids"]).union(second["selected_nodeids"]) == set(
        full
    )

    for manifest in manifests:
        assert manifest["schema_version"] == "1.0.0"
        assert manifest["runner"] == ".github/scripts/run_installer_ci.py"
        assert manifest["test_paths"] == list(runner.NATIVE_TEST_PATHS)
        assert manifest["mode"] == "collect-only"
        assert manifest["selection"]["algorithm"] == runner.SELECTION_ALGORITHM
        assert manifest["selection"]["shard_count"] == 2
        assert manifest["counts"]["collected"] == len(full)
        assert manifest["counts"]["selected"] > 0
        assert manifest["counts"]["deselected"] > 0
        assert (
            manifest["counts"]["selected"]
            + manifest["counts"]["deselected"]
            == manifest["counts"]["collected"]
        )
        assert set(manifest["selected_nodeids"]).isdisjoint(
            manifest["deselected_nodeids"]
        )
        assert set(manifest["selected_nodeids"]).union(
            manifest["deselected_nodeids"]
        ) == set(full)
        assert str(ROOT) not in json.dumps(manifest)
        assert all(
            nodeid.startswith(
                tuple(f"{path}::" for path in runner.NATIVE_TEST_PATHS)
            )
            for nodeid in manifest["collected_nodeids"]
        )
