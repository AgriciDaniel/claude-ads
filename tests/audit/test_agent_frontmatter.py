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


CREATIVE_TOOL_ALLOWLISTS = {
    "copy-writer": ["Read", "Glob", "Grep"],
    "creative-strategist": ["Read", "Glob", "Grep"],
    "format-adapter": ["Read", "Glob", "Grep"],
    "visual-designer": ["Read", "Glob", "Grep", "Write"],
}


def _frontmatter_tools(path):
    frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
    for line in frontmatter.splitlines():
        if line.startswith("tools:"):
            return [tool.strip() for tool in line.split(":", 1)[1].split(",")]
    return None


def test_every_agent_declares_a_least_privilege_tool_allowlist(repo_root):
    for path in sorted((repo_root / "agents").glob("*.md")):
        tools = _frontmatter_tools(path)
        assert tools, f"{path.name} omits a tools allowlist and would inherit every tool"
        assert not {"WebFetch", "WebSearch", "Bash", "Edit", "Agent"} & set(tools) or path.stem in {
            "release-verifier",
            "research-worker",
            "source-verifier",
        }, path.name


def test_creative_workers_hold_only_the_tools_their_contract_needs(repo_root):
    for name, expected in CREATIVE_TOOL_ALLOWLISTS.items():
        tools = _frontmatter_tools(repo_root / "agents" / f"{name}.md")
        assert tools == expected, name
