"""Prompt-level contracts for host model inheritance and audit worker results."""

from __future__ import annotations

CANONICAL_PLATFORMS = {
    "google",
    "meta",
    "youtube",
    "linkedin",
    "tiktok",
    "microsoft",
    "apple",
    "amazon",
    "reddit",
    "pinterest",
    "snapchat",
    "x",
}


def test_all_audit_agents_require_strict_v1_worker_results(repo_root):
    agents = sorted((repo_root / "agents").glob("audit-*.md"))
    assert len(agents) == 17
    for path in agents:
        text = path.read_text(encoding="utf-8")
        for field in (
            "`schema_version`",
            "`status`",
            "`platform`",
            "`scope`",
            "`findings`",
            "`contradictions`",
            "`missing_inputs`",
            "`stale_sources`",
            "`recovery_hints`",
            "`diagnosis`",
        ):
            assert field in text, f"{path.name} lacks {field}"
        for legacy in (
            "Every finding includes `control_id`,",
            "Each finding includes a stable control",
            "decision-complete `recommendation` or",
        ):
            assert legacy not in text, f"{path.name} retains a legacy contract"
        assert "Do not emit alternate finding keys" in text


def test_platform_audit_agents_pin_only_their_result_platform(repo_root):
    for platform in CANONICAL_PLATFORMS:
        text = (repo_root / f"agents/audit-{platform}.md").read_text(encoding="utf-8")
        assert f"`platform` to `{platform}`" in text


def test_audit_skill_example_uses_canonical_finding_fields(repo_root):
    text = (repo_root / "skills/ads-audit/SKILL.md").read_text(encoding="utf-8")
    for fragment in (
        '"schema_version": "1.0.0"',
        '"status": "unknown"',
        '"evidence": [',
        '"diagnosis":',
        '"stale_sources": []',
    ):
        assert fragment in text
    for legacy in ('"result":', '"severity":', '"evidence_refs":'):
        assert legacy not in text
