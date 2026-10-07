from __future__ import annotations

from pathlib import Path

import pytest

from claude_ads_core.policy_root import PolicyRootError, resolve_policy_root


def _policy_root(tmp_path: Path) -> Path:
    root = tmp_path / "runtime"
    (root / "control-plane" / "manifests").mkdir(parents=True)
    return root


def test_explicit_policy_root_is_resolved(tmp_path: Path):
    root = _policy_root(tmp_path)
    assert resolve_policy_root(root) == root.resolve()


def test_empty_explicit_policy_root_is_rejected():
    with pytest.raises(PolicyRootError, match="non-empty"):
        resolve_policy_root("")


def test_source_layout_resolves_without_current_working_directory(tmp_path: Path, monkeypatch):
    root = _policy_root(tmp_path)
    module = root / "claude_ads_core" / "policy_root.py"
    module.parent.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert resolve_policy_root(module_path=module) == root.resolve()


def test_standalone_layout_resolves_without_current_working_directory(
    tmp_path: Path, monkeypatch
):
    root = _policy_root(tmp_path)
    module = root / "scripts" / "claude_ads_core" / "policy_root.py"
    module.parent.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert resolve_policy_root(module_path=module) == root.resolve()


def test_resolver_does_not_fall_back_to_ambient_working_directory(
    tmp_path: Path, monkeypatch
):
    ambient = _policy_root(tmp_path)
    monkeypatch.chdir(ambient)
    unrelated_module = tmp_path / "isolated" / "claude_ads_core" / "policy_root.py"
    unrelated_module.parent.mkdir(parents=True)
    with pytest.raises(PolicyRootError, match="supply --policy-root"):
        resolve_policy_root(module_path=unrelated_module)
