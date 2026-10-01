"""Public issue 78: agents must not override the operator's subagent model choice."""

from __future__ import annotations


def test_agents_leave_model_selection_to_the_host(repo_root):
    agents = sorted((repo_root / "agents").glob("*.md"))
    assert agents
    for path in agents:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{path.name} has no frontmatter"
        frontmatter = text.split("---", 2)[1]
        keys = {
            line.split(":", 1)[0].strip()
            for line in frontmatter.splitlines()
            if ":" in line and not line.startswith((" ", "\t"))
        }
        assert "name" in keys, f"{path.name} frontmatter was not parsed"
        assert "model" not in keys, f"{path.name} pins a model over the host's subagent setting"
