#!/usr/bin/env bash
set -euo pipefail

# Claude Ads Installer
# Wraps everything in main() to prevent partial execution on network failure.
#
# Default target is Claude Code. Cross-host targets are EXPERIMENTAL — they
# install the same skill artifacts under each host's expected directory, but
# the host's own runtime conventions may differ. Pin path overrides via
# --skill-dir / --agent-dir if the auto-detected paths are wrong for your
# install.
#
# Usage:
#   bash install.sh                              # default: --target=claude
#   bash install.sh --target=codex
#   bash install.sh --target=cursor
#   bash install.sh --target=windsurf
#   bash install.sh --target=gemini
#   bash install.sh --target=goose
#   bash install.sh --skill-dir=/custom/path     # override the target's default path
#   bash install.sh --source=local --no-deps     # install this checkout, skip Python deps
#
# All target keys are validated against a strict whitelist (no shell injection
# possible via --target=...). Custom --skill-dir paths are validated against
# `;&|$()<>` ` `, leading dashes, `..` segments, and UNC-style paths.

REPO_URL="https://github.com/AgriciDaniel/claude-ads"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# ─────────────────────────────────────────────────────────────────────────────
# Target whitelist + path mapping
# ─────────────────────────────────────────────────────────────────────────────
#
# Keep this table the SINGLE source of truth. When a new host CLI is added,
# update only this case statement plus the help text.
#
# claude    — Claude Code (VERIFIED, GA)
# codex     — OpenAI Codex CLI (EXPERIMENTAL, verify before relying on)
# cursor    — Cursor IDE (EXPERIMENTAL, extension model differs)
# windsurf  — Windsurf IDE (EXPERIMENTAL)
# gemini    — Gemini CLI (EXPERIMENTAL)
# goose     — Goose CLI (EXPERIMENTAL)

resolve_target_paths() {
    local target="$1"
    case "$target" in
        claude)
            SKILL_BASE="${HOME}/.claude/skills"
            AGENT_DIR="${HOME}/.claude/agents"
            ALLOW_PIP=1
            HOST_LABEL="Claude Code"
            ;;
        codex)
            SKILL_BASE="${HOME}/.codex/skills"
            AGENT_DIR="${HOME}/.codex/agents"
            ALLOW_PIP=1
            HOST_LABEL="OpenAI Codex CLI"
            ;;
        cursor)
            SKILL_BASE="${HOME}/.cursor/extensions/claude-ads/skills"
            AGENT_DIR="${HOME}/.cursor/extensions/claude-ads/agents"
            ALLOW_PIP=0
            HOST_LABEL="Cursor IDE"
            ;;
        windsurf)
            SKILL_BASE="${HOME}/.windsurf/skills"
            AGENT_DIR="${HOME}/.windsurf/agents"
            ALLOW_PIP=0
            HOST_LABEL="Windsurf IDE"
            ;;
        gemini)
            SKILL_BASE="${HOME}/.gemini/extensions/claude-ads/skills"
            AGENT_DIR="${HOME}/.gemini/extensions/claude-ads/agents"
            ALLOW_PIP=0
            HOST_LABEL="Gemini CLI"
            ;;
        goose)
            SKILL_BASE="${HOME}/.config/goose/skills"
            AGENT_DIR="${HOME}/.config/goose/agents"
            ALLOW_PIP=0
            HOST_LABEL="Goose CLI"
            ;;
        *)
            return 1
            ;;
    esac
    return 0
}

