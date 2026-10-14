"""Main release integration for the independently selected companion."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.release.test_release import release, _repository, _write, _git

ROOT = Path(__file__).resolve().parents[2]


def companion_repo(tmp_path):
    root = _repository(tmp_path)
    marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text())
    manifest = json.loads((ROOT / "mods/claude-ads-cockpit/.claude-plugin/plugin.json").read_text())
    marketplace["plugins"].append({"name": "ads-cockpit", "source": "./mods/claude-ads-cockpit", "version": manifest["version"], "repository": manifest["repository"], "license": manifest["license"]})
    _write(root, ".claude-plugin/marketplace.json", json.dumps(marketplace))
    for relative in release._companion_package_files() | {"scripts/package_cockpit.py"}:
        _write(root, relative, (ROOT / relative).read_text())
    _git(root, "add", ".")
    return root


def test_dual_marketplace_and_curated_main_archive(tmp_path):
    root = companion_repo(tmp_path)
    assert release.audit_repository(root) == []
    members = release.package_files(release.tracked_files(root))
    assert set(release._companion_package_files()) <= set(members)
    assert not any("mods/claude-ads-cockpit/tests/" in p for p in members)
    assert not any(".claude-plugin/types/" in p for p in members)
    assert ".claude-plugin/marketplace.json" in members
    primary = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    assert primary["skills"] == ["./ads/", "./skills/"]
    assert "hooks" not in primary


@pytest.mark.parametrize("change", ["duplicate", "unreviewed", "unsafe-source", "malformed-name", "missing-manifest", "missing-runtime", "missing-allowlist"])
def test_optional_marketplace_rejects_incomplete_or_unreviewed_component(tmp_path, change):
    root = companion_repo(tmp_path)
    path = root / ".claude-plugin/marketplace.json"
    doc = json.loads(path.read_text())
    if change == "duplicate":
        doc["plugins"].append(dict(doc["plugins"][1]))
    elif change == "unreviewed":
        doc["plugins"].append({"name": "other-companion"})
    elif change == "unsafe-source":
        doc["plugins"][1]["source"] = "../other"
    elif change == "malformed-name":
        doc["plugins"][1]["name"] = ["ads-cockpit"]
    else:
        missing = {"missing-manifest": "mods/claude-ads-cockpit/.claude-plugin/plugin.json", "missing-runtime": "mods/claude-ads-cockpit/hooks/register.mjs", "missing-allowlist": "scripts/package_cockpit.py"}[change]
        _git(root, "rm", "--cached", missing)
    path.write_text(json.dumps(doc))
    assert release._audit_manifest_consistency(root, set(release.tracked_files(root)))


def test_task_created_javascript_gets_sensitive_content_audit(tmp_path):
    root = _repository(tmp_path)
    _write(root, "new-plugin/hooks/register.mjs", "const token = 'ghp_" + "x" * 36 + "';\n")
    assert release.audit_repository(root) == []
    errors = release.audit_repository(root, include_untracked=True)
    assert any("possible GitHub token" in error for error in errors)


def test_product_optional_entry_preserves_safety_boundaries():
    doc = json.loads((ROOT / "control-plane/manifests/product-manifest.json").read_text())
    assert doc["public_release_authorized"] is False
    assert doc["default_mutation_mode"] == "read-only"
    companion, = doc["optional_components"]
    assert companion["id"] == "ads-cockpit" and companion["default_enabled"] is False
    assert companion["native_acceptance"] == "pending"
