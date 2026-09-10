#!/usr/bin/env bash
set -euo pipefail

# Claude Ads Uninstaller (multi-host)
#
# Usage:
#   bash uninstall.sh                  # default: --target=claude
#   bash uninstall.sh --target=codex
#
# Removes only files and directories recorded by install.sh's ownership
# manifest. Unrelated ads-* skills and agents are never discovered by glob.

resolve_target_paths() {
    local target="$1"
    case "$target" in
        claude)   SKILL_BASE="${HOME}/.claude/skills";                                   AGENT_DIR="${HOME}/.claude/agents" ;;
        codex)    SKILL_BASE="${HOME}/.codex/skills";                                    AGENT_DIR="${HOME}/.codex/agents" ;;
        cursor)   SKILL_BASE="${HOME}/.cursor/extensions/claude-ads/skills";             AGENT_DIR="${HOME}/.cursor/extensions/claude-ads/agents" ;;
        windsurf) SKILL_BASE="${HOME}/.windsurf/skills";                                 AGENT_DIR="${HOME}/.windsurf/agents" ;;
        gemini)   SKILL_BASE="${HOME}/.gemini/extensions/claude-ads/skills";             AGENT_DIR="${HOME}/.gemini/extensions/claude-ads/agents" ;;
        goose)    SKILL_BASE="${HOME}/.config/goose/skills";                             AGENT_DIR="${HOME}/.config/goose/agents" ;;
        *)        return 1 ;;
    esac
    return 0
}

validate_install_path() {
    local path="$1"
    [ -z "$path" ] && return 1
    case "$path" in -*) return 1 ;; esac
    case "$path" in *[\;\&\|\$\(\)\<\>\`\\]*) return 1 ;; esac
    case "$path" in *..*) return 1 ;; esac
    case "$path" in //*|\\\\*) return 1 ;; esac
    case "$path" in *$'\n'*|*$'\r'*|*$'\t'*) return 1 ;; esac
    return 0
}

is_owned_path() {
    local path="$1" parent base canonical_parent canonical
    case "$path" in *$'\n'*|*$'\r'*|*$'\t'*|*/../*|*/..|../*|..|*/./*|*/.) return 1 ;; esac
    parent=$(dirname -- "$path")
    base=$(basename -- "$path")
    if [ -d "$parent" ]; then
        canonical_parent=$(CDPATH= cd -- "$parent" 2>/dev/null && pwd -P) || return 1
        canonical="${canonical_parent}/${base}"
    else
        # A missing parent cannot be deleted by any manifest record. Keep the
        # lexical check so stale, safe entries do not block uninstall.
        canonical="$path"
    fi
    case "$canonical" in
        "${SKILL_BASE_CANON}"/*|"${AGENT_DIR_CANON}"/*) return 0 ;;
        *) return 1 ;;
    esac
}

main() {
    local TARGET="claude"
    local SKILL_DIR_OVERRIDE=""
    local AGENT_DIR_OVERRIDE=""

    while [ $# -gt 0 ]; do
        case "$1" in
            --target=*) TARGET="${1#*=}" ;;
            --target)   shift; [ $# -eq 0 ] && { echo "✗ --target requires a value" >&2; exit 1; }; TARGET="$1" ;;
            --skill-dir=*) SKILL_DIR_OVERRIDE="${1#*=}" ;;
            --skill-dir) shift; [ $# -eq 0 ] && { echo "✗ --skill-dir requires a value" >&2; exit 1; }; SKILL_DIR_OVERRIDE="$1" ;;
            --agent-dir=*) AGENT_DIR_OVERRIDE="${1#*=}" ;;
            --agent-dir) shift; [ $# -eq 0 ] && { echo "✗ --agent-dir requires a value" >&2; exit 1; }; AGENT_DIR_OVERRIDE="$1" ;;
            --help|-h)
                echo "Usage: bash uninstall.sh [--target=<host>] [--skill-dir=<path>] [--agent-dir=<path>]"
                exit 0
                ;;
            *) echo "✗ Unknown argument: $1" >&2; exit 1 ;;
        esac
        shift
    done

    if ! resolve_target_paths "$TARGET"; then
        echo "✗ Unknown target: $TARGET" >&2
        echo "  Valid targets: claude, codex, cursor, windsurf, gemini, goose" >&2
        exit 1
    fi

    if [ -n "$SKILL_DIR_OVERRIDE" ]; then
        validate_install_path "$SKILL_DIR_OVERRIDE" || { echo "✗ Invalid --skill-dir" >&2; exit 1; }
        SKILL_BASE="$SKILL_DIR_OVERRIDE"
    fi
    if [ -n "$AGENT_DIR_OVERRIDE" ]; then
        validate_install_path "$AGENT_DIR_OVERRIDE" || { echo "✗ Invalid --agent-dir" >&2; exit 1; }
        AGENT_DIR="$AGENT_DIR_OVERRIDE"
    fi

    [ -d "$SKILL_BASE" ] || { echo "✗ Skill root not found: ${SKILL_BASE}" >&2; exit 1; }
    [ -d "$AGENT_DIR" ] || { echo "✗ Agent root not found: ${AGENT_DIR}" >&2; exit 1; }
    SKILL_BASE_CANON=$(CDPATH= cd -- "$SKILL_BASE" && pwd -P)
    AGENT_DIR_CANON=$(CDPATH= cd -- "$AGENT_DIR" && pwd -P)

    local MANIFEST_PATH="${SKILL_BASE}/.claude-ads-${TARGET}.manifest"
    if [ ! -f "$MANIFEST_PATH" ]; then
        echo "✗ Ownership manifest not found: ${MANIFEST_PATH}" >&2
        echo "  Installs older than v2.0.0 wrote no ownership manifest." >&2
        echo "  Refusing namespace-based deletion. Remove a legacy install manually after reviewing its files." >&2
        exit 1
    fi

    echo "→ Uninstalling Claude Ads from ${SKILL_BASE} and ${AGENT_DIR}..."

    # Validate the complete manifest before deleting anything. A tampered
    # manifest must fail atomically rather than turning into an arbitrary rm.
    while IFS=$'\t' read -r kind path; do
        case "$kind" in
            V|T) continue ;;
            F|D|R)
                is_owned_path "$path" || {
                    echo "✗ Unsafe ownership-manifest path: ${path}" >&2
                    exit 1
                }
                ;;
            *) echo "✗ Unknown ownership-manifest record: ${kind}" >&2; exit 1 ;;
        esac
    done < "$MANIFEST_PATH"

    while IFS=$'\t' read -r kind path; do
        [ "$kind" = "F" ] || continue
        [ -e "$path" ] || [ -L "$path" ] || continue
        rm -f -- "$path"
    done < "$MANIFEST_PATH"

    while IFS=$'\t' read -r kind path; do
        [ "$kind" = "R" ] || continue
        rm -rf -- "$path"
    done < "$MANIFEST_PATH"

    while IFS=$'\t' read -r kind path; do
        [ "$kind" = "D" ] || continue
        rmdir -- "$path" 2>/dev/null || true
    done < "$MANIFEST_PATH"

    rm -f -- "$MANIFEST_PATH"

    echo "✓ Claude Ads uninstalled."
}

main "$@"
