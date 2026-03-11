#!/usr/bin/env bash
set -euo pipefail

# Claude Ads Installer
# Wraps everything in main() to prevent partial execution on network failure

main() {
    SKILL_DIR="${HOME}/.claude/skills/ads"
    AGENT_DIR="${HOME}/.claude/agents"
    REPO_URL="https://github.com/AgriciDaniel/claude-ads"

    echo "════════════════════════════════════════"
    echo "║   Claude Ads - Installer             ║"
    echo "║   Claude Code Paid Ads Skill         ║"
    echo "════════════════════════════════════════"
    echo ""

    # Check prerequisites
    command -v git >/dev/null 2>&1 || { echo "✗ Git is required but not installed."; exit 1; }
    echo "✓ Git detected"

    # Create directories
    mkdir -p "${SKILL_DIR}/references"
    mkdir -p "${AGENT_DIR}"

    # Clone or update
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf ${TEMP_DIR}" EXIT

    echo "↓ Downloading Claude Ads..."
    git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/claude-ads" 2>/dev/null

    # Copy main skill + references
    echo "→ Installing skill files..."
    cp "${TEMP_DIR}/claude-ads/ads/SKILL.md" "${SKILL_DIR}/SKILL.md"
    cp "${TEMP_DIR}/claude-ads/ads/references/"*.md "${SKILL_DIR}/references/"

    # Copy sub-skills
    echo "→ Installing sub-skills..."
    for skill_dir in "${TEMP_DIR}/claude-ads/skills"/*/; do
        skill_name=$(basename "${skill_dir}")
        target="${HOME}/.claude/skills/${skill_name}"
        mkdir -p "${target}"
        cp "${skill_dir}SKILL.md" "${target}/SKILL.md"

        # Copy assets (industry templates) if they exist
        if [ -d "${skill_dir}assets" ]; then
            mkdir -p "${target}/assets"
            cp "${skill_dir}assets/"*.md "${target}/assets/"
        fi
    done

    # Copy agents
    echo "→ Installing subagents..."
    cp "${TEMP_DIR}/claude-ads/agents/"*.md "${AGENT_DIR}/" 2>/dev/null || true

    # Copy scripts (optional Python tools)
    SCRIPTS_DIR="${HOME}/.claude/skills/ads/scripts"
    if [ -d "${TEMP_DIR}/claude-ads/scripts" ]; then
        echo "→ Installing Python scripts..."
        mkdir -p "${SCRIPTS_DIR}"
        cp "${TEMP_DIR}/claude-ads/scripts/"*.py "${SCRIPTS_DIR}/"
        cp "${TEMP_DIR}/claude-ads/requirements.txt" "${SKILL_DIR}/requirements.txt"
    fi

    echo ""
    echo "✓ Claude Ads installed successfully!"
    echo ""
    echo "  Installed:"
    echo "    • 1 main skill (ads orchestrator)"
    echo "    • 22 sub-skills (platform + functional + campaign manager)"
    echo "    • 6 parallel audit agents"
    echo "    • 12 reference files"
    echo "    • 11 industry templates"
    echo ""
    echo "Usage:"
    echo "  1. Start Claude Code:  claude"
    echo "  2. Audit commands:     /ads audit"
    echo "                         /ads plan saas"
    echo "                         /ads google"
    echo "  3. Campaign manager:   /paid-ads"
    echo "                         /ad-creative"
    echo "                         /html-ad"
    echo ""
    echo "To uninstall: curl -fsSL ${REPO_URL}/raw/main/uninstall.sh | bash"
}

main "$@"
