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
#
# A leading `~` or `~/` in --skill-dir or --agent-dir is expanded to $HOME,
# because bash does not expand a tilde after `=`. Paths may contain spaces; the
# `..` check rejects parent-traversal components only.

# Global so the EXIT trap can see it on every exit path; a local declared in
# main() is out of scope once main returns.
VALIDATION_DIR=""

cleanup() {
    [ -n "$VALIDATION_DIR" ] || return 0
    rm -rf -- "$VALIDATION_DIR"
}
trap cleanup EXIT

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
    case "$path" in ..|../*|*/..|*/../*) return 1 ;; esac
    case "$path" in //*|\\\\*) return 1 ;; esac
    case "$path" in *$'\n'*|*$'\r'*|*$'\t'*) return 1 ;; esac
    return 0
}

expand_home_path() {
    local value="$1"
    case "$value" in
        \~) printf '%s' "$HOME" ;;
        \~/*) printf '%s' "${HOME}/${value#\~/}" ;;
        *) printf '%s' "$value" ;;
    esac
}

path_uses_unsupported_tilde() {
    case "$1" in
        \~|\~/*) return 1 ;;
        \~*) return 0 ;;
        *) return 1 ;;
    esac
}

is_owned_path() {
    local path="$1" parent base canonical_parent canonical
    case "$path" in *$'\n'*|*$'\r'*|*$'\t'*|*/|*//*|*/../*|*/..|../*|..|*/./*|*/.) return 1 ;; esac
    parent=$(dirname -- "$path")
    base=$(basename -- "$path")
    if [ -d "$parent" ]; then
        canonical_parent=$(CDPATH='' cd -- "$parent" 2>/dev/null && pwd -P) || return 1
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

    if path_uses_unsupported_tilde "$SKILL_DIR_OVERRIDE" || path_uses_unsupported_tilde "$AGENT_DIR_OVERRIDE"; then
        echo "✗ Unsupported ~user path. Use an absolute path or a path starting with ~/" >&2
        exit 1
    fi
    SKILL_DIR_OVERRIDE=$(expand_home_path "$SKILL_DIR_OVERRIDE")
    AGENT_DIR_OVERRIDE=$(expand_home_path "$AGENT_DIR_OVERRIDE")
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
    SKILL_BASE_CANON=$(CDPATH='' cd -- "$SKILL_BASE" && pwd -P)
    AGENT_DIR_CANON=$(CDPATH='' cd -- "$AGENT_DIR" && pwd -P)

    local MANIFEST_PATH="${SKILL_BASE}/.claude-ads-${TARGET}.manifest"
    if [ ! -f "$MANIFEST_PATH" ] || [ -L "$MANIFEST_PATH" ]; then
        echo "✗ Ownership manifest not found or unsafe: ${MANIFEST_PATH}" >&2
        echo "  Installs older than v2.0.0 wrote no ownership manifest." >&2
        echo "  Refusing namespace-based deletion. Remove a legacy install manually after reviewing its files." >&2
        exit 1
    fi

    local VALID_FILES VALID_DIRS VALID_RECURSIVE VALID_BYTECODE VALID_ALL
    VALIDATION_DIR=$(mktemp -d)
    VALID_FILES="${VALIDATION_DIR}/files"
    VALID_DIRS="${VALIDATION_DIR}/directories"
    VALID_RECURSIVE="${VALIDATION_DIR}/recursive"
    VALID_BYTECODE="${VALIDATION_DIR}/bytecode"
    VALID_ALL="${VALIDATION_DIR}/all"
    : > "$VALID_FILES"; : > "$VALID_DIRS"; : > "$VALID_RECURSIVE"; : > "$VALID_BYTECODE"; : > "$VALID_ALL"

    assert_safe_recursive_links() {
        local tree="$1" links link target
        links=$(find "$tree" -type l -print) || return 1
        [ -n "$links" ] || return 0
        # Unlink only standard venv children. Recursive removal of the owned
        # root does not follow these links to the host interpreter or lib tree.
        [ "$tree" = "${SKILL_BASE}/ads/.venv" ] || return 1
        while IFS= read -r link; do
            case "$link" in
                "$tree/lib64")
                    [ "$(readlink "$link")" = "lib" ] && [ -d "$tree/lib" ] && [ ! -L "$tree/lib" ] || return 1
                    ;;
                "$tree/bin/python"|"$tree/bin/python3"|"$tree/bin/python3.11"|"$tree/bin/python3.12")
                    [ -f "$link" ] && [ -x "$link" ] || return 1
                    target=$(readlink "$link") || return 1
                    case "$target" in
                        python|python3|python3.11|python3.12|/*) ;;
                        *) return 1 ;;
                    esac
                    ;;
                *) return 1 ;;
            esac
        done <<< "$links"
    }
    assert_safe_recursive_tree() {
        local path="$1"
        is_owned_path "$path" || return 1
        [ ! -e "$path" ] && return 0
        [ -d "$path" ] && [ ! -L "$path" ] || return 1
        assert_safe_recursive_links "$path" || return 1
    }

    # Parse once and require the exact current, target-bound schema before
    # granting any delete authority.
    awk -F '\t' 'NF != 2 { exit 1 }' "$MANIFEST_PATH" || {
        echo "✗ Invalid ownership-manifest record shape" >&2
        exit 1
    }
    local VERSION_COUNT=0 TARGET_COUNT=0 LINE_NUMBER=0 PATH_KEY
    while IFS=$'\t' read -r kind path; do
        LINE_NUMBER=$((LINE_NUMBER + 1))
        case "$kind" in
            V)
                [ "$LINE_NUMBER" -eq 1 ] && [ "$path" = "1" ] || { echo "✗ Invalid ownership-manifest version/header" >&2; exit 1; }
                VERSION_COUNT=$((VERSION_COUNT + 1))
                ;;
            T)
                [ "$LINE_NUMBER" -eq 2 ] && [ "$path" = "$TARGET" ] || { echo "✗ Ownership-manifest target/header mismatch" >&2; exit 1; }
                TARGET_COUNT=$((TARGET_COUNT + 1))
                ;;
            F|D|R|B)
                case "$path" in /*) ;; *) echo "✗ Non-canonical ownership-manifest path: ${path}" >&2; exit 1 ;; esac
                is_owned_path "$path" || { echo "✗ Unsafe ownership-manifest path: ${path}" >&2; exit 1; }
                [ "$LINE_NUMBER" -gt 2 ] || { echo "✗ Ownership records must follow manifest headers" >&2; exit 1; }
                PATH_KEY=$(printf '%s' "$path" | tr '[:upper:]' '[:lower:]')
                if grep -Fqx -- "$PATH_KEY" "$VALID_ALL"; then
                    echo "✗ Duplicate ownership-manifest path: ${path}" >&2
                    exit 1
                fi
                printf '%s\n' "$PATH_KEY" >> "$VALID_ALL"
                if [ -e "$path" ] || [ -L "$path" ]; then
                    case "$kind" in
                        F) [ ! -d "$path" ] && [ ! -L "$path" ] || { echo "✗ Owned file changed type: ${path}" >&2; exit 1; } ;;
                        D|B) [ -d "$path" ] && [ ! -L "$path" ] || { echo "✗ Owned directory changed type: ${path}" >&2; exit 1; } ;;
                        R) assert_safe_recursive_tree "$path" || { echo "✗ Unsafe recursive ownership tree: ${path}" >&2; exit 1; } ;;
                    esac
                fi
                case "$kind" in
                    F) printf '%s\n' "$path" >> "$VALID_FILES" ;;
                    D) printf '%s\n' "$path" >> "$VALID_DIRS" ;;
                    R) printf '%s\n' "$path" >> "$VALID_RECURSIVE" ;;
                    B) printf '%s\n' "$path" >> "$VALID_BYTECODE" ;;
                esac
                ;;
            *) echo "✗ Unknown ownership-manifest record: ${kind}" >&2; exit 1 ;;
        esac
    done < "$MANIFEST_PATH"
    [ "$VERSION_COUNT" -eq 1 ] && [ "$TARGET_COUNT" -eq 1 ] || {
        echo "✗ Ownership manifest must contain exactly one V and one T record" >&2
        exit 1
    }

    # A B record grants authority only over normal CPython cache files for
    # manifest-owned modules in these two package-local cache roots. Unknown
    # files, links, subdirectories, and sibling cache roots remain untouched.
    while IFS= read -r path; do
        case "$path" in
            "${SKILL_BASE_CANON}/ads/scripts/claude_ads_core/__pycache__"|"${SKILL_BASE_CANON}/ads/scripts/claude_ads_core/adapters/__pycache__") ;;
            *) echo "✗ Unsafe bytecode ownership root: ${path}" >&2; exit 1 ;;
        esac
        parent=$(dirname -- "$path")
        HAS_OWNED_MODULE=0
        while IFS= read -r source; do
            if [ "$(dirname -- "$source")" = "$parent" ]; then
                case "$source" in *.py) HAS_OWNED_MODULE=1; break ;; esac
            fi
        done < "$VALID_FILES"
        [ "$HAS_OWNED_MODULE" -eq 1 ] || {
            echo "✗ Bytecode ownership root has no owned Python modules: ${path}" >&2
            exit 1
        }
    done < "$VALID_BYTECODE"

    echo "→ Uninstalling Claude Ads from ${SKILL_BASE} and ${AGENT_DIR}..."

    while IFS= read -r path; do
        [ -e "$path" ] || continue
        is_owned_path "$path" && [ ! -d "$path" ] && [ ! -L "$path" ] || {
            echo "✗ Owned file changed before deletion: ${path}" >&2; exit 1;
        }
        rm -f "$path"
    done < "$VALID_FILES"

    while IFS= read -r path; do
        [ -e "$path" ] || continue
        parent=$(dirname -- "$path")
        while IFS= read -r source; do
            if [ "$(dirname -- "$source")" = "$parent" ]; then
                case "$source" in *.py)
                    module=$(basename -- "${source%.py}")
                    for cached in \
                        "$path/${module}".cpython-31[12].pyc \
                        "$path/${module}".cpython-31[12].opt-[0-9].pyc; do
                        [ -f "$cached" ] && [ ! -L "$cached" ] || continue
                        rm -f -- "$cached"
                    done
                ;; esac
            fi
        done < "$VALID_FILES"
        rmdir "$path" 2>/dev/null || true
    done < "$VALID_BYTECODE"

    while IFS= read -r path; do
        [ -e "$path" ] || continue
        assert_safe_recursive_tree "$path" || {
            echo "✗ Recursive ownership tree changed before deletion: ${path}" >&2; exit 1;
        }
        rm -rf "$path"
    done < "$VALID_RECURSIVE"

    awk '{ print length($0) "\t" $0 }' "$VALID_DIRS" | sort -nr | cut -f2- | while IFS= read -r path; do
        [ -e "$path" ] || continue
        is_owned_path "$path" && [ -d "$path" ] && [ ! -L "$path" ] || {
            echo "✗ Owned directory changed before deletion: ${path}" >&2; exit 1;
        }
        rmdir "$path" 2>/dev/null || true
    done

    [ -f "$MANIFEST_PATH" ] && [ ! -L "$MANIFEST_PATH" ] || {
        echo "✗ Ownership manifest changed before deletion" >&2; exit 1;
    }
    rm -f "$MANIFEST_PATH"

    echo "✓ Claude Ads uninstalled."
}

main "$@"
