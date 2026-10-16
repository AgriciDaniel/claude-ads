#!/usr/bin/env bash
set -euo pipefail

# Claude Ads Installer
# Wraps everything in main() to prevent partial execution on network failure.
#
# Default target is Claude Code. Cross-host targets are EXPERIMENTAL: they
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
#   bash install.sh --source=git --ref=v2.0.2    # clone, then pin to a tag, branch, or commit
#
# All target keys are validated against a strict whitelist (no shell injection
# possible via --target=...). Custom --skill-dir and --agent-dir paths are
# validated against shell metacharacters (`;&|$()<>` and backtick), backslashes,
# control characters (newline, carriage return, tab), leading dashes, `..` path
# components, and UNC-style paths. Spaces are allowed because every path is
# quoted and a user home directory may legitimately contain them. A leading `~`
# or `~/` is expanded to $HOME because bash does not expand a tilde after `=`.
#
# --source=git clones the default branch HEAD of the public repository and is
# NOT pinned to a release. Releases publish a zip, SHA256SUMS, an SBOM and a
# manifest (no signatures); see the README for the checksum recipe.
#
# --ref=<tag|branch|commit> is an opt-in pin for --source=git only. The value is
# validated strictly before any use (at most 100 characters of letters, digits,
# dot, underscore, hyphen, and slash; no leading hyphen, dot, or slash; no `..`,
# `//`, or trailing slash), resolved to a full commit SHA after the clone, and checked
# out detached through `--end-of-options`, so it can never be parsed as an option.
# A git ref is not a checksum-verified release and nothing here is signed. An
# unresolvable ref fails before any install-root mutation.

REPO_URL="https://github.com/AgriciDaniel/claude-ads"
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

# Temporary paths are globals so the EXIT trap can see them on every exit path
# (normal return, `return 1` from main, and `exit 1`). Locals declared in main()
# are out of scope when the trap fires.
TEMP_DIR=""
MANIFEST_TMP=""
PLAN_DIR=""

cleanup() {
    local path
    for path in "$TEMP_DIR" "$MANIFEST_TMP" "$PLAN_DIR"; do
        [ -n "$path" ] || continue
        rm -rf -- "$path"
    done
    return 0
}
trap cleanup EXIT

# ─────────────────────────────────────────────────────────────────────────────
# Target whitelist + path mapping
# ─────────────────────────────────────────────────────────────────────────────
#
# Keep this table the SINGLE source of truth. When a new host CLI is added,
# update only this case statement plus the help text.
#
# claude    : Claude Code (VERIFIED, GA)
# codex     : OpenAI Codex CLI (EXPERIMENTAL, verify before relying on)
# cursor    : Cursor IDE (EXPERIMENTAL, extension model differs)
# windsurf  : Windsurf IDE (EXPERIMENTAL)
# gemini    : Gemini CLI (EXPERIMENTAL)
# goose     : Goose CLI (EXPERIMENTAL)

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
    # Reject parent-traversal components. Names that merely contain two dots,
    # such as `my..skills` or `v1..2`, are legitimate.
    case "$path" in ..|../*|*/..|*/../*) return 1 ;; esac
    # Reject UNC-style paths (Windows-ish input slipping through bash)
    case "$path" in //*|\\\\*) return 1 ;; esac
    # Manifest records are tab/newline delimited.
    case "$path" in *$'\n'*|*$'\r'*|*$'\t'*) return 1 ;; esac
    return 0
}

# Bash does not expand a tilde that follows `=` (as in `--skill-dir=~/x`), so a
# literal `~` directory would be created. Expand a leading `~` or `~/` to $HOME.
# Other tilde forms (`~user/x`) are not supported and are rejected by the caller.
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

validate_runtime_resource_path() {
    local relative="$1"
    [ -n "$relative" ] || return 1
    case "$relative" in
        control-plane/*) ;;
        *) return 1 ;;
    esac
    case "$relative" in
        /*|*\\*|*//*|*/../*|../*|*/..|..|*/./*|./*|*/.|.) return 1 ;;
        *[!A-Za-z0-9._/-]*) return 1 ;;
    esac
    return 0
}

# A --ref value must be a plain ref or commit name. It is rejected before any
# git call so it can never be parsed as an option or act as a path trick.
validate_git_ref() {
    local ref="$1"
    local LC_ALL=C
    [ -n "$ref" ] || return 1
    [ "${#ref}" -le 100 ] || return 1
    # Allow letters, digits, dot, underscore, hyphen, and slash only. This also
    # rejects whitespace, control characters, and shell or git revision syntax.
    case "$ref" in *[!A-Za-z0-9._/-]*) return 1 ;; esac
    # No option lookalikes, hidden or relative names, or absolute paths.
    case "$ref" in -*|.*|/*) return 1 ;; esac
    # No parent traversal, empty path components, or trailing slash.
    case "$ref" in *..*|*//*|*/) return 1 ;; esac
    return 0
}

# Resolve a validated ref to one full commit SHA inside a fresh clone. Tags and
# commits resolve directly; a branch resolves through its remote-tracking ref.
resolve_git_ref() {
    local repo="$1" ref="$2" candidate sha
    for candidate in "${ref}^{commit}" "refs/remotes/origin/${ref}^{commit}"; do
        sha=$(git -C "$repo" rev-parse --verify --quiet --end-of-options "$candidate" 2>/dev/null) || continue
        case "$sha" in ""|*[!0-9a-f]*) continue ;; esac
        case "${#sha}" in
            40|64) printf '%s' "$sha"; return 0 ;;
        esac
    done
    return 1
}