# Reject anything that could be path-injection, flag-confusion, or
# directory-traversal. Called before --skill-dir / --agent-dir values are
# used in `mkdir`, `cp`, or `rm`.
validate_install_path() {
    local path="$1"
    # Reject empty
    [ -z "$path" ] && return 1
    # Reject leading dash (flag confusion: `--skill-dir=-rf`)
    case "$path" in -*) return 1 ;; esac
    # Reject shell metacharacters
    case "$path" in *[\;\&\|\$\(\)\<\>\`\\]*) return 1 ;; esac
    # Reject parent-traversal segments
    case "$path" in *..*) return 1 ;; esac
    # Reject UNC-style paths (Windows-ish input slipping through bash)
    case "$path" in //*|\\\\*) return 1 ;; esac
    # Manifest records are tab/newline delimited.
    case "$path" in *$'\n'*|*$'\r'*|*$'\t'*) return 1 ;; esac
    return 0
}

print_help() {
    cat <<EOF
Claude Ads Installer

Usage:
  bash install.sh [--target=<host>] [--skill-dir=<path>] [--agent-dir=<path>]
                  [--source=<auto|local|git>] [--repo-dir=<path>] [--no-deps]

Targets (default: claude):
  claude     Claude Code (verified)
  codex      OpenAI Codex CLI (experimental)
  cursor     Cursor IDE (experimental)
  windsurf   Windsurf IDE (experimental)
  gemini     Gemini CLI (experimental)
  goose      Goose CLI (experimental)

Overrides:
  --skill-dir=<path>   Override the target's default skill install root
  --agent-dir=<path>   Override the target's default agent install root
  --source=<mode>      auto uses this checkout when available, otherwise authenticated Git
  --repo-dir=<path>    Local checkout to install (implies --source=local)
  --no-deps            Do not create the verified managed Python environment

Examples:
  bash install.sh
  bash install.sh --target=codex
  bash install.sh --source=local --no-deps
  bash install.sh --target=claude --skill-dir=~/custom/skills

Security:
  Prefer a host-native plugin install or a signed release archive with a
  verified SHA-256 checksum. Never pipe a remote installer directly to a shell.

EOF
}

main() {
    # Defaults
    local TARGET="claude"
    local SKILL_DIR_OVERRIDE=""
    local AGENT_DIR_OVERRIDE=""
    local SOURCE_MODE="auto"
    local REPO_DIR=""
    local INSTALL_DEPS=1

    # Parse args
    while [ $# -gt 0 ]; do
        case "$1" in
            --target=*)
                TARGET="${1#*=}"
                ;;
            --target)
                shift
                [ $# -eq 0 ] && { echo "✗ --target requires a value" >&2; exit 1; }
                TARGET="$1"
                ;;
            --skill-dir=*)
                SKILL_DIR_OVERRIDE="${1#*=}"
                ;;
            --skill-dir)
                shift
                [ $# -eq 0 ] && { echo "✗ --skill-dir requires a value" >&2; exit 1; }
                SKILL_DIR_OVERRIDE="$1"
                ;;
            --agent-dir=*)
                AGENT_DIR_OVERRIDE="${1#*=}"
                ;;
            --agent-dir)
                shift
                [ $# -eq 0 ] && { echo "✗ --agent-dir requires a value" >&2; exit 1; }
                AGENT_DIR_OVERRIDE="$1"
                ;;
            --source=*)
                SOURCE_MODE="${1#*=}"
                ;;
            --source)
                shift
                [ $# -eq 0 ] && { echo "✗ --source requires a value" >&2; exit 1; }
                SOURCE_MODE="$1"
                ;;
            --repo-dir=*)
                REPO_DIR="${1#*=}"
                SOURCE_MODE="local"
                ;;
            --repo-dir)
                shift
                [ $# -eq 0 ] && { echo "✗ --repo-dir requires a value" >&2; exit 1; }
                REPO_DIR="$1"
                SOURCE_MODE="local"
                ;;
            --no-deps)
                INSTALL_DEPS=0
                ;;
            --help|-h)
                print_help
                exit 0
                ;;
            *)
                echo "✗ Unknown argument: $1" >&2
                echo "  Run: bash install.sh --help" >&2
                exit 1
                ;;
        esac
        shift
    done

    # Resolve target paths (rejects unknown targets via whitelist)
    if ! resolve_target_paths "$TARGET"; then
        echo "✗ Unknown target: $TARGET" >&2
        echo "  Valid targets: claude, codex, cursor, windsurf, gemini, goose" >&2
        echo "  Run: bash install.sh --help" >&2
        exit 1
    fi

    # Apply path overrides (with strict validation)
    if [ -n "$SKILL_DIR_OVERRIDE" ]; then
        validate_install_path "$SKILL_DIR_OVERRIDE" || {
            echo "✗ Invalid --skill-dir: contains forbidden characters or traversal" >&2
            exit 1
        }
        SKILL_BASE="$SKILL_DIR_OVERRIDE"
    fi
    if [ -n "$AGENT_DIR_OVERRIDE" ]; then
        validate_install_path "$AGENT_DIR_OVERRIDE" || {
            echo "✗ Invalid --agent-dir: contains forbidden characters or traversal" >&2
            exit 1
        }
        AGENT_DIR="$AGENT_DIR_OVERRIDE"
    fi

    local SKILL_DIR="${SKILL_BASE}/ads"
    local MANIFEST_PATH="${SKILL_BASE}/.claude-ads-${TARGET}.manifest"
    local POWERSHELL_MANIFEST_PATH="${MANIFEST_PATH}.json"
    local SOURCE_DIR=""
    local TEMP_DIR=""
    local MANIFEST_TMP=""
    trap 'rm -rf "${TEMP_DIR:-}" "${MANIFEST_TMP:-}"' EXIT

    case "$SOURCE_MODE" in
        auto)
            if [ -f "${SCRIPT_DIR}/ads/SKILL.md" ] && [ -d "${SCRIPT_DIR}/skills" ]; then
                SOURCE_MODE="local"
                SOURCE_DIR="${SCRIPT_DIR}"
            else
                SOURCE_MODE="git"
            fi
            ;;
        local)
            SOURCE_DIR="${REPO_DIR:-${SCRIPT_DIR}}"
            ;;
        git) ;;
        *)
            echo "✗ Invalid --source: ${SOURCE_MODE}. Use auto, local, or git." >&2
            exit 1
            ;;
    esac

    if [ "$SOURCE_MODE" = "local" ]; then
        validate_install_path "$SOURCE_DIR" || {
            echo "✗ Invalid local repository path" >&2
            exit 1
        }
        SOURCE_DIR=$(CDPATH= cd -- "$SOURCE_DIR" 2>/dev/null && pwd) || {
            echo "✗ Local repository does not exist: ${REPO_DIR:-${SCRIPT_DIR}}" >&2
            exit 1
        }
        [ -f "${SOURCE_DIR}/ads/SKILL.md" ] && [ -d "${SOURCE_DIR}/skills" ] || {
            echo "✗ Local source is not a Claude Ads distribution: ${SOURCE_DIR}" >&2
            exit 1
        }
    fi

    # Bash and PowerShell use different ownership-manifest contracts. Never
    # let one installer infer overwrite authority from the other contract.
    if [ -e "$POWERSHELL_MANIFEST_PATH" ]; then
        echo "✗ PowerShell ownership manifest detected: ${POWERSHELL_MANIFEST_PATH}" >&2
        echo "  Continue with install.ps1, or uninstall with uninstall.ps1 before switching installers." >&2
        return 1
    fi

    # Fail before any destination mutation or dependency network access when
    # the requested managed runtime is outside the supported wheel-lock matrix.
    if [ "${ALLOW_PIP}" = "1" ] && [ "$INSTALL_DEPS" = "1" ]; then
        command -v python3 >/dev/null 2>&1 || {
            echo "✗ python3 not found. Re-run with --no-deps to install without Python helpers." >&2
            return 1
        }
        PYTHON_TARGET=$(python3 -c 'import platform,sys
system=platform.system().lower(); machine=platform.machine().lower(); libc_name,libc_version=platform.libc_ver(); mac_version=platform.mac_ver()[0]
def pair(value):
    try: return tuple(int(part) for part in value.split(".")[:2])
    except ValueError: return (0,0)
boundary_ok=(system=="linux" and libc_name=="glibc" and pair(libc_version)>=(2,17)) or (system=="darwin" and pair(mac_version)>=(11,0))
print("|".join((sys.implementation.name, f"{sys.version_info.major}.{sys.version_info.minor}", system, machine, libc_name or "none", libc_version or mac_version or "none", "supported" if boundary_ok else "unsupported")))')
        case "$PYTHON_TARGET" in
            cpython\|3.11\|linux\|x86_64\|glibc\|*\|supported) DEPENDENCY_TARGET_ID="runtime-linux-cp311" ;;
            cpython\|3.12\|linux\|x86_64\|glibc\|*\|supported) DEPENDENCY_TARGET_ID="runtime-linux-cp312" ;;
            cpython\|3.11\|darwin\|x86_64\|*\|*\|supported) DEPENDENCY_TARGET_ID="runtime-macos-x86-cp311" ;;
            cpython\|3.12\|darwin\|x86_64\|*\|*\|supported) DEPENDENCY_TARGET_ID="runtime-macos-x86-cp312" ;;
            cpython\|3.11\|darwin\|arm64\|*\|*\|supported) DEPENDENCY_TARGET_ID="runtime-macos-arm-cp311" ;;
            cpython\|3.12\|darwin\|arm64\|*\|*\|supported) DEPENDENCY_TARGET_ID="runtime-macos-arm-cp312" ;;
            *\|windows\|*) echo "✗ install.sh does not manage Windows Python dependencies. Use install.ps1 -Source local." >&2; return 1 ;;
            *\|linux\|*\|musl\|*\|unsupported) echo "✗ Managed dependencies require glibc >=2.17; musl Linux is unsupported. Re-run with --no-deps." >&2; return 1 ;;
            *) echo "✗ No verified dependency lock target for ${PYTHON_TARGET}. Re-run with --no-deps; moving-range fallback is disabled." >&2; return 1 ;;
        esac
    fi

    echo "════════════════════════════════════════"
    echo "║   Claude Ads - Installer             ║"
    echo "║   Target: ${HOST_LABEL}"
    echo "════════════════════════════════════════"
    echo ""

    # Resolve distribution source. Private Git installs use the operator's
    # existing credential helper/SSH setup; credentials are never accepted as
    # command arguments or embedded into the URL.
    if [ "$SOURCE_MODE" = "git" ]; then
        command -v git >/dev/null 2>&1 || { echo "✗ Git is required for --source=git."; exit 1; }
        TEMP_DIR=$(mktemp -d)
        echo "↓ Downloading Claude Ads with authenticated Git..."
        git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/claude-ads"
        SOURCE_DIR="${TEMP_DIR}/claude-ads"
    fi
    echo "✓ Distribution source: ${SOURCE_MODE}"

    mkdir -p "${SKILL_BASE}" "${AGENT_DIR}"
    SKILL_BASE_CANON=$(CDPATH= cd -- "$SKILL_BASE" && pwd -P)
    AGENT_DIR_CANON=$(CDPATH= cd -- "$AGENT_DIR" && pwd -P)
    MANIFEST_TMP=$(mktemp "${SKILL_BASE}/.claude-ads-manifest.XXXXXX")
    printf 'V\t1\nT\t%s\n' "$TARGET" > "$MANIFEST_TMP"

    record_file() { printf 'F\t%s\n' "$1" >> "$MANIFEST_TMP"; }
    record_dir() { printf 'D\t%s\n' "$1" >> "$MANIFEST_TMP"; }
    canonical_destination() {
        local destination="$1" parent base canonical_parent
        parent=$(dirname -- "$destination")
        base=$(basename -- "$destination")
        canonical_parent=$(CDPATH= cd -- "$parent" 2>/dev/null && pwd -P) || return 1
        printf '%s/%s\n' "$canonical_parent" "$base"
    }
    assert_owned_destination() {
        local destination="$1"
        case "$destination" in
            "${SKILL_BASE_CANON}"|"${SKILL_BASE_CANON}"/*|"${AGENT_DIR_CANON}"|"${AGENT_DIR_CANON}"/*) return 0 ;;
            *) echo "✗ Install destination escapes configured roots: ${destination}" >&2; return 1 ;;
        esac
    }
    ensure_owned_dir() {
        local directory="$1" canonical
        [ ! -L "$directory" ] || { echo "✗ Refusing symlinked install directory: ${directory}" >&2; return 1; }
        mkdir -p "$(dirname -- "$directory")"
        canonical=$(canonical_destination "$directory") || return 1
        assert_owned_destination "$canonical" || return 1
        mkdir -p "$canonical"
        CDPATH= cd -- "$canonical" && pwd -P
    }
    previously_owned_file() {
        local destination="$1"
        [ -f "$MANIFEST_PATH" ] || return 1
        awk -F '\t' -v destination="$destination" \
            '$1 == "F" && $2 == destination { found=1 } END { exit !found }' "$MANIFEST_PATH"
    }
    install_file() {
        local source="$1" destination="$2" canonical
        [ ! -L "$destination" ] || { echo "✗ Refusing symlinked install file: ${destination}" >&2; return 1; }
        ensure_owned_dir "$(dirname -- "$destination")" >/dev/null
        canonical=$(canonical_destination "$destination") || return 1
        assert_owned_destination "$canonical" || return 1
        if [ -e "$canonical" ] && ! previously_owned_file "$canonical"; then
            echo "✗ Refusing to overwrite unowned file: ${canonical}" >&2
            return 1
        fi
        cp "$source" "$canonical"
        record_file "$canonical"
    }

    SKILL_DIR=$(ensure_owned_dir "$SKILL_DIR")
    REFERENCES_DIR=$(ensure_owned_dir "${SKILL_DIR}/references")

    # Copy main skill + references
    echo "→ Installing skill files..."
    install_file "${SOURCE_DIR}/ads/SKILL.md" "${SKILL_DIR}/SKILL.md"
    for source_file in "${SOURCE_DIR}/ads/references/"*.md; do
        [ -f "$source_file" ] || continue
        install_file "$source_file" "${REFERENCES_DIR}/$(basename -- "$source_file")"
    done
    record_dir "$REFERENCES_DIR"
    if [ -d "${SOURCE_DIR}/ads/agents" ]; then
        INTERFACE_DIR=$(ensure_owned_dir "${SKILL_DIR}/agents")
        for source_file in "${SOURCE_DIR}/ads/agents/"*.yaml; do
            [ -f "$source_file" ] || continue
            install_file "$source_file" "${INTERFACE_DIR}/$(basename -- "$source_file")"
        done
        record_dir "$INTERFACE_DIR"
    fi

    # Copy sub-skills
    echo "→ Installing sub-skills..."
    for skill_dir in "${SOURCE_DIR}/skills"/*/; do
        skill_name=$(basename "${skill_dir}")
        target="${SKILL_BASE}/${skill_name}"
        target=$(ensure_owned_dir "$target")
        install_file "${skill_dir}SKILL.md" "${target}/SKILL.md"

        # Copy assets (industry templates) if they exist
        if [ -d "${skill_dir}assets" ]; then
            target_assets=$(ensure_owned_dir "${target}/assets")
            for source_file in "${skill_dir}assets/"*.md; do
                [ -f "$source_file" ] || continue
                install_file "$source_file" "${target_assets}/$(basename -- "$source_file")"
            done
            record_dir "$target_assets"
        fi
        record_dir "$target"
    done

    # Copy agents
    echo "→ Installing subagents..."
    for source_file in "${SOURCE_DIR}/agents/"*.md; do
        [ -f "$source_file" ] || continue
        install_file "$source_file" "${AGENT_DIR}/$(basename -- "$source_file")"
    done

    # Copy scripts (optional Python tools)
    SCRIPTS_DIR="${SKILL_DIR}/scripts"
    if [ -d "${SOURCE_DIR}/scripts" ]; then
        echo "→ Installing Python scripts..."
        SCRIPTS_DIR=$(ensure_owned_dir "$SCRIPTS_DIR")
        for source_file in "${SOURCE_DIR}/scripts/"*.py; do
            [ -f "$source_file" ] || continue
            install_file "$source_file" "${SCRIPTS_DIR}/$(basename -- "$source_file")"
        done
        install_file "${SOURCE_DIR}/requirements.txt" "${SKILL_DIR}/requirements.txt"
        install_file "${SOURCE_DIR}/requirements.lock" "${SKILL_DIR}/requirements.lock"
        CORE_DIR=$(ensure_owned_dir "${SCRIPTS_DIR}/claude_ads_core")
        for source_file in "${SOURCE_DIR}/claude_ads_core/"*.py; do
            [ -f "$source_file" ] || continue
            install_file "$source_file" "${CORE_DIR}/$(basename -- "$source_file")"
        done
        ADAPTERS_DIR=$(ensure_owned_dir "${CORE_DIR}/adapters")
        for source_file in "${SOURCE_DIR}/claude_ads_core/adapters/"*.py; do
            [ -f "$source_file" ] || continue
            install_file "$source_file" "${ADAPTERS_DIR}/$(basename -- "$source_file")"
        done
        SCHEMAS_DIR=$(ensure_owned_dir "${CORE_DIR}/schemas/v1")
        for source_file in "${SOURCE_DIR}/claude_ads_core/schemas/v1/"*.json; do
            [ -f "$source_file" ] || continue
            install_file "$source_file" "${SCHEMAS_DIR}/$(basename -- "$source_file")"
        done
        record_dir "$SCHEMAS_DIR"
        record_dir "$ADAPTERS_DIR"
        record_dir "$CORE_DIR"
        record_dir "${SCRIPTS_DIR}"
    fi

    # Commit ownership before dependency installation. A later pip failure is
    # therefore recoverable with uninstall and never leaves unowned files.
    if [ "${ALLOW_PIP}" = "1" ] && [ "$INSTALL_DEPS" = "1" ]; then
        VENV_DIR="${SKILL_DIR}/.venv"
        printf 'R\t%s\n' "$VENV_DIR" >> "$MANIFEST_TMP"
        record_file "${SKILL_DIR}/managed-runtime-receipt.json"
    fi
    record_dir "${SKILL_DIR}"
    mv -f "$MANIFEST_TMP" "$MANIFEST_PATH"
    MANIFEST_TMP=""
    echo "✓ Ownership manifest: ${MANIFEST_PATH}"

    # Install Python dependencies — only for hosts that explicitly support
    # Python execution (claude, codex). Other targets skip the pip step.
    echo ""
    if [ "${ALLOW_PIP}" = "1" ] && [ "$INSTALL_DEPS" = "1" ]; then
        RECEIPT_PATH="${SKILL_DIR}/managed-runtime-receipt.json"
        if ! rm -f -- "$RECEIPT_PATH"; then
            echo "✗ Could not invalidate the prior managed runtime receipt." >&2
            return 1
        fi
        echo "→ Installing exact hashed Python dependencies into a managed virtual environment..."
        if command -v python3 >/dev/null 2>&1; then
            if python3 -m venv "${VENV_DIR}" \
                && "${VENV_DIR}/bin/python" -m pip install -q --ignore-installed --report "${VENV_DIR}/install-report.json" --require-hashes --only-binary=:all: -r "${SKILL_DIR}/requirements.lock" \
                && SITE_PACKAGES=$("${VENV_DIR}/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])') \
                && printf '%s\n' "${SCRIPTS_DIR}" > "${SITE_PACKAGES}/claude-ads-core.pth" \
                && "${VENV_DIR}/bin/python" -m pip check \
                && "${VENV_DIR}/bin/python" "${SCRIPTS_DIR}/write_install_receipt.py" --inventory "${SOURCE_DIR}/control-plane/manifests/dependency-inventory.json" --lock "${SKILL_DIR}/requirements.lock" --evidence "${SOURCE_DIR}/control-plane/dependency-evidence/${DEPENDENCY_TARGET_ID}.json" --pip-report "${VENV_DIR}/install-report.json" --target-id "${DEPENDENCY_TARGET_ID}" --output "${SKILL_DIR}/managed-runtime-receipt.json"; then
                echo "  ✓ Exact locked Python dependencies installed in ${VENV_DIR}"
            else
                rm -rf "$VENV_DIR"
                rm -f -- "$RECEIPT_PATH"
                echo "✗ Exact hashed dependency installation failed; no moving-range fallback was attempted." >&2
                return 1
            fi
        else
            echo "✗ python3 not found. Use --no-deps to install without Python helpers." >&2
            return 1
        fi
    elif [ "$INSTALL_DEPS" = "0" ]; then
        echo "ℹ Skipping Python dependencies (--no-deps)."
    else
        echo "ℹ Skipping Python dependencies — ${HOST_LABEL} host runtime may not execute Python skills directly."
        echo "  Python helpers require the packaged exact-hash lock on a supported CPython wheel target."
    fi

    echo ""
    echo "ℹ Image generation requires an explicitly configured eligible provider/model"
    echo "  with capability evidence; Claude Ads does not probe or recommend a default."

    echo ""
    echo "✓ Claude Ads installed successfully for ${HOST_LABEL}!"
    echo ""
    echo "  Installed to:"
    echo "    Skills: ${SKILL_BASE}"
    echo "    Agents: ${AGENT_DIR}"
    echo ""
    echo "  Bundled:"
    SUB_SKILL_COUNT=$(find "${SOURCE_DIR}/skills" -mindepth 2 -maxdepth 2 -name SKILL.md -type f | wc -l | tr -d ' ')
    AGENT_COUNT=$(find "${SOURCE_DIR}/agents" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
    REFERENCE_COUNT=$(find "${SOURCE_DIR}/ads/references" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
    echo "    • 1 main skill (ads orchestrator)"
    echo "    • ${SUB_SKILL_COUNT} sub-skills (platform + lifecycle + functional + creative)"
    echo "    • ${AGENT_COUNT} agents"
    echo "    • ${REFERENCE_COUNT} reference files"
    echo "    • 12 industry templates"
    echo ""
    echo "Usage:"
    echo "  1. Start your host CLI"
    echo "  2. Run commands:       /ads audit"
    echo "                         /ads plan saas"
    echo "                         /ads google"
    echo ""
    echo "To uninstall: bash uninstall.sh --target=${TARGET}"
}

main "$@"
