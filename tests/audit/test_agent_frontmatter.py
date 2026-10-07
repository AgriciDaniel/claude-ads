"""Agent definitions inherit the host-selected model."""

from __future__ import annotations


def test_no_agent_frontmatter_pins_a_model(repo_root):
    agents = sorted((repo_root / "agents").glob("*.md"))
    assert len(agents) == 25
    for path in agents:
        frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
        assert "\nmodel:" not in frontmatter, path.name


def test_root_documents_host_model_inheritance(repo_root):
    root = " ".join(
        (repo_root / "ads/SKILL.md").read_text(encoding="utf-8").split()
    )
    assert "Agents inherit the model selected by the host runtime" in root
    assert "Do not pin a model in agent frontmatter" in root