print_help() {
    cat <<EOF
Claude Ads Installer

Usage:
  bash install.sh [--target=<host>] [--skill-dir=<path>] [--agent-dir=<path>]
                  [--source=<auto|local|git>] [--ref=<tag|branch|commit>]
                  [--repo-dir=<path>] [--no-deps]

Targets (default: claude):
  claude     Claude Code (verified)
  codex      OpenAI Codex CLI (experimental)
  cursor     Cursor IDE (experimental)
  windsurf   Windsurf IDE (experimental)
  gemini     Gemini CLI (experimental)
  goose      Goose CLI (experimental)

Overrides:
  --skill-dir=<path>   Override the target's default skill install root
                       (a leading ~ or ~/ is expanded to your home directory)
  --agent-dir=<path>   Override the target's default agent install root
  --source=<mode>      auto uses this checkout when available, otherwise git
                       git clones the default branch HEAD (unpinned, not a release)
  --ref=<ref>          Pin --source=git to a tag, branch, or commit (opt-in).
                       Checked out detached and reported as a full commit SHA.
                       A git ref is not a checksum-verified release.
  --repo-dir=<path>    Local checkout to install (implies --source=local)
  --no-deps            Do not create the verified managed Python environment

Examples:
  bash install.sh
  bash install.sh --target=codex
  bash install.sh --source=local --no-deps
  bash install.sh --source=git --ref=v2.0.2
  bash install.sh --target=claude --skill-dir=~/custom/skills

Security:
  Prefer a host-native plugin install or a tagged release archive with a
  verified SHA-256 checksum (releases publish SHA256SUMS; they are not signed).
  --source=git is unpinned: it installs whatever the default branch holds now.
  --source=git --ref=<ref> installs exactly that git ref, which is still not a
  checksum-verified release and is not signed.
  Never pipe a remote installer directly to a shell.

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
    local GIT_REF=""
    local GIT_REF_SET=0
    local PINNED_SHA=""

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
            --ref=*)
                GIT_REF="${1#*=}"
                GIT_REF_SET=1
                ;;
            --ref)
                shift
                [ $# -eq 0 ] && { echo "✗ --ref requires a value" >&2; exit 1; }
                GIT_REF="$1"
                GIT_REF_SET=1
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

    # Validate --ref before any other use. The rejected value is not echoed
    # because it may contain control characters.
    if [ "$GIT_REF_SET" = "1" ]; then
        validate_git_ref "$GIT_REF" || {
            echo "✗ Invalid --ref: use 1 to 100 characters from letters, digits, . _ - /" >&2
            echo "  A ref must not start with - . or /, and must not contain .. or //" >&2
            exit 1
        }
    fi

    # Resolve target paths (rejects unknown targets via whitelist)
    if ! resolve_target_paths "$TARGET"; then
        echo "✗ Unknown target: $TARGET" >&2
        echo "  Valid targets: claude, codex, cursor, windsurf, gemini, goose" >&2
        echo "  Run: bash install.sh --help" >&2
        exit 1
    fi

    # Apply path overrides (with strict validation)
    if path_uses_unsupported_tilde "$SKILL_DIR_OVERRIDE" \
        || path_uses_unsupported_tilde "$AGENT_DIR_OVERRIDE" \
        || path_uses_unsupported_tilde "$REPO_DIR"; then
        echo "✗ Unsupported ~user path. Use an absolute path or a path starting with ~/" >&2
        exit 1
    fi
    SKILL_DIR_OVERRIDE=$(expand_home_path "$SKILL_DIR_OVERRIDE")
    AGENT_DIR_OVERRIDE=$(expand_home_path "$AGENT_DIR_OVERRIDE")
    REPO_DIR=$(expand_home_path "$REPO_DIR")
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

    case "$SKILL_BASE" in /*) ;; *) SKILL_BASE="$(pwd -P)/${SKILL_BASE}" ;; esac
    case "$AGENT_DIR" in /*) ;; *) AGENT_DIR="$(pwd -P)/${AGENT_DIR}" ;; esac
    SKILL_BASE=${SKILL_BASE%/}
    AGENT_DIR=${AGENT_DIR%/}
    [ -n "$SKILL_BASE" ] && [ -n "$AGENT_DIR" ] || {
        echo "✗ Configured install roots cannot be the filesystem root" >&2
        exit 1
    }

    local SKILL_DIR="${SKILL_BASE}/ads"
    local MANIFEST_PATH="${SKILL_BASE}/.claude-ads-${TARGET}.manifest"
    local POWERSHELL_MANIFEST_PATH="${MANIFEST_PATH}.json"
    local SOURCE_DIR=""

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

    if [ "$GIT_REF_SET" = "1" ] && [ "$SOURCE_MODE" != "git" ]; then
        echo "✗ --ref is only valid with --source=git (resolved source: ${SOURCE_MODE})." >&2
        echo "  A local install uses the checkout as it is; use a verified release archive instead." >&2
        exit 1
    fi

    if [ "$SOURCE_MODE" = "local" ]; then
        validate_install_path "$SOURCE_DIR" || {
            echo "✗ Invalid local repository path" >&2
            exit 1
        }
        SOURCE_DIR=$(CDPATH='' cd -- "$SOURCE_DIR" 2>/dev/null && pwd) || {
            echo "✗ Local repository does not exist: ${REPO_DIR:-${SCRIPT_DIR}}" >&2
            exit 1
        }
        [ -f "${SOURCE_DIR}/ads/SKILL.md" ] \
            && [ -d "${SOURCE_DIR}/skills" ] \
            && [ -f "${SOURCE_DIR}/control-plane/runtime-resources.txt" ] || {
            echo "✗ Local source is not a Claude Ads distribution: ${SOURCE_DIR}" >&2
            exit 1
        }
    fi

    # Bash and PowerShell use different ownership-manifest contracts. Never
    # let one installer infer overwrite authority from the other contract.
    if [ -e "$POWERSHELL_MANIFEST_PATH" ] || [ -L "$POWERSHELL_MANIFEST_PATH" ]; then
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
boundary_ok=(system=="linux" and libc_name=="glibc" and pair(libc_version)>=(2,28)) or (system=="darwin" and pair(mac_version)>=(11,0))
print("|".join((sys.implementation.name, f"{sys.version_info.major}.{sys.version_info.minor}", system, machine, libc_name or "none", libc_version or mac_version or "none", "supported" if boundary_ok else "unsupported")))')
        case "$PYTHON_TARGET" in
            cpython\|3.11\|linux\|x86_64\|glibc\|*\|supported) DEPENDENCY_TARGET_ID="runtime-linux-cp311" ;;
            cpython\|3.12\|linux\|x86_64\|glibc\|*\|supported) DEPENDENCY_TARGET_ID="runtime-linux-cp312" ;;
            cpython\|3.11\|darwin\|x86_64\|*\|*\|supported) DEPENDENCY_TARGET_ID="runtime-macos-x86-cp311" ;;
            cpython\|3.12\|darwin\|x86_64\|*\|*\|supported) DEPENDENCY_TARGET_ID="runtime-macos-x86-cp312" ;;
            cpython\|3.11\|darwin\|arm64\|*\|*\|supported) DEPENDENCY_TARGET_ID="runtime-macos-arm-cp311" ;;
            cpython\|3.12\|darwin\|arm64\|*\|*\|supported) DEPENDENCY_TARGET_ID="runtime-macos-arm-cp312" ;;
            *\|windows\|*) echo "✗ install.sh does not manage Windows Python dependencies. Use install.ps1 -Source local." >&2; return 1 ;;
            *\|linux\|*\|musl\|*\|unsupported) echo "✗ Managed dependencies require glibc >=2.28; musl Linux is unsupported. Re-run with --no-deps." >&2; return 1 ;;
            *) echo "✗ No verified dependency lock target for ${PYTHON_TARGET}. Re-run with --no-deps; moving-range fallback is disabled." >&2; return 1 ;;
        esac
    fi

    echo "════════════════════════════════════════"
    echo "║   Claude Ads - Installer             ║"
    echo "║   Target: ${HOST_LABEL}"
    echo "════════════════════════════════════════"
    echo ""

    # Resolve distribution source. Git installs use the operator's existing
    # Git configuration; credentials are never accepted as command arguments or
    # embedded into the URL. The clone is NOT pinned to a release tag.
    if [ "$SOURCE_MODE" = "git" ]; then
        command -v git >/dev/null 2>&1 || { echo "✗ Git is required for --source=git." >&2; exit 1; }
        TEMP_DIR=$(mktemp -d)
        # macOS reports temp dirs under the /var symlink. Use the physical path so
        # the symlink guard accepts the clone; keep the original on failure so the
        # EXIT trap still removes it.
        PHYSICAL_TEMP=$(cd "$TEMP_DIR" && pwd -P) || { echo "✗ Cannot resolve the temporary directory" >&2; exit 1; }
        TEMP_DIR="$PHYSICAL_TEMP"
        if [ -n "$GIT_REF" ]; then
            echo "↓ Downloading Claude Ads with Git (pinned to git ref ${GIT_REF}; a git ref is not a checksum-verified release)..."
            # A full clone without a checkout, so any tag, branch, or commit can
            # be resolved before a single file is written.
            git clone --no-checkout "${REPO_URL}" "${TEMP_DIR}/claude-ads"
            PINNED_SHA=$(resolve_git_ref "${TEMP_DIR}/claude-ads" "$GIT_REF") || {
                echo "✗ Git ref does not resolve to a commit: ${GIT_REF}" >&2
                echo "  Nothing was installed." >&2
                exit 1
            }
            git -c advice.detachedHead=false -C "${TEMP_DIR}/claude-ads" \
                checkout --detach --end-of-options "$PINNED_SHA" -- || {
                echo "✗ Could not check out git ref ${GIT_REF} (${PINNED_SHA}). Nothing was installed." >&2
                exit 1
            }
            [ "$(git -C "${TEMP_DIR}/claude-ads" rev-parse --verify HEAD 2>/dev/null)" = "$PINNED_SHA" ] || {
                echo "✗ Checked-out commit does not match the resolved ref ${GIT_REF}. Nothing was installed." >&2
                exit 1
            }
        else
            echo "↓ Downloading Claude Ads with Git (default branch HEAD, unpinned, not a verified release)..."
            git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/claude-ads"
        fi
        SOURCE_DIR="${TEMP_DIR}/claude-ads"
    fi
    echo "✓ Distribution source: ${SOURCE_MODE}"
    if [ -n "$PINNED_SHA" ]; then
        echo "✓ Pinned git ref: ${GIT_REF}"
        echo "  Resolved commit: ${PINNED_SHA}"
        echo "  This is a git ref, not a checksum-verified release, and it is not signed."
    fi

    # Validate the public runtime resource list before touching either install
    # root. The list is data, never shell input, and every entry must resolve to
    # one regular public file inside the distribution.
    local RUNTIME_RESOURCE_LIST="${SOURCE_DIR}/control-plane/runtime-resources.txt"
    local RUNTIME_RESOURCE_SEEN=$'\n'
    [ -f "$RUNTIME_RESOURCE_LIST" ] && [ ! -L "$RUNTIME_RESOURCE_LIST" ] || {
        echo "✗ Missing or symlinked runtime resource allowlist" >&2
        return 1
    }
    while IFS= read -r runtime_resource || [ -n "$runtime_resource" ]; do
        case "$runtime_resource" in ""|\#*) continue ;; esac
        validate_runtime_resource_path "$runtime_resource" || {
            echo "✗ Unsafe runtime resource path: ${runtime_resource}" >&2
            return 1
        }
        runtime_resource_key=$(printf '%s' "$runtime_resource" | tr '[:upper:]' '[:lower:]')
        case "$RUNTIME_RESOURCE_SEEN" in
            *$'\n'"${runtime_resource_key}"$'\n'*)
                echo "✗ Duplicate runtime resource path: ${runtime_resource}" >&2
                return 1
                ;;
        esac
        RUNTIME_RESOURCE_SEEN="${RUNTIME_RESOURCE_SEEN}${runtime_resource_key}"$'\n'
        [ -f "${SOURCE_DIR}/${runtime_resource}" ] \
            && [ ! -L "${SOURCE_DIR}/${runtime_resource}" ] || {
            echo "✗ Missing or symlinked runtime resource: ${runtime_resource}" >&2
            return 1
        }
    done < "$RUNTIME_RESOURCE_LIST"

    # Build and validate the complete source and destination plan before the
    # first install-root mutation. The plan is plain tab-delimited data and is
    # never evaluated as shell input.
    local FILE_PLAN OUTPUT_PLAN DIR_PLAN DESTINATION_KEYS
    local PRIOR_FILES PRIOR_DIRS PRIOR_RECURSIVE PRIOR_BYTECODE PRIOR_ALL
    local CURRENT_FILES CURRENT_DIRS CURRENT_RECURSIVE CURRENT_BYTECODE
    PLAN_DIR=$(mktemp -d)
    FILE_PLAN="${PLAN_DIR}/files"
    OUTPUT_PLAN="${PLAN_DIR}/outputs"
    DIR_PLAN="${PLAN_DIR}/directories"
    DESTINATION_KEYS="${PLAN_DIR}/destination-keys"
    PRIOR_FILES="${PLAN_DIR}/prior-files"
    PRIOR_DIRS="${PLAN_DIR}/prior-directories"
    PRIOR_RECURSIVE="${PLAN_DIR}/prior-recursive"
    PRIOR_BYTECODE="${PLAN_DIR}/prior-bytecode"
    PRIOR_ALL="${PLAN_DIR}/prior-all"
    CURRENT_FILES="${PLAN_DIR}/current-files"
    CURRENT_DIRS="${PLAN_DIR}/current-directories"
    CURRENT_RECURSIVE="${PLAN_DIR}/current-recursive"
    CURRENT_BYTECODE="${PLAN_DIR}/current-bytecode"
    : > "$FILE_PLAN"; : > "$OUTPUT_PLAN"; : > "$DIR_PLAN"; : > "$DESTINATION_KEYS"
    : > "$PRIOR_FILES"; : > "$PRIOR_DIRS"; : > "$PRIOR_RECURSIVE"; : > "$PRIOR_BYTECODE"; : > "$PRIOR_ALL"
    : > "$CURRENT_FILES"; : > "$CURRENT_DIRS"; : > "$CURRENT_RECURSIVE"; : > "$CURRENT_BYTECODE"

    case "$SKILL_BASE" in /*) ;; *) SKILL_BASE="$(pwd -P)/${SKILL_BASE}" ;; esac
    case "$AGENT_DIR" in /*) ;; *) AGENT_DIR="$(pwd -P)/${AGENT_DIR}" ;; esac
    SKILL_BASE=${SKILL_BASE%/}
    AGENT_DIR=${AGENT_DIR%/}
    SKILL_DIR="${SKILL_BASE}/ads"
    MANIFEST_PATH="${SKILL_BASE}/.claude-ads-${TARGET}.manifest"
    POWERSHELL_MANIFEST_PATH="${MANIFEST_PATH}.json"
    case "${SKILL_BASE}/" in "${AGENT_DIR}/"*) echo "✗ Skill and agent install roots must not overlap" >&2; return 1 ;; esac
    case "${AGENT_DIR}/" in "${SKILL_BASE}/"*) echo "✗ Skill and agent install roots must not overlap" >&2; return 1 ;; esac

    plan_field_is_safe() {
        case "$1" in ""|*$'\n'*|*$'\r'*|*$'\t'*) return 1 ;; esac
        return 0
    }
    path_is_inside_roots() {
        case "$1" in "${SKILL_BASE}"/*|"${AGENT_DIR}"/*) return 0 ;; *) return 1 ;; esac
    }
    assert_no_symlink_chain() {
        local full="$1" current="$1"
        while :; do
            [ ! -L "$current" ] || { echo "✗ Refusing symlinked install directory or file: ${current}" >&2; return 1; }
            if [ "$current" != "$full" ] && [ -e "$current" ] && [ ! -d "$current" ]; then
                echo "✗ Install path parent is not a directory: ${current}" >&2
                return 1
            fi
            [ "$current" = "/" ] && break
            current=$(dirname -- "$current")
        done
    }
    assert_safe_recursive_links() {
        local tree="$1" links link target
        links=$(find "$tree" -type l -print) || return 1
        [ -n "$links" ] || return 0
        # Standard venvs link their interpreters and lib64. Only these known
        # child paths are allowed; the owned root and its parents stay unlinked.
        [ "$tree" = "${SKILL_DIR}/.venv" ] || return 1
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
    validate_owned_manifest_path() {
        local path="$1" kind="$2"
        plan_field_is_safe "$path" || return 1
        case "$path" in /*) ;; *) return 1 ;; esac
        case "$path" in */|*//*|*/../*|*/..|*/./*|*/.) return 1 ;; esac
        path_is_inside_roots "$path" || return 1
        [ "$path" != "$SKILL_BASE" ] && [ "$path" != "$AGENT_DIR" ] || return 1
        if [ "$kind" = "B" ]; then
            case "$path" in
                "${SKILL_DIR}/scripts/claude_ads_core/__pycache__"|"${SKILL_DIR}/scripts/claude_ads_core/adapters/__pycache__") ;;
                *) return 1 ;;
            esac
        fi
        assert_no_symlink_chain "$path" || return 1
        if [ -e "$path" ]; then
            case "$kind" in
                F) [ ! -d "$path" ] || return 1 ;;
                D|R|B) [ -d "$path" ] || return 1 ;;
            esac
        fi
        if [ "$kind" = "R" ] && [ -d "$path" ]; then
            assert_safe_recursive_links "$path" || return 1
        fi
        return 0
    }
    assert_managed_interpreter_binding() {
        local tree="$1"
        validate_owned_manifest_path "$tree" R || return 1
        # EnvBuilder preserves existing interpreter files and links. Inspect
        # them with the selected host Python before executing anything in the
        # owned environment. Copies must match the host binary byte for byte.
        python3 -I -S - "$tree" <<'PYTHON'
import hashlib
from pathlib import Path
import sys

def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").digest()

try:
    base = Path(sys._base_executable).resolve(strict=True)
    expected = digest(base)
    for candidate in (Path(sys.argv[1]) / "bin").glob("python*"):
        if not candidate.is_file() or digest(candidate) != expected:
            raise SystemExit("Existing managed interpreter does not match the selected host Python")
except OSError:
    raise SystemExit("Cannot verify the existing managed interpreter")
PYTHON
    }
    read_valid_prior_manifest() {
        local version_count=0 target_count=0 line_number=0 kind value path_key
        [ -e "$MANIFEST_PATH" ] || return 0
        [ -f "$MANIFEST_PATH" ] && [ ! -L "$MANIFEST_PATH" ] || {
            echo "✗ Invalid ownership manifest path: ${MANIFEST_PATH}" >&2
            return 1
        }
        awk -F '\t' 'NF != 2 { exit 1 }' "$MANIFEST_PATH" || {
            echo "✗ Invalid ownership manifest record shape: ${MANIFEST_PATH}" >&2
            return 1
        }
        while IFS=$'\t' read -r kind value; do
            line_number=$((line_number + 1))
            case "$kind" in
                V)
                    [ "$line_number" -eq 1 ] && [ "$value" = "1" ] || { echo "✗ Invalid ownership manifest version/header" >&2; return 1; }
                    version_count=$((version_count + 1))
                    ;;
                T)
                    [ "$line_number" -eq 2 ] && [ "$value" = "$TARGET" ] || { echo "✗ Ownership manifest target/header mismatch" >&2; return 1; }
                    target_count=$((target_count + 1))
                    ;;
                F|D|R|B)
                    validate_owned_manifest_path "$value" "$kind" || {
                        echo "✗ Unsafe ownership-manifest path: ${value}" >&2
                        return 1
                    }
                    [ "$line_number" -gt 2 ] || { echo "✗ Ownership records must follow manifest headers" >&2; return 1; }
                    path_key=$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')
                    if grep -Fqx -- "$path_key" "$PRIOR_ALL"; then
                        echo "✗ Duplicate ownership-manifest path: ${value}" >&2
                        return 1
                    fi
                    printf '%s\n' "$path_key" >> "$PRIOR_ALL"
                    case "$kind" in
                        F) printf '%s\n' "$value" >> "$PRIOR_FILES" ;;
                        D) printf '%s\n' "$value" >> "$PRIOR_DIRS" ;;
                        R) printf '%s\n' "$value" >> "$PRIOR_RECURSIVE" ;;
                        B) printf '%s\n' "$value" >> "$PRIOR_BYTECODE" ;;
                    esac
                    ;;
                *) echo "✗ Unknown ownership-manifest record: ${kind}" >&2; return 1 ;;
            esac
        done < "$MANIFEST_PATH"
        [ "$version_count" -eq 1 ] && [ "$target_count" -eq 1 ] || {
            echo "✗ Ownership manifest must contain exactly one V and one T record" >&2
            return 1
        }
    }
    add_planned_directory() {
        local directory="$1" current key
        plan_field_is_safe "$directory" || {
            echo "✗ Unsafe planned install directory: ${directory}" >&2
            return 1
        }
        if [ "$directory" = "$SKILL_BASE" ] || [ "$directory" = "$AGENT_DIR" ]; then
            return 0
        fi
        path_is_inside_roots "$directory" || {
            echo "✗ Unsafe planned install directory: ${directory}" >&2
            return 1
        }
        current="$directory"
        while [ "$current" != "$SKILL_BASE" ] && [ "$current" != "$AGENT_DIR" ]; do
            key=$(printf '%s' "$current" | tr '[:upper:]' '[:lower:]')
            grep -Fqx -- "$key" "${DIR_PLAN}.keys" 2>/dev/null || {
                printf '%s\n' "$current" >> "$DIR_PLAN"
                printf '%s\n' "$key" >> "${DIR_PLAN}.keys"
            }
            current=$(dirname -- "$current")
            path_is_inside_roots "$current" || [ "$current" = "$SKILL_BASE" ] || [ "$current" = "$AGENT_DIR" ] || return 1
        done
    }
    add_planned_destination() {
        local destination="$1" key
        if ! plan_field_is_safe "$destination" || ! path_is_inside_roots "$destination"; then
            echo "✗ Unsafe planned install file: ${destination}" >&2
            return 1
        fi
        key=$(printf '%s' "$destination" | tr '[:upper:]' '[:lower:]')
        grep -Fqx -- "$key" "$DESTINATION_KEYS" && {
            echo "✗ Duplicate planned install file: ${destination}" >&2
            return 1
        }
        printf '%s\n' "$key" >> "$DESTINATION_KEYS"
        add_planned_directory "$(dirname -- "$destination")"
    }
    add_planned_file() {
        local source="$1" destination="$2"
        plan_field_is_safe "$source" || { echo "✗ Unsafe source path" >&2; return 1; }
        [ -f "$source" ] && [ ! -L "$source" ] || {
            echo "✗ Missing or symlinked install source: ${source}" >&2
            return 1
        }
        assert_no_symlink_chain "$source" || return 1
        add_planned_destination "$destination"
        printf '%s\t%s\n' "$source" "$destination" >> "$FILE_PLAN"
    }
    add_planned_output() {
        add_planned_destination "$1"
        printf '%s\n' "$1" >> "$OUTPUT_PLAN"
    }
    add_planned_bytecode_root() {
        local directory="$1" key
        if ! plan_field_is_safe "$directory" || ! path_is_inside_roots "$directory"; then
            echo "✗ Unsafe planned bytecode cache root: ${directory}" >&2
            return 1
        fi
        case "$directory" in
            "${SCRIPTS_DIR}/claude_ads_core/__pycache__"|"${SCRIPTS_DIR}/claude_ads_core/adapters/__pycache__") ;;
            *) echo "✗ Unsupported planned bytecode cache root: ${directory}" >&2; return 1 ;;
        esac
        key=$(printf '%s' "$directory" | tr '[:upper:]' '[:lower:]')
        if grep -Fqx -- "$key" "$PRIOR_ALL" && ! grep -Fqx -- "$directory" "$PRIOR_BYTECODE"; then
            echo "✗ Bytecode cache root conflicts with prior ownership: ${directory}" >&2
            return 1
        fi
        grep -Fqx -- "$directory" "$CURRENT_BYTECODE" || printf '%s\n' "$directory" >> "$CURRENT_BYTECODE"
    }
    add_matching_files() {
        local destination="$1" source_file
        shift
        for source_file in "$@"; do
            [ -e "$source_file" ] || [ -L "$source_file" ] || continue
            add_planned_file "$source_file" "${destination}/$(basename -- "$source_file")"
        done
    }

    read_valid_prior_manifest

    [ -d "${SOURCE_DIR}/ads/references" ] && [ ! -L "${SOURCE_DIR}/ads/references" ] || {
        echo "✗ Missing or symlinked install source directory: ${SOURCE_DIR}/ads/references" >&2; return 1;
    }
    [ -d "${SOURCE_DIR}/skills" ] && [ ! -L "${SOURCE_DIR}/skills" ] || {
        echo "✗ Missing or symlinked install source directory: ${SOURCE_DIR}/skills" >&2; return 1;
    }
    [ -d "${SOURCE_DIR}/agents" ] && [ ! -L "${SOURCE_DIR}/agents" ] || {
        echo "✗ Missing or symlinked install source directory: ${SOURCE_DIR}/agents" >&2; return 1;
    }
    add_planned_file "${SOURCE_DIR}/ads/SKILL.md" "${SKILL_DIR}/SKILL.md"
    add_matching_files "${SKILL_DIR}/references" "${SOURCE_DIR}"/ads/references/*.md
    if [ -d "${SOURCE_DIR}/ads/agents" ]; then
        [ ! -L "${SOURCE_DIR}/ads/agents" ] || { echo "✗ Symlinked install source directory" >&2; return 1; }
        add_matching_files "${SKILL_DIR}/agents" "${SOURCE_DIR}"/ads/agents/*.yaml
    fi
    for skill_dir in "${SOURCE_DIR}/skills/"*/; do
        [ -d "$skill_dir" ] || continue
        [ ! -L "${skill_dir%/}" ] || { echo "✗ Symlinked sub-skill source: ${skill_dir}" >&2; return 1; }
        skill_name=$(basename -- "$skill_dir")
        target="${SKILL_BASE}/${skill_name}"
        add_planned_file "${skill_dir}SKILL.md" "${target}/SKILL.md"
        if [ -d "${skill_dir}assets" ]; then
            [ ! -L "${skill_dir}assets" ] || { echo "✗ Symlinked asset source" >&2; return 1; }
            add_matching_files "${target}/assets" "${skill_dir}"assets/*.md
        fi
    done
    add_matching_files "$AGENT_DIR" "${SOURCE_DIR}"/agents/*.md

    SCRIPTS_DIR="${SKILL_DIR}/scripts"
    if [ -d "${SOURCE_DIR}/scripts" ]; then
        [ ! -L "${SOURCE_DIR}/scripts" ] || { echo "✗ Symlinked scripts source" >&2; return 1; }
        for source_file in "${SOURCE_DIR}"/scripts/*.py; do
            [ -e "$source_file" ] || [ -L "$source_file" ] || continue
            [ "$(basename -- "$source_file")" = "verify_managed_install.py" ] && continue
            add_planned_file "$source_file" "${SCRIPTS_DIR}/$(basename -- "$source_file")"
        done
        add_planned_file "${SOURCE_DIR}/requirements.txt" "${SKILL_DIR}/requirements.txt"
        add_planned_file "${SOURCE_DIR}/requirements.lock" "${SKILL_DIR}/requirements.lock"
        for required_dir in "${SOURCE_DIR}/claude_ads_core" "${SOURCE_DIR}/claude_ads_core/adapters" "${SOURCE_DIR}/claude_ads_core/schemas/v1"; do
            [ -d "$required_dir" ] && [ ! -L "$required_dir" ] || {
                echo "✗ Missing or symlinked core source directory: ${required_dir}" >&2; return 1;
            }
        done
        add_matching_files "${SCRIPTS_DIR}/claude_ads_core" "${SOURCE_DIR}"/claude_ads_core/*.py
        add_matching_files "${SCRIPTS_DIR}/claude_ads_core/adapters" "${SOURCE_DIR}"/claude_ads_core/adapters/*.py
        add_matching_files "${SCRIPTS_DIR}/claude_ads_core/schemas/v1" "${SOURCE_DIR}"/claude_ads_core/schemas/v1/*.json
        add_planned_bytecode_root "${SCRIPTS_DIR}/claude_ads_core/__pycache__"
        add_planned_bytecode_root "${SCRIPTS_DIR}/claude_ads_core/adapters/__pycache__"
    fi
    while IFS= read -r runtime_resource || [ -n "$runtime_resource" ]; do
        case "$runtime_resource" in ""|\#*) continue ;; esac
        add_planned_file "${SOURCE_DIR}/${runtime_resource}" "${SKILL_DIR}/${runtime_resource}"
    done < "$RUNTIME_RESOURCE_LIST"

    if [ "${ALLOW_PIP}" = "1" ] && [ "$INSTALL_DEPS" = "1" ]; then
        VENV_DIR="${SKILL_DIR}/.venv"
        RECEIPT_PATH="${SKILL_DIR}/managed-runtime-receipt.json"
        add_planned_output "$RECEIPT_PATH"
        printf '%s\n' "$VENV_DIR" >> "$CURRENT_RECURSIVE"
    fi

    # A manifest-free collision is a legacy install. Report all paths before
    # any mutation. With a valid prior manifest, every existing file must be
    # listed as an owned F record.
    if [ ! -e "$MANIFEST_PATH" ]; then
        LEGACY_PATHS=""
        while IFS=$'\t' read -r _source destination; do
            if [ -e "$destination" ] || [ -L "$destination" ]; then
                LEGACY_PATHS="${LEGACY_PATHS}    ${destination}"$'\n'
            fi
        done < "$FILE_PLAN"
        if [ -n "$LEGACY_PATHS" ]; then
            {
                echo "✗ Existing Claude Ads files without an ownership manifest detected:"
                printf '%s' "$LEGACY_PATHS"
                echo "  Installs older than v2.0.0 wrote no ownership manifest, so this installer"
                echo "  cannot verify what it may overwrite. Remove the old install manually, then"
                echo "  re-run. Paths this installer would own for target ${TARGET}:"
                echo "    ${SKILL_DIR}/"
                echo "    ${AGENT_DIR}/"
                echo "    ${MANIFEST_PATH}"
            } >&2
            return 1
        fi
    fi

    assert_no_symlink_chain "$SKILL_BASE"
    assert_no_symlink_chain "$AGENT_DIR"
    while IFS= read -r directory; do
        assert_no_symlink_chain "$directory"
        [ ! -e "$directory" ] || [ -d "$directory" ] || {
            echo "✗ Install directory destination is not a directory: ${directory}" >&2; return 1;
        }
    done < "$DIR_PLAN"
    while IFS=$'\t' read -r source destination; do
        [ -f "$source" ] && [ ! -L "$source" ] || { echo "✗ Install source changed: ${source}" >&2; return 1; }
        assert_no_symlink_chain "$source"
        assert_no_symlink_chain "$destination"
        if [ -e "$destination" ] || [ -L "$destination" ]; then
            if [ -d "$destination" ] || ! grep -Fqx -- "$destination" "$PRIOR_FILES"; then
                echo "✗ Refusing to overwrite unowned file: ${destination}" >&2; return 1
            fi
        fi
    done < "$FILE_PLAN"
    while IFS= read -r destination; do
        assert_no_symlink_chain "$destination"
        if [ -e "$destination" ] || [ -L "$destination" ]; then
            if [ -d "$destination" ] || ! grep -Fqx -- "$destination" "$PRIOR_FILES"; then
                echo "✗ Refusing to overwrite unowned file: ${destination}" >&2; return 1
            fi
        fi
    done < "$OUTPUT_PLAN"
    while IFS= read -r directory; do
        assert_no_symlink_chain "$directory"
        [ ! -e "$directory" ] || [ -d "$directory" ] || {
            echo "✗ Bytecode cache root is not a directory: ${directory}" >&2; return 1;
        }
    done < "$CURRENT_BYTECODE"
    if [ -n "${VENV_DIR:-}" ] && [ -e "$VENV_DIR" ]; then
        if [ ! -d "$VENV_DIR" ] || ! grep -Fqx -- "$VENV_DIR" "$PRIOR_RECURSIVE"; then
            echo "✗ Refusing to reuse unowned managed environment: ${VENV_DIR}" >&2; return 1
        fi
        assert_managed_interpreter_binding "$VENV_DIR" || return 1
    fi

    # All source and collision checks passed. Recheck each path immediately
    # before mutation so a concurrent replacement cannot bypass the guard.
    mkdir -p "$SKILL_BASE" "$AGENT_DIR"
    SKILL_BASE_CANON=$(CDPATH='' cd -- "$SKILL_BASE" && pwd -P)
    AGENT_DIR_CANON=$(CDPATH='' cd -- "$AGENT_DIR" && pwd -P)
    [ "$SKILL_BASE_CANON" = "$SKILL_BASE" ] && [ "$AGENT_DIR_CANON" = "$AGENT_DIR" ] || {
        echo "✗ Configured install root changed during preflight" >&2; return 1;
    }
    sort "$DIR_PLAN" | while IFS= read -r directory; do
        assert_no_symlink_chain "$directory"
        if [ ! -e "$directory" ]; then
            mkdir -p "$directory"
            printf '%s\n' "$directory" >> "$CURRENT_DIRS"
        elif [ ! -d "$directory" ]; then
            echo "✗ Install directory changed type: ${directory}" >&2
            return 1
        fi
    done
    while IFS=$'\t' read -r source destination; do
        [ -f "$source" ] && [ ! -L "$source" ] || { echo "✗ Install source changed: ${source}" >&2; return 1; }
        assert_no_symlink_chain "$source"
        assert_no_symlink_chain "$destination"
        if [ -e "$destination" ] || [ -L "$destination" ]; then
            if [ -d "$destination" ] || ! grep -Fqx -- "$destination" "$PRIOR_FILES"; then
                echo "✗ Refusing to overwrite unowned file: ${destination}" >&2; return 1
            fi
        fi
        cp "$source" "$destination"
        printf '%s\n' "$destination" >> "$CURRENT_FILES"
    done < "$FILE_PLAN"

    MANIFEST_TMP=$(mktemp "${SKILL_BASE}/.claude-ads-manifest.XXXXXX")
    printf 'V\t1\nT\t%s\n' "$TARGET" > "$MANIFEST_TMP"
    while IFS= read -r path; do [ -n "$path" ] && printf 'F\t%s\n' "$path" >> "$MANIFEST_TMP"; done < "$PRIOR_FILES"
    while IFS= read -r path; do [ -n "$path" ] && printf 'D\t%s\n' "$path" >> "$MANIFEST_TMP"; done < "$PRIOR_DIRS"
    while IFS= read -r path; do [ -n "$path" ] && printf 'R\t%s\n' "$path" >> "$MANIFEST_TMP"; done < "$PRIOR_RECURSIVE"
    while IFS= read -r path; do [ -n "$path" ] && printf 'B\t%s\n' "$path" >> "$MANIFEST_TMP"; done < "$PRIOR_BYTECODE"
    while IFS= read -r path; do
        [ -n "$path" ] || continue
        grep -Fqx -- "$path" "$PRIOR_FILES" || printf 'F\t%s\n' "$path" >> "$MANIFEST_TMP"
    done < "$CURRENT_FILES"
    while IFS= read -r path; do
        [ -n "$path" ] || continue
        grep -Fqx -- "$path" "$PRIOR_DIRS" || printf 'D\t%s\n' "$path" >> "$MANIFEST_TMP"
    done < "$CURRENT_DIRS"
    while IFS= read -r path; do
        [ -n "$path" ] || continue
        grep -Fqx -- "$path" "$PRIOR_RECURSIVE" || printf 'R\t%s\n' "$path" >> "$MANIFEST_TMP"
    done < "$CURRENT_RECURSIVE"
    while IFS= read -r path; do
        [ -n "$path" ] || continue
        grep -Fqx -- "$path" "$PRIOR_BYTECODE" || printf 'B\t%s\n' "$path" >> "$MANIFEST_TMP"
    done < "$CURRENT_BYTECODE"
    while IFS= read -r path; do
        [ -n "$path" ] || continue
        grep -Fqx -- "$path" "$PRIOR_FILES" || printf 'F\t%s\n' "$path" >> "$MANIFEST_TMP"
    done < "$OUTPUT_PLAN"
    mv -f "$MANIFEST_TMP" "$MANIFEST_PATH"
    MANIFEST_TMP=""
    echo "✓ Ownership manifest: ${MANIFEST_PATH}"

    # Install Python dependencies, but only for hosts that explicitly support
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
            if [ -e "$VENV_DIR" ]; then
                assert_managed_interpreter_binding "$VENV_DIR" || return 1
            fi
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
        echo "ℹ Skipping Python dependencies: ${HOST_LABEL} host runtime may not execute Python skills directly."
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
    TEMPLATE_COUNT=0
    if [ -d "${SOURCE_DIR}/skills/ads-plan/assets" ]; then
        TEMPLATE_COUNT=$(find "${SOURCE_DIR}/skills/ads-plan/assets" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
    fi
    if [ "$TEMPLATE_COUNT" -gt 0 ]; then
        echo "    • ${TEMPLATE_COUNT} industry templates"
    fi
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
