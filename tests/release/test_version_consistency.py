"""The product version is declared in several files and must never drift apart."""
import json
import re
import tomllib


def test_product_version_is_identical_across_every_declaration(repo_root):
    import claude_ads_core

    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    plugin = json.loads((repo_root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads((repo_root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    primary = next(item for item in marketplace["plugins"] if item["name"] == plugin["name"])
    citation = re.search(r'^version:\s*"?([0-9][^"\s]*)"?\s*$', (repo_root / "CITATION.cff").read_text(encoding="utf-8"), re.M).group(1)
    declared = {
        "pyproject.toml": pyproject,
        "claude_ads_core.__version__": claude_ads_core.__version__,
        ".claude-plugin/plugin.json": plugin["version"],
        ".claude-plugin/marketplace.json metadata": marketplace["metadata"]["version"],
        ".claude-plugin/marketplace.json primary plugin": primary["version"],
        "CITATION.cff": citation,
    }
    assert len(set(declared.values())) == 1, declared
