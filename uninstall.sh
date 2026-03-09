#!/usr/bin/env bash
set -euo pipefail

main() {
    echo "→ Uninstalling Claude AI Ads..."

    # Remove main skill (orchestrator + references)
    rm -rf "${HOME}/.claude/skills/ads"

    # Remove sub-skills
    for skill in ads-audit ads-google ads-meta ads-youtube ads-linkedin ads-tiktok ads-microsoft ads-creative ads-landing ads-budget ads-plan ads-competitor; do
        rm -rf "${HOME}/.claude/skills/${skill}"
    done

    # Remove agents
    for agent in audit-google audit-meta audit-creative audit-tracking audit-budget audit-compliance; do
        rm -f "${HOME}/.claude/agents/${agent}.md"
    done

    echo "✓ Claude AI Ads uninstalled."
}

main "$@"
