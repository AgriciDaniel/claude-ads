#!/usr/bin/env python3
"""Audit and reproducibly package the public-safe Claude Ads release surface."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
from urllib.parse import unquote, urlsplit
import uuid
import zipfile


PACKAGE_PREFIXES = (
    ".claude-plugin/",
    "ads/",
    "agents/",
    "assets/",
    "claude_ads_core/",
    "control-plane/",
    "evals/",
    "scripts/",
    "skills/",
)
PACKAGE_FILES = {
    "CHANGELOG.md",
    "CITATION.cff",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    "THIRD_PARTY_NOTICES.md",
    "install.ps1",
    "install.sh",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.lock",
    "requirements-dev.lock",
    "tests/scripts/test_generate_report.py",
    "uninstall.ps1",
    "uninstall.sh",
}
PACKAGE_EXCLUDED_PREFIXES = ("ads/research-sources/",)
SENSITIVE_FILENAMES = {
    ".env",
    "credentials.json",
    "service-account.json",
    "service_account.json",
}
SENSITIVE_FILENAME_PREFIXES = ("credentials", "secrets", "config.local.")
SENSITIVE_ARTIFACT_SUFFIXES = {".db", ".log", ".sqlite", ".sqlite3"}
TEXT_SUFFIXES = {
    ".cff",
    ".css",
    ".csv",
    ".html",
    ".json",
    ".lock",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = {
    "private key": re.compile(
        r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{40,}"
    ),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[A-Za-z0-9_-]{30,}\b"),
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
}
PRIVATE_PATH_PATTERNS = {
    "Unix home path": re.compile(r"(?<![A-Za-z0-9])(?:/var)?/home/[A-Za-z0-9._-]+/"),
    "macOS home path": re.compile(r"(?<![A-Za-z0-9])/Users/[A-Za-z0-9._-]+/"),
    "Windows home path": re.compile(r"(?i)\b[A-Z]:\\Users\\[A-Za-z0-9._-]+\\"),
    "personal tilde path": re.compile(
        r"(?i)(?<![A-Za-z0-9])~/(?:Desktop|Documents|Downloads|Dropbox|Music|OneDrive|Pictures|Videos)/"
    ),
    "private Fable corpus path": re.compile(r"(?i)(?:/|\\)Desktop[/\\]Fable 5 Brain(?:/|\\)"),
    "private Brainstein vault path": re.compile(
        r"(?i)(?:/|\\)Desktop[/\\]Vaults[/\\]Brainstein(?:/|\\)"
    ),
}
WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

# These are trust anchors in the verifier, not values supplied by the release
# archive. Update them only after repeating the independent dependency and
# notice review. The inventory digest is filled from the reviewed canonical
# document; keeping it in executable verifier code makes self-consistent
# archive/manifest/SBOM/checksum forgery fail closed.
EXPECTED_DEPENDENCY_INVENTORY_SHA256 = "48ed1cdd3023bdb9781e7ffe9d987fb9425cc23e2dea053e2da5e8d461e588de"
EXPECTED_THIRD_PARTY_NOTICES_SHA256 = "b90c38b4cce60c06c0090be31ee721d3482640923d9ff6f3c711c047317746d0"
EXPECTED_EXTERNAL_RUNTIME_DEPENDENCIES_SHA256 = "c5962746f3a49570c810525c5a8557a3884e64e3b764476ff18cb65741853bc2"
INVENTORY_RESOLVED_AT = "2026-07-11T00:00:00Z"
INVENTORY_SOURCE_DATE_EPOCH = 1783728000
INVENTORY_PYTHON_REQUIRES = ">=3.11,<3.13"
INVENTORY_POLICY = (
    "One exact lowest-common version set with target-specific wheel hashes for "
    "glibc 2.17+/manylinux-compatible x86_64, macOS 11 x86_64/arm64, and "
    "Windows amd64. Unlisted interpreters, libc families, platforms, and "
    "architectures fail closed."
)
INVENTORY_SUBJECT_BINDING = (
    "Generated release SBOM binds the exact Git commit; this inventory binds "
    "all input manifests, normalized target resolver evidence, and third-party "
    "notices by SHA-256."
)

REVIEWED_LICENSE_EXPRESSIONS = {
    "brotli": "MIT", "certifi": "MPL-2.0", "cffi": "MIT-0",
    "charset-normalizer": "MIT", "colorama": "BSD-3-Clause",
    "contourpy": "BSD-3-Clause", "cryptography": "Apache-2.0 OR BSD-3-Clause",
    "cssselect2": "BSD-3-Clause", "cycler": "BSD-3-Clause", "fonttools": "MIT",
    "greenlet": "MIT AND Python-2.0", "idna": "BSD-3-Clause",
    "iniconfig": "MIT", "kiwisolver": "BSD-3-Clause",
    "matplotlib": "LicenseRef-Matplotlib-1.3",
    "numpy": "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0",
    "packaging": "Apache-2.0 OR BSD-2-Clause", "pillow": "MIT-CMU",
    "playwright": "Apache-2.0", "pluggy": "MIT", "pycparser": "BSD-3-Clause",
    "pydyf": "BSD-3-Clause", "pyee": "MIT", "pygments": "BSD-2-Clause",
    "pyparsing": "MIT",
    "pyphen": "GPL-2.0-or-later OR LGPL-2.1-or-later OR MPL-1.1",
    "pytest": "MIT", "python-dateutil": "Apache-2.0 OR BSD-3-Clause",
    "pyyaml": "MIT", "reportlab": "BSD-3-Clause", "requests": "Apache-2.0",
    "six": "MIT", "tinycss2": "BSD-3-Clause", "tinyhtml5": "MIT",
    "typing-extensions": "PSF-2.0", "urllib3": "MIT",
    "weasyprint": "BSD-3-Clause", "webencodings": "BSD-3-Clause",
    "zopfli": "Apache-2.0",
}

class ReleaseError(RuntimeError):
    """A release gate failed."""


def _load_local_module(root: Path, relative: str, module_name: str):
    path = root / relative
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ReleaseError(f"cannot load release verifier: {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=root, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReleaseError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def tracked_files(root: Path) -> list[str]:
    """Return repository-tracked regular paths in stable POSIX order."""
    paths = _git(root, "ls-files", "-z").decode("utf-8").split("\0")
    return sorted(path for path in paths if path)


def package_files(paths: list[str]) -> list[str]:
    """Select the explicitly public-safe product surface from tracked files."""
    return [
        path
        for path in paths
        if (path in PACKAGE_FILES or any(path.startswith(prefix) for prefix in PACKAGE_PREFIXES))
        and not any(path.startswith(prefix) for prefix in PACKAGE_EXCLUDED_PREFIXES)
    ]


def _assert_clean_head_release_subject(root: Path) -> list[str]:
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all").decode("utf-8")
    if status:
        raise ReleaseError("release packaging requires a clean index and worktree")
    head_paths = _git(root, "ls-tree", "-r", "--name-only", "HEAD").decode("utf-8").splitlines()
    selected = package_files(sorted(head_paths))
    for relative in selected:
        head_data = _git(root, "show", f"HEAD:{relative}")
        if not (root / relative).is_file() or (root / relative).read_bytes() != head_data:
            raise ReleaseError(f"release input differs from HEAD-tracked content: {relative}")
    return selected


def validate_portable_path(path: str) -> list[str]:
    errors: list[str] = []
    pure = PurePosixPath(path)
    if not path or path.startswith(("/", "\\")) or pure.is_absolute():
        errors.append("path is absolute or empty")
    if "\\" in path:
        errors.append("path contains a backslash")
    if any(part in {"", ".", ".."} for part in pure.parts):
        errors.append("path contains an empty, dot, or traversal segment")
    if any(ord(character) < 32 for character in path):
        errors.append("path contains a control character")
    for part in pure.parts:
        if re.search(r'[<>:"|?*]', part):
            errors.append(f"path segment is not Windows-portable: {part!r}")
        if part.endswith((" ", ".")):
            errors.append(f"path segment has a trailing space or dot: {part!r}")
        if part.split(".", 1)[0].casefold() in WINDOWS_RESERVED_NAMES:
            errors.append(f"path segment is reserved on Windows: {part!r}")
    return errors


def _read_text(path: Path) -> str | None:
    if path.suffix.casefold() not in TEXT_SUFFIXES and path.name not in {
        "LICENSE",
        "Dockerfile",
    }:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ReleaseError(f"text file is not valid UTF-8: {path}: {exc}") from exc


def _parse_yaml(text: str, path: str) -> object:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised in dependency-free installs
        raise ReleaseError("PyYAML is required for YAML and frontmatter audits") from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ReleaseError(f"invalid YAML in {path}: {exc}") from exc


def _frontmatter(text: str, path: str) -> dict[str, object]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ReleaseError(f"missing YAML frontmatter in {path}")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ReleaseError(f"unterminated YAML frontmatter in {path}") from exc
    value = _parse_yaml("\n".join(lines[1:end]), path)
    if not isinstance(value, dict):
        raise ReleaseError(f"frontmatter must be an object in {path}")
    return value


def _audit_manifest_consistency(root: Path, tracked: set[str]) -> list[str]:
    errors: list[str] = []
    plugin_path = ".claude-plugin/plugin.json"
    marketplace_path = ".claude-plugin/marketplace.json"
    if plugin_path not in tracked or marketplace_path not in tracked:
        return ["plugin and marketplace manifests must both be tracked"]
    plugin = json.loads((root / plugin_path).read_text(encoding="utf-8"))
    marketplace = json.loads((root / marketplace_path).read_text(encoding="utf-8"))
    entries = marketplace.get("plugins") if isinstance(marketplace, dict) else None
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        return ["marketplace manifest must contain exactly one plugin object"]
    entry = entries[0]
    for field in ("name", "version", "license", "repository"):
        if plugin.get(field) != entry.get(field):
            errors.append(f"plugin and marketplace disagree on {field!r}")
    for skill_root in plugin.get("skills", []):
        if not isinstance(skill_root, str):
            errors.append("plugin skills entries must be strings")
            continue
        normalized = skill_root.removeprefix("./").rstrip("/")
        if normalized not in {"ads", "skills"}:
            errors.append(f"unexpected plugin skill root: {skill_root!r}")
        if not (root / normalized).is_dir():
            errors.append(f"plugin skill root does not exist: {skill_root!r}")
    return errors


def audit_repository(root: Path) -> list[str]:
    """Audit tracked repository files without changing the repository."""
    errors: list[str] = []
    tracked = tracked_files(root)
    folded: dict[str, str] = {}
    skill_names: dict[str, str] = {}

    for relative in tracked:
        for issue in validate_portable_path(relative):
            errors.append(f"{relative}: {issue}")
        collision = folded.setdefault(relative.casefold(), relative)
        if collision != relative:
            errors.append(f"case-insensitive path collision: {collision!r} and {relative!r}")

        pure = PurePosixPath(relative)
        filename = pure.name.casefold()
        if filename in SENSITIVE_FILENAMES or filename.startswith(".env."):
            errors.append(f"sensitive filename must not be tracked: {relative}")
        if filename.startswith(SENSITIVE_FILENAME_PREFIXES):
            errors.append(f"sensitive filename must not be tracked: {relative}")
        if pure.suffix.casefold() in SENSITIVE_ARTIFACT_SUFFIXES:
            errors.append(f"sensitive artifact must not be tracked: {relative}")
        if pure.suffix.casefold() in {".key", ".p12", ".pfx", ".pem"}:
            errors.append(f"credential-like file must not be tracked: {relative}")

        path = root / relative
        if path.is_symlink():
            errors.append(f"tracked symlink is not release-safe: {relative}")
            continue
        if not path.is_file():
            errors.append(f"tracked path is not a regular file: {relative}")
            continue

        raw = path.read_bytes()
        scan_text = raw.decode("utf-8", errors="ignore")
        text = _read_text(path)
        if text is not None and relative.endswith(".json"):
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON in {relative}: {exc}")
        if text is not None and relative.endswith((".yml", ".yaml", ".cff")):
            try:
                _parse_yaml(text, relative)
            except ReleaseError as exc:
                errors.append(str(exc))

        if text is not None and (relative == "ads/SKILL.md" or (
            relative.startswith("skills/") and relative.endswith("/SKILL.md")
        )):
            try:
                frontmatter = _frontmatter(text, relative)
            except ReleaseError as exc:
                errors.append(str(exc))
            else:
                expected_name = PurePosixPath(relative).parent.name
                name = frontmatter.get("name")
                description = frontmatter.get("description")
                if name != expected_name:
                    errors.append(
                        f"{relative}: frontmatter name {name!r} must equal {expected_name!r}"
                    )
                if not isinstance(description, str) or not description.strip():
                    errors.append(f"{relative}: frontmatter description must be a non-empty string")
                if isinstance(name, str):
                    previous = skill_names.setdefault(name, relative)
                    if previous != relative:
                        errors.append(f"duplicate skill name {name!r}: {previous} and {relative}")

        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(scan_text):
                errors.append(f"{relative}: possible {label}")
        for label, pattern in PRIVATE_PATH_PATTERNS.items():
            if pattern.search(scan_text):
                errors.append(f"{relative}: contains {label}")

    errors.extend(_audit_manifest_consistency(root, set(tracked)))
    selected = package_files(tracked)
    if not selected:
        errors.append("public-safe package selection is empty")
    for required in ("LICENSE", "README.md", ".claude-plugin/plugin.json", "ads/SKILL.md"):
        if required not in selected:
            errors.append(f"required release file is missing or untracked: {required}")
    return sorted(set(errors))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_sha256(value: object) -> str:
    return _sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _canonical_package_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def _packaging_types():
    try:
        from packaging.markers import Marker
        from packaging.requirements import Requirement
        from packaging.version import Version
    except ImportError as exc:  # pragma: no cover - release environments install pytest/packaging
        raise ReleaseError("packaging is required to validate the dependency inventory") from exc
    return Marker, Requirement, Version


def _wheel_is_compatible(filename: str, target: dict[str, object], name: str, version: str) -> None:
    """Validate distribution identity and the complete wheel tag set for one target."""
    try:
        from packaging.utils import canonicalize_name, parse_wheel_filename
    except ImportError as exc:  # pragma: no cover
        raise ReleaseError("packaging wheel utilities are required") from exc
    try:
        distribution, wheel_version, _build, tags = parse_wheel_filename(filename)
    except Exception as exc:
        raise ReleaseError(f"invalid wheel filename for {target['id']}/{name}: {filename}") from exc
    if canonicalize_name(distribution) != name or str(wheel_version) != version:
        raise ReleaseError(f"wheel identity mismatch for {target['id']}/{name}")

    # A universal wheel must explicitly include py3-none-any. Some legacy
    # universal wheels advertise py2.py3, which expands to include that tag.
    if all(tag.abi == "none" and tag.platform == "any" for tag in tags):
        if not any(tag.interpreter == "py3" for tag in tags):
            raise ReleaseError(f"pure wheel is not py3-compatible: {target['id']}/{name}")
        return
    if any(tag.platform == "any" for tag in tags):
        raise ReleaseError(f"wheel mixes pure and platform tags: {target['id']}/{name}")

    target_minor = int(str(target["python_version"]).split(".")[1])
    for tag in tags:
        interpreter = tag.interpreter
        if tag.abi == "none":
            if interpreter != "py3":
                raise ReleaseError(f"platform wheel is not py3-compatible: {target['id']}/{name}")
        elif tag.abi == "abi3":
            match = re.fullmatch(r"cp3(\d+)", interpreter)
            if not match or int(match.group(1)) > target_minor:
                raise ReleaseError(f"wheel ABI is incompatible with {target['id']}/{name}")
        elif interpreter != target["abi"] or tag.abi != target["abi"]:
            raise ReleaseError(f"wheel ABI is incompatible with {target['id']}/{name}")

    platforms = {tag.platform for tag in tags}
    os_name, arch = target["os"], target["arch"]
    if os_name == "linux":
        compatible_baseline = False
        for platform_tag in platforms:
            if "musllinux" in platform_tag or not platform_tag.endswith("_x86_64"):
                raise ReleaseError(f"wheel platform is incompatible with {target['id']}/{name}")
            if platform_tag == "manylinux1_x86_64":
                compatible_baseline = True
            elif platform_tag == "manylinux2010_x86_64":
                compatible_baseline = True
            elif platform_tag == "manylinux2014_x86_64":
                compatible_baseline = True
            else:
                match = re.fullmatch(r"manylinux_(\d+)_(\d+)_x86_64", platform_tag)
                if not match:
                    raise ReleaseError(f"wheel platform is incompatible with {target['id']}/{name}")
                if (int(match.group(1)), int(match.group(2))) <= (2, 17):
                    compatible_baseline = True
        if not compatible_baseline:
            raise ReleaseError(f"wheel requires a newer glibc baseline: {target['id']}/{name}")
    elif os_name == "macos":
        expected_arches = {"universal2", "arm64" if arch == "arm64" else "x86_64"}
        for platform_tag in platforms:
            match = re.fullmatch(r"macosx_(\d+)_(\d+)_(arm64|x86_64|universal2)", platform_tag)
            if not match or match.group(3) not in expected_arches:
                raise ReleaseError(f"wheel platform is incompatible with {target['id']}/{name}")
            if (int(match.group(1)), int(match.group(2))) > (11, 0):
                raise ReleaseError(f"wheel requires a newer macOS baseline: {target['id']}/{name}")
    elif os_name == "windows":
        if platforms != {"win_amd64"}:
            raise ReleaseError(f"wheel platform is incompatible with {target['id']}/{name}")
    else:  # pragma: no cover - target matrix validation rejects this first
        raise ReleaseError(f"unknown wheel target OS: {os_name}")


def _load_target_evidence(root: Path, target_id: str) -> tuple[dict[str, object], str]:
    path = root / "control-plane" / "dependency-evidence" / f"{target_id}.json"
    try:
        data = path.read_bytes()
        evidence = json.loads(data)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot load target resolver evidence for {target_id}: {exc}") from exc
    expected_fields = {
        "schema_version", "evidence_id", "resolved_at", "source_date_epoch",
        "source_report_sha256", "source_pip_version", "source_environment", "normalization_notes",
        "evidence_class", "environment", "resolver", "platform_policy", "components",
    }
    if not isinstance(evidence, dict) or set(evidence) != expected_fields:
        raise ReleaseError(f"target resolver evidence fields mismatch: {target_id}")
    if (
        evidence.get("schema_version") != "1.0.0"
        or evidence.get("evidence_id") != target_id
        or evidence.get("resolved_at") != INVENTORY_RESOLVED_AT
        or evidence.get("source_date_epoch") != INVENTORY_SOURCE_DATE_EPOCH
        or evidence.get("evidence_class") != "cross-target-pip-resolution-requiring-native-ci-confirmation"
        or evidence.get("resolver") != "pip / PyPI"
        or evidence.get("platform_policy") != "Exact lowest-common lock with target-selected PyPI wheels"
        or not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("source_report_sha256", "")))
        or not re.fullmatch(r"\d+(?:\.\d+){1,3}", str(evidence.get("source_pip_version", "")))
        or not isinstance(evidence.get("source_environment"), dict)
        or not isinstance(evidence.get("normalization_notes"), list)
    ):
        raise ReleaseError(f"target resolver evidence header mismatch: {target_id}")
    return evidence, _sha256(data)


def _declared_requirements(root: Path) -> list[dict[str, str]]:
    _, Requirement, _ = _packaging_types()
    declared: list[dict[str, str]] = []
    for source, profile in (("requirements.txt", "runtime"), ("requirements-dev.txt", "development")):
        for raw in (root / source).read_text(encoding="utf-8").splitlines():
            value = raw.split("#", 1)[0].strip()
            if not value or value.startswith("-"):
                continue
            try:
                requirement = Requirement(value)
            except Exception as exc:
                raise ReleaseError(f"invalid direct requirement in {source}: {value}") from exc
            declared.append({"name": _canonical_package_name(requirement.name), "requirement": value, "source": source, "profile": profile})
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    for value in project.get("dependencies", []):
        requirement = Requirement(value)
        declared.append({"name": _canonical_package_name(requirement.name), "requirement": value, "source": "pyproject.toml#project.dependencies", "profile": "runtime"})
    for group, values in sorted(project.get("optional-dependencies", {}).items()):
        for value in values:
            requirement = Requirement(value)
            declared.append({"name": _canonical_package_name(requirement.name), "requirement": value, "source": f"pyproject.toml#project.optional-dependencies.{group}", "profile": "runtime"})
    return sorted(declared, key=lambda item: (item["profile"], item["name"], item["source"]))


def _parse_hash_lock(path: Path) -> dict[str, dict[str, object]]:
    logical = path.read_text(encoding="utf-8").replace("\\\n", " ")
    entries: dict[str, dict[str, object]] = {}
    _, Requirement, Version = _packaging_types()
    for raw in logical.splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})(?:\s|$)", value)
        requirement_text = re.sub(r"\s*--hash=sha256:[0-9a-f]{64}(?:\s|$)", " ", value).strip()
        if "--hash" in requirement_text:
            raise ReleaseError(f"invalid lock hash in {path.name}")
        requirement = Requirement(requirement_text)
        name = _canonical_package_name(requirement.name)
        specs = list(requirement.specifier)
        if len(specs) != 1 or specs[0].operator != "==" or specs[0].version.endswith(".*"):
            raise ReleaseError(f"{path.name} must use exact == pins: {requirement}")
        Version(specs[0].version)
        if name in entries or not hashes or len(hashes) != len(set(hashes)):
            raise ReleaseError(f"duplicate component or hash in {path.name}: {name}")
        entries[name] = {"version": specs[0].version, "hashes": sorted(hashes), "marker": str(requirement.marker) if requirement.marker else None}
    if not entries:
        raise ReleaseError(f"{path.name} is empty")
    return entries


def _load_dependency_inventory(root: Path) -> dict[str, object]:
    path = root / "control-plane/manifests/dependency-inventory.json"
    try:
        inventory = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot load dependency inventory: {exc}") from exc
    required = {"schema_version", "inventory_id", "resolved_at", "resolution", "manifests", "direct_requirements", "targets", "component_catalog", "dependency_edges", "bundled_notices"}
    if not isinstance(inventory, dict) or set(inventory) != required:
        raise ReleaseError("dependency inventory fields are incomplete or unknown")
    if inventory.get("schema_version") != "1.0.0" or inventory.get("inventory_id") != "claude-ads-python-dependencies":
        raise ReleaseError("dependency inventory identity/version mismatch")
    resolution = inventory.get("resolution")
    if inventory.get("resolved_at") != INVENTORY_RESOLVED_AT:
        raise ReleaseError("dependency inventory resolution timestamp mismatch")
    try:
        parsed_resolved_at = datetime.fromisoformat(INVENTORY_RESOLVED_AT.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - constant is reviewed
        raise ReleaseError("invalid verifier resolution timestamp") from exc
    if int(parsed_resolved_at.timestamp()) != INVENTORY_SOURCE_DATE_EPOCH:
        raise ReleaseError("dependency inventory source epoch policy mismatch")
    resolution = inventory.get("resolution")
    expected_resolution_keys = {
        "index", "managed_lock_python_range", "supported_python_versions", "implementation",
        "source_date_epoch", "policy", "reviewed_metadata_sha256",
        "third_party_notices_sha256", "target_evidence_class", "subject_binding",
    }
    if not isinstance(resolution, dict) or set(resolution) != expected_resolution_keys:
        raise ReleaseError("dependency inventory resolution metadata is incomplete")
    if (
        resolution.get("index") != "https://pypi.org/simple"
        or resolution.get("managed_lock_python_range") != INVENTORY_PYTHON_REQUIRES
        or resolution.get("supported_python_versions") != ["3.11", "3.12"]
        or resolution.get("implementation") != "CPython"
        or resolution.get("source_date_epoch") != INVENTORY_SOURCE_DATE_EPOCH
        or resolution.get("policy") != INVENTORY_POLICY
        or resolution.get("subject_binding") != INVENTORY_SUBJECT_BINDING
        or resolution.get("target_evidence_class") != "cross-target-pip-resolution-requiring-native-ci-confirmation"
    ):
        raise ReleaseError("dependency inventory resolution target policy mismatch")
    notices_path = root / "THIRD_PARTY_NOTICES.md"
    if (
        not notices_path.is_file()
        or _sha256(notices_path.read_bytes()) != EXPECTED_THIRD_PARTY_NOTICES_SHA256
        or resolution.get("third_party_notices_sha256") != EXPECTED_THIRD_PARTY_NOTICES_SHA256
        or not re.fullmatch(r"[0-9a-f]{64}", str(resolution.get("reviewed_metadata_sha256", "")))
    ):
        raise ReleaseError("dependency inventory resolution evidence is incomplete")
    manifests = inventory["manifests"]
    expected_manifest_paths = {"requirements.txt", "requirements-dev.txt", "requirements.lock", "requirements-dev.lock", "pyproject.toml"}
    if not isinstance(manifests, list) or {item.get("path") for item in manifests if isinstance(item, dict)} != expected_manifest_paths or len(manifests) != len(expected_manifest_paths):
        raise ReleaseError("dependency inventory manifest coverage is incomplete or duplicated")
    for item in manifests:
        manifest_path = root / item["path"]
        if not manifest_path.is_file() or item.get("sha256") != _sha256(manifest_path.read_bytes()):
            raise ReleaseError(f"dependency inventory manifest hash mismatch: {item.get('path')}")

    catalog: dict[tuple[str, str], dict[str, object]] = {}
    names_to_version: dict[str, str] = {}
    for component in inventory["component_catalog"]:
        if not isinstance(component, dict):
            raise ReleaseError("dependency catalog entries must be objects")
        name, component_version = component.get("name"), component.get("version")
        if not isinstance(name, str) or name != _canonical_package_name(name) or not isinstance(component_version, str) or not component_version.strip():
            raise ReleaseError("dependency catalog contains an invalid name/version")
        key = (name, component_version)
        if key in catalog or (name in names_to_version and names_to_version[name] != component_version):
            raise ReleaseError(f"duplicate or multi-version dependency component: {name}")
        names_to_version[name] = component_version
        license_expression = component.get("license_expression")
        if license_expression != REVIEWED_LICENSE_EXPRESSIONS.get(name):
            raise ReleaseError(f"dependency component lacks a reviewed license: {name}")
        if component.get("purl") != f"pkg:pypi/{name}@{component_version}":
            raise ReleaseError(f"dependency component purl mismatch: {name}")
        provenance = component.get("license_provenance")
        if not isinstance(provenance, dict) or set(provenance) != {"kind", "metadata_url", "evidence_sha256"} or provenance.get("kind") != "publisher-metadata-review" or provenance.get("metadata_url") != f"https://pypi.org/pypi/{name}/{component_version}/json" or not re.fullmatch(r"[0-9a-f]{64}", str(provenance.get("evidence_sha256", ""))):
            raise ReleaseError(f"dependency component license provenance mismatch: {name}")
        catalog[key] = component
    if set(REVIEWED_LICENSE_EXPRESSIONS) != set(names_to_version):
        raise ReleaseError("reviewed license component coverage mismatch")
    reviewed_metadata = {name: catalog[(name, version)]["license_provenance"]["evidence_sha256"] for name, version in names_to_version.items()}
    if resolution["reviewed_metadata_sha256"] != _canonical_json_sha256(reviewed_metadata):
        raise ReleaseError("reviewed publisher metadata binding mismatch")

    targets = inventory["targets"]
    if not isinstance(targets, list) or len(targets) != 16:
        raise ReleaseError("dependency inventory must contain the 16 verified targets")
    expected_targets = {
        f"runtime-{platform}-{abi}": ("runtime", python, os_name, arch, abi, 33)
        for platform, os_name, arch in (
            ("linux", "linux", "x86_64"), ("macos-arm", "macos", "arm64"),
            ("macos-x86", "macos", "x86_64"), ("windows", "windows", "amd64"),
        )
        for abi, python in (("cp311", "3.11"), ("cp312", "3.12"))
    }
    expected_targets.update({
        f"development-{platform}-{abi}": ("development", python, os_name, arch, abi, 10 if os_name == "windows" else 9)
        for platform, os_name, arch in (
            ("linux", "linux", "x86_64"), ("macos-arm", "macos", "arm64"),
            ("macos-x86", "macos", "x86_64"), ("windows", "windows", "amd64"),
        )
        for abi, python in (("cp311", "3.11"), ("cp312", "3.12"))
    })
    target_ids: set[str] = set()
    occurrence: dict[tuple[str, str], set[str]] = {key: set() for key in catalog}
    target_components: dict[str, dict[str, dict[str, object]]] = {}
    target_evidence: dict[str, dict[str, object]] = {}
    for target in targets:
        target_id = target.get("id") if isinstance(target, dict) else None
        if not isinstance(target_id, str) or target_id in target_ids:
            raise ReleaseError("dependency target IDs must be unique strings")
        target_ids.add(target_id)
        expected = expected_targets.get(target_id)
        observed = (target.get("profile"), target.get("python_version"), target.get("os"), target.get("arch"), target.get("abi"), len(target.get("components", [])))
        if expected is None or observed != expected:
            raise ReleaseError(f"dependency target matrix mismatch: {target_id}")
        if target.get("implementation") != "CPython" or target.get("resolver") != "pip / PyPI" or target.get("platform_policy") != "Exact lowest-common lock with target-selected PyPI wheels" or not re.fullmatch(r"[0-9a-f]{64}", str(target.get("resolution_evidence_sha256", ""))):
            raise ReleaseError(f"dependency target provenance mismatch: {target_id}")
        evidence, evidence_sha256 = _load_target_evidence(root, target_id)
        expected_environment = {
            key: target[key]
            for key in ("profile", "python_version", "implementation", "os", "arch", "abi")
        }
        if evidence_sha256 != target["resolution_evidence_sha256"] or evidence["environment"] != expected_environment:
            raise ReleaseError(f"dependency target resolver evidence binding mismatch: {target_id}")
        target_evidence[target_id] = evidence
        components: dict[str, dict[str, object]] = {}
        for component in target.get("components", []):
            name, component_version = component.get("name"), component.get("version")
            if name in components or (name, component_version) not in catalog:
                raise ReleaseError(f"duplicate or unknown target component in {target_id}: {name}")
            artifact = component.get("artifact")
            if not isinstance(artifact, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))) or not str(artifact.get("url", "")).startswith("https://files.pythonhosted.org/"):
                raise ReleaseError(f"target component lacks exact artifact evidence: {target_id}/{name}")
            if artifact.get("filename") != str(artifact.get("url")).rsplit("/", 1)[-1]:
                raise ReleaseError(f"target component artifact filename mismatch: {target_id}/{name}")
            parsed_url = urlsplit(str(artifact.get("url")))
            if parsed_url.scheme != "https" or parsed_url.netloc != "files.pythonhosted.org" or parsed_url.query or parsed_url.fragment or unquote(PurePosixPath(parsed_url.path).name) != artifact.get("filename"):
                raise ReleaseError(f"target component artifact URL binding mismatch: {target_id}/{name}")
            _wheel_is_compatible(artifact["filename"], target, name, component_version)
            if component.get("purl") != f"pkg:pypi/{name}@{component_version}":
                raise ReleaseError(f"target component purl mismatch: {target_id}/{name}")
            components[name] = component
            occurrence[(name, component_version)].add(target_id)
        target_components[target_id] = components
    if target_ids != set(expected_targets):
        raise ReleaseError("dependency target matrix IDs are incomplete")
    for key, component in catalog.items():
        if sorted(occurrence[key]) != component.get("target_occurrences"):
            raise ReleaseError(f"dependency target occurrence mismatch: {key[0]}")

    declared = _declared_requirements(root)
    _, Requirement, Version = _packaging_types()
    inventory_declared = []
    for item in inventory["direct_requirements"]:
        requirement = Requirement(item["requirement"])
        inventory_declared.append({"name": _canonical_package_name(requirement.name), "requirement": str(requirement), "source": item["source"], "profile": item["profile"]})
    normalized_declared = [{**item, "requirement": str(Requirement(item["requirement"]))} for item in declared]
    if sorted(inventory_declared, key=lambda item: (item["profile"], item["name"], item["source"])) != sorted(normalized_declared, key=lambda item: (item["profile"], item["name"], item["source"])):
        raise ReleaseError("dependency inventory direct requirement coverage mismatch")
    declared_names_by_profile = {
        profile: {item["name"] for item in normalized_declared if item["profile"] == profile}
        for profile in ("runtime", "development")
    }
    for target in targets:
        profile = target["profile"]
        components = target_components[target["id"]]
        observed_direct = {name for name, component in components.items() if component.get("direct") is True}
        if observed_direct != declared_names_by_profile[profile] or any(
            not isinstance(component.get("direct"), bool) for component in components.values()
        ):
            raise ReleaseError(f"direct component flags mismatch declared requirements: {target['id']}")
        for item in normalized_declared:
            if item["profile"] != profile:
                continue
            component = components.get(item["name"])
            if not component or not component.get("direct") or Version(component["version"]) not in Requirement(item["requirement"]).specifier:
                raise ReleaseError(f"direct requirement is missing or constraint-mismatched in {target['id']}: {item['name']}")
    for target in targets:
        if target_evidence[target["id"]]["components"] != target["components"]:
            raise ReleaseError(f"dependency target component evidence mismatch: {target['id']}")

    runtime_lock = _parse_hash_lock(root / "requirements.lock")
    development_lock = _parse_hash_lock(root / "requirements-dev.lock")
    for profile, lock in (("runtime", runtime_lock), ("development", development_lock)):
        relevant = [target for target in targets if target["profile"] == profile]
        expected_names = {name for target in relevant for name in target_components[target["id"]]}
        if set(lock) != expected_names:
            raise ReleaseError(f"{profile} lock component coverage mismatch")
        for name, locked in lock.items():
            versions = {target_components[target["id"]][name]["version"] for target in relevant if name in target_components[target["id"]]}
            hashes = {target_components[target["id"]][name]["artifact"]["sha256"] for target in relevant if name in target_components[target["id"]]}
            if versions != {locked["version"]} or hashes != set(locked["hashes"]):
                raise ReleaseError(f"{profile} lock target artifact mismatch: {name}")
            if name == "colorama" and locked["marker"] != 'sys_platform == "win32"':
                raise ReleaseError("development lock must retain the win32-only colorama marker")

    catalog_names = set(names_to_version)
    edges_seen: set[tuple[str, str, str]] = set()
    edge_fields = {"profile", "from", "to", "requirement", "specifier", "marker", "extras", "publisher_metadata_sha256"}
    _, Requirement, Version = _packaging_types()
    for edge in inventory["dependency_edges"]:
        if not isinstance(edge, dict) or set(edge) != edge_fields:
            raise ReleaseError("dependency graph edge fields mismatch")
        if edge.get("profile") not in {"runtime", "development"}:
            raise ReleaseError("dependency graph edge profile mismatch")
        key = (edge["profile"], edge.get("from"), edge.get("requirement"))
        if key in edges_seen or edge.get("from") not in catalog_names or edge.get("to") not in catalog_names:
            raise ReleaseError("dependency graph contains a duplicate or dangling edge")
        edges_seen.add(key)
        if not isinstance(edge.get("requirement"), str) or not edge["requirement"]:
            raise ReleaseError("dependency graph requirement must be a nonempty string")
        try:
            requirement = Requirement(edge["requirement"])
        except Exception as exc:
            raise ReleaseError("dependency graph contains an invalid publisher requirement") from exc
        if (
            _canonical_package_name(requirement.name) != edge["to"]
            or str(requirement.specifier) != edge["specifier"]
            or (str(requirement.marker) if requirement.marker else None) != edge["marker"]
            or sorted(requirement.extras) != edge["extras"]
            or not isinstance(edge["extras"], list)
            or any(not isinstance(extra, str) or not re.fullmatch(r"[a-z0-9]+(?:[-_.][a-z0-9]+)*", extra) for extra in edge["extras"])
            or edge["publisher_metadata_sha256"] != catalog[(edge["from"], names_to_version[edge["from"]])]["license_provenance"]["evidence_sha256"]
        ):
            raise ReleaseError("dependency graph publisher metadata mismatch")
    for profile in ("runtime", "development"):
        if not any(edge["profile"] == profile for edge in inventory["dependency_edges"]):
            raise ReleaseError(f"dependency graph is empty for {profile}")
    try:
        from packaging.markers import Marker, default_environment
    except ImportError as exc:  # pragma: no cover
        raise ReleaseError("packaging markers are required for dependency graph validation") from exc
    for target in targets:
        profile = target["profile"]
        components = target_components[target["id"]]
        environment = default_environment()
        environment.update({
            "implementation_name": "cpython", "platform_python_implementation": "CPython",
            "python_version": target["python_version"], "python_full_version": target["python_version"] + ".0",
            "sys_platform": {"linux": "linux", "macos": "darwin", "windows": "win32"}[target["os"]],
            "platform_system": {"linux": "Linux", "macos": "Darwin", "windows": "Windows"}[target["os"]],
            "platform_machine": target["arch"],
        })
        adjacency: dict[str, list[dict[str, object]]] = {}
        for edge in inventory["dependency_edges"]:
            if edge["profile"] == profile:
                adjacency.setdefault(edge["from"], []).append(edge)
        reachable = set(declared_names_by_profile[profile])
        active_extras: dict[str, set[str]] = {name: set() for name in reachable}
        pending = list(sorted(reachable))
        while pending:
            parent = pending.pop(0)
            contexts = active_extras[parent] or {""}
            for edge in adjacency.get(parent, []):
                marker = edge["marker"]
                if marker and not any(Marker(marker).evaluate({**environment, "extra": extra}) for extra in contexts):
                    continue
                dependency = edge["to"]
                if dependency not in components:
                    raise ReleaseError(f"dependency edge target absent from closure: {target['id']}/{dependency}")
                if Version(components[dependency]["version"]) not in Requirement(edge["requirement"]).specifier:
                    raise ReleaseError(f"dependency edge constraint mismatch: {target['id']}/{parent}->{dependency}")
                new_extras = set(edge["extras"]) - active_extras.get(dependency, set())
                if dependency not in reachable or new_extras:
                    reachable.add(dependency)
                    active_extras.setdefault(dependency, set()).update(new_extras)
                    pending.append(dependency)
        if reachable != set(components):
            missing = ", ".join(sorted(set(components) - reachable))
            raise ReleaseError(f"dependency graph has unreachable target components in {target['id']}: {missing}")
    expected_notice_ids = {f"{name}-selected-wheel-documents" for name in names_to_version}
    notice_ids = {notice.get("id") for notice in inventory["bundled_notices"] if isinstance(notice, dict)}
    if notice_ids != expected_notice_ids or len(notice_ids) != len(inventory["bundled_notices"]):
        raise ReleaseError("reviewed bundled notice set mismatch")
    artifacts_by_component = {
        name: {
            component["artifact"]["sha256"]
            for target in targets
            for component in target["components"]
            if component["name"] == name
        }
        for name in names_to_version
    }
    for notice in inventory["bundled_notices"]:
        if not isinstance(notice, dict) or set(notice) != {"id", "component", "summary", "documents", "documentless_artifact_sha256s"}:
            raise ReleaseError("bundled notice fields mismatch")
        expected_component = notice["id"].removesuffix("-selected-wheel-documents")
        expected_summary = f"Preserve every license/notice-like file embedded in each selected {expected_component} wheel; artifacts listed as documentless contain no matching embedded path."
        if notice["component"] != expected_component or notice["summary"] != expected_summary:
            raise ReleaseError(f"reviewed bundled notice content mismatch: {notice['id']}")
        documents = notice["documents"]
        documentless = notice["documentless_artifact_sha256s"]
        if not isinstance(documents, list) or not isinstance(documentless, list) or documentless != sorted(set(documentless)) or not set(documentless).issubset(artifacts_by_component[expected_component]):
            raise ReleaseError(f"bundled notice documentless evidence mismatch: {notice['id']}")
        covered_artifacts: set[str] = set()
        document_keys: set[tuple[str, str]] = set()
        for document in documents:
            if not isinstance(document, dict) or set(document) != {"path", "sha256", "text", "artifact_sha256s"}:
                raise ReleaseError(f"bundled notice document fields mismatch: {notice['id']}")
            path_value, text_value = document["path"], document["text"]
            if (
                not isinstance(path_value, str)
                or validate_portable_path(path_value)
                or not isinstance(text_value, str)
                or _sha256(text_value.encode("utf-8")) != document["sha256"]
                or not isinstance(document["artifact_sha256s"], list)
                or document["artifact_sha256s"] != sorted(set(document["artifact_sha256s"]))
                or not set(document["artifact_sha256s"]).issubset(artifacts_by_component[expected_component])
            ):
                raise ReleaseError(f"bundled notice document evidence mismatch: {notice['id']}")
            key = (path_value, document["sha256"])
            if key in document_keys:
                raise ReleaseError(f"duplicate bundled notice document: {notice['id']}")
            document_keys.add(key)
            covered_artifacts.update(document["artifact_sha256s"])
        if covered_artifacts & set(documentless) or covered_artifacts | set(documentless) != artifacts_by_component[expected_component]:
            raise ReleaseError(f"bundled notice selected-wheel coverage mismatch: {notice['id']}")
    for component in catalog.values():
        expected_ids = [f"{component['name']}-selected-wheel-documents"]
        if component.get("bundled_notice_ids") != expected_ids:
            raise ReleaseError(f"component bundled notice assignment mismatch: {component['name']}")
    if _sha256(path.read_bytes()) != EXPECTED_DEPENDENCY_INVENTORY_SHA256:
        raise ReleaseError("dependency inventory differs from the exact independently reviewed document")
    return inventory


def _load_external_runtime_dependencies(root: Path) -> dict[str, object]:
    path = root / "control-plane/manifests/external-runtime-dependencies.json"
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot load external runtime dependency manifest: {exc}") from exc
    if _sha256(raw) != EXPECTED_EXTERNAL_RUNTIME_DEPENDENCIES_SHA256:
        raise ReleaseError("external runtime dependency manifest differs from the reviewed document")
    if not isinstance(document, dict) or set(document) != {"schema_version", "subject", "scope", "sources", "dependencies"}:
        raise ReleaseError("external runtime dependency manifest fields mismatch")
    if document["schema_version"] != "1.0.0" or document["subject"] != "claude-ads-external-runtime-dependencies":
        raise ReleaseError("external runtime dependency manifest identity mismatch")
    sources = document["sources"]
    dependencies = document["dependencies"]
    expected_source_ids = {"playwright-python-intro", "playwright-browsers", "playwright-ci", "weasyprint-69-install", "cyclonedx-1.5-json"}
    if not isinstance(sources, list) or {item.get("id") for item in sources if isinstance(item, dict)} != expected_source_ids or len(sources) != len(expected_source_ids):
        raise ReleaseError("external runtime dependency source coverage mismatch")
    for source in sources:
        if set(source) != {"id", "url", "publisher", "accessed_at"} or not str(source["url"]).startswith("https://") or source["accessed_at"] != "2026-07-11" or not source["publisher"]:
            raise ReleaseError("external runtime dependency source metadata mismatch")
    if not isinstance(dependencies, list) or {item.get("id") for item in dependencies if isinstance(item, dict)} != {"playwright-browser-payload", "weasyprint-native-libraries"} or len(dependencies) != 2:
        raise ReleaseError("external runtime dependency coverage mismatch")
    for dependency in dependencies:
        if dependency.get("included_in_python_lock") is not False or dependency.get("included_in_python_sbom") is not False or dependency.get("cross_platform_feature_attestation") != "not-claimed":
            raise ReleaseError("external runtime dependency boundary mismatch")
        source_ids = dependency.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or not set(source_ids).issubset(expected_source_ids):
            raise ReleaseError("external runtime dependency source binding mismatch")
    return document


def _build_sbom_from_inventory(
    inventory: dict[str, object],
    product_name: str,
    version: str,
    commit: str,
    inventory_sha256: str,
) -> dict[str, object]:
    catalog = inventory["component_catalog"]
    target_artifacts: dict[tuple[str, str], list[dict[str, str]]] = {}
    direct_names: set[str] = set()
    runtime_targets = [target for target in inventory["targets"] if target["profile"] == "runtime"]
    for target in runtime_targets:
        for component in target["components"]:
            key = (component["name"], component["version"])
            artifact = {"target": target["id"], **component["artifact"]}
            if artifact not in target_artifacts.setdefault(key, []):
                target_artifacts[key].append(artifact)
            if component["direct"]:
                direct_names.add(component["name"])
    components = []
    for item in catalog:
        key = (item["name"], item["version"])
        if key not in target_artifacts:
            continue
        artifacts = sorted(target_artifacts[key], key=lambda value: (value["target"], value["filename"]))
        hashes = sorted({artifact["sha256"] for artifact in artifacts})
        artifact_groups: dict[tuple[str, str, str], list[str]] = {}
        for artifact in artifacts:
            artifact_groups.setdefault((artifact["url"], artifact["sha256"], artifact["filename"]), []).append(artifact["target"])
        external_references = [
            {
                "type": "distribution", "url": url,
                "hashes": [{"alg": "SHA-256", "content": digest}],
                "comment": "targets=" + ",".join(sorted(targets)),
            }
            for (url, digest, _filename), targets in sorted(artifact_groups.items())
        ]
        components.append({
            "type": "library", "bom-ref": item["purl"], "name": item["name"], "version": item["version"], "purl": item["purl"],
            "scope": "required",
            "licenses": [{"expression": item["license_expression"]}],
            "hashes": [{"alg": "SHA-256", "content": digest} for digest in hashes],
            "externalReferences": external_references,
            "properties": [
                {"name": "claude-ads:direct", "value": str(item["name"] in direct_names).lower()},
                {"name": "claude-ads:target-occurrences", "value": ",".join(item["target_occurrences"])},
                {"name": "claude-ads:license-provenance", "value": item["license_provenance"]["metadata_url"]},
                {"name": "claude-ads:bundled-notices", "value": ",".join(item["bundled_notice_ids"]) or "none"},
            ],
        })
    components.sort(key=lambda item: item["name"])
    component_purls = {item["name"]: item["purl"] for item in catalog if (item["name"], item["version"]) in target_artifacts}
    dependencies = []
    app_ref = f"pkg:generic/{product_name}@{version}"
    dependencies.append({"ref": app_ref, "dependsOn": sorted(component_purls[name] for name in direct_names)})
    for name in sorted(component_purls):
        targets = sorted({edge["to"] for edge in inventory["dependency_edges"] if edge["profile"] == "runtime" and edge["from"] == name})
        dependencies.append({"ref": component_purls[name], "dependsOn": [component_purls[target] for target in targets]})
    identity = json.dumps({"commit": commit, "components": components, "dependencies": dependencies}, sort_keys=True, separators=(",", ":"))
    serial = uuid.uuid5(uuid.NAMESPACE_URL, f"claude-ads:{version}:{identity}")
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{serial}", "version": 1,
        "metadata": {"component": {"type": "application", "bom-ref": app_ref, "name": product_name, "version": version, "purl": app_ref, "licenses": [{"expression": "MIT"}]}, "properties": [{"name": "claude-ads:source-commit", "value": commit}, {"name": "claude-ads:dependency-inventory-sha256", "value": inventory_sha256}]},
        "components": components, "dependencies": dependencies,
    }


def build_sbom(root: Path, product_name: str, version: str) -> dict[str, object]:
    inventory = _load_dependency_inventory(root)
    commit = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    inventory_sha256 = _sha256((root / "control-plane/manifests/dependency-inventory.json").read_bytes())
    return _build_sbom_from_inventory(inventory, product_name, version, commit, inventory_sha256)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _product(root: Path) -> tuple[str, str]:
    manifest = json.loads((root / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    name, version = manifest.get("name"), manifest.get("version")
    if not isinstance(name, str) or not isinstance(version, str) or not name or not version:
        raise ReleaseError("plugin manifest requires string name and version")
    return name, version


def build_release(root: Path, output_dir: Path) -> dict[str, Path]:
    selected = _assert_clean_head_release_subject(root)
    errors = audit_repository(root)
    if errors:
        raise ReleaseError("repository audit failed:\n- " + "\n- ".join(errors))
    _load_external_runtime_dependencies(root)

    name, version = _product(root)
    archive_root = f"{name}-{version}"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{archive_root}.zip"
    file_records: list[dict[str, object]] = []

    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for relative in selected:
            path = root / relative
            if path.is_symlink() or not path.is_file():
                raise ReleaseError(f"release input is not a regular file: {relative}")
            data = path.read_bytes()
            executable = bool(path.stat().st_mode & stat.S_IXUSR)
            mode = 0o755 if executable else 0o644
            info = zipfile.ZipInfo(f"{archive_root}/{relative}", ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            file_records.append(
                {
                    "path": relative,
                    "sha256": _sha256(data),
                    "size": len(data),
                    "mode": f"{mode:04o}",
                }
            )

    archive_data = archive_path.read_bytes()
    commit = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    release_manifest = {
        "schema_version": "1.0.0",
        "product": {"name": name, "version": version},
        "source": {"commit": commit},
        "archive": {
            "file": archive_path.name,
            "root": archive_root,
            "sha256": _sha256(archive_data),
            "size": len(archive_data),
        },
        "files": file_records,
    }
    manifest_path = output_dir / "release-manifest.json"
    sbom_path = output_dir / "sbom.cdx.json"
    checksums_path = output_dir / "SHA256SUMS"
    manifest_path.write_bytes(_json_bytes(release_manifest))
    sbom_path.write_bytes(_json_bytes(build_sbom(root, name, version)))

    checksum_targets = (archive_path, manifest_path, sbom_path)
    checksums_path.write_text(
        "".join(f"{_sha256(path.read_bytes())}  {path.name}\n" for path in checksum_targets),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "archive": archive_path,
        "manifest": manifest_path,
        "sbom": sbom_path,
        "checksums": checksums_path,
    }


def _verify_sbom_document(sbom: object, inventory: object, commit: str) -> None:
    if not isinstance(sbom, dict) or sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.5":
        raise ReleaseError("SBOM is not a supported CycloneDX inventory")
    if not isinstance(inventory, dict):
        raise ReleaseError("archived dependency inventory is invalid")
    runtime_targets = [target for target in inventory.get("targets", []) if target.get("profile") == "runtime"]
    runtime_occurrences: dict[tuple[str, str], list[dict[str, object]]] = {}
    runtime_direct: set[str] = set()
    for target in runtime_targets:
        for component in target.get("components", []):
            runtime_occurrences.setdefault((component["name"], component["version"]), []).append(component)
            if component.get("direct"):
                runtime_direct.add(component["name"])
    catalog = {(item["name"], item["version"]): item for item in inventory.get("component_catalog", [])}
    components = sbom.get("components")
    if not isinstance(components, list) or len(components) != len(runtime_occurrences):
        raise ReleaseError("SBOM runtime component coverage mismatch")
    refs: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            raise ReleaseError("SBOM component is not an object")
        key = (component.get("name"), component.get("version"))
        expected = catalog.get(key)
        if expected is None or component.get("purl") != expected.get("purl") or component.get("bom-ref") != expected.get("purl"):
            raise ReleaseError(f"SBOM contains an unknown or mismatched component: {key[0]}")
        if component["bom-ref"] in refs:
            raise ReleaseError(f"SBOM contains a duplicate component: {key[0]}")
        refs.add(component["bom-ref"])
        if component.get("licenses") != [{"expression": expected.get("license_expression")}]:
            raise ReleaseError(f"SBOM component lacks the reviewed license: {key[0]}")
        expected_hashes = sorted({item["artifact"]["sha256"] for item in runtime_occurrences[key]})
        observed_hashes = sorted(item.get("content") for item in component.get("hashes", []) if item.get("alg") == "SHA-256")
        if observed_hashes != expected_hashes:
            raise ReleaseError(f"SBOM artifact hash coverage mismatch: {key[0]}")
    metadata = sbom.get("metadata")
    properties = metadata.get("properties", []) if isinstance(metadata, dict) else []
    property_map = {item.get("name"): item.get("value") for item in properties if isinstance(item, dict)}
    if property_map.get("claude-ads:source-commit") != commit:
        raise ReleaseError("SBOM source commit binding mismatch")
    dependencies = sbom.get("dependencies")
    if not isinstance(dependencies, list) or len(dependencies) != len(refs) + 1:
        raise ReleaseError("SBOM dependency graph coverage mismatch")
    dependency_refs = [item.get("ref") for item in dependencies if isinstance(item, dict)]
    if len(dependency_refs) != len(set(dependency_refs)):
        raise ReleaseError("SBOM dependency graph has duplicate refs")
    allowed_refs = refs | {metadata["component"]["bom-ref"]}
    if set(dependency_refs) != allowed_refs:
        raise ReleaseError("SBOM dependency graph refs are incomplete")
    for dependency in dependencies:
        if not set(dependency.get("dependsOn", [])).issubset(refs):
            raise ReleaseError("SBOM dependency graph contains a dangling ref")
    app = next(item for item in dependencies if item["ref"] == metadata["component"]["bom-ref"])
    expected_direct = sorted(catalog[(name, next(version for candidate, version in runtime_occurrences if candidate == name))]["purl"] for name in runtime_direct)
    if app.get("dependsOn") != expected_direct:
        raise ReleaseError("SBOM application dependency set includes non-runtime or missing direct components")


def verify_release(output_dir: Path, expected_commit: str, repository_root: Path) -> None:
    if not isinstance(expected_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ReleaseError("trusted expected commit must be a full lowercase Git SHA-1")
    repository_root = repository_root.resolve()
    trusted_paths = package_files(sorted(_git(repository_root, "ls-tree", "-r", "--name-only", expected_commit).decode("utf-8").splitlines()))
    manifest_path = output_dir / "release-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"release manifest is missing or invalid: {exc}") from exc
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "product", "source", "archive", "files"} or manifest.get("schema_version") != "1.0.0":
        raise ReleaseError("release manifest fields/schema mismatch")
    product, source, archive_meta, records = manifest["product"], manifest["source"], manifest["archive"], manifest["files"]
    if not isinstance(product, dict) or set(product) != {"name", "version"} or not all(isinstance(product.get(key), str) and product[key] for key in ("name", "version")):
        raise ReleaseError("release manifest product mismatch")
    try:
        trusted_plugin = json.loads(_git(repository_root, "show", f"{expected_commit}:.claude-plugin/plugin.json"))
    except json.JSONDecodeError as exc:
        raise ReleaseError("trusted Git commit contains an invalid plugin manifest") from exc
    if (
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", product["name"])
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", product["version"])
        or not isinstance(trusted_plugin, dict)
        or trusted_plugin.get("name") != product["name"]
        or trusted_plugin.get("version") != product["version"]
    ):
        raise ReleaseError("release manifest product differs from the trusted Git plugin identity")
    if not isinstance(source, dict) or set(source) != {"commit"} or source.get("commit") != expected_commit:
        raise ReleaseError("release manifest does not bind the trusted expected commit")
    if not isinstance(archive_meta, dict) or set(archive_meta) != {"file", "root", "sha256", "size"}:
        raise ReleaseError("release manifest archive fields mismatch")
    expected_root = f"{product['name']}-{product['version']}"
    if archive_meta.get("root") != expected_root or archive_meta.get("file") != f"{expected_root}.zip" or not re.fullmatch(r"[0-9a-f]{64}", str(archive_meta.get("sha256", ""))) or type(archive_meta.get("size")) is not int or archive_meta["size"] <= 0:
        raise ReleaseError("release manifest archive identity/type mismatch")
    if not isinstance(records, list) or not records:
        raise ReleaseError("release manifest files must be a nonempty array")
    record_paths: list[str] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "size", "mode"} or not isinstance(record.get("path"), str) or validate_portable_path(record["path"]) or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", ""))) or type(record.get("size")) is not int or record["size"] < 0 or record.get("mode") not in {"0644", "0755"}:
            raise ReleaseError("release manifest file record mismatch")
        record_paths.append(record["path"])
    if record_paths != sorted(set(record_paths)):
        raise ReleaseError("release manifest file paths are duplicated or unordered")
    if record_paths != trusted_paths:
        raise ReleaseError("release manifest file list differs from the trusted Git commit")

    checksums_path = output_dir / "SHA256SUMS"
    if not checksums_path.is_file():
        raise ReleaseError("SHA256SUMS is missing")
    checksum_records: dict[str, str] = {}
    for line in checksums_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if not match:
            raise ReleaseError(f"invalid SHA256SUMS line: {line!r}")
        expected, filename = match.groups()
        if filename in checksum_records:
            raise ReleaseError(f"duplicate SHA256SUMS filename: {filename}")
        checksum_records[filename] = expected
        path = output_dir / filename
        if not path.is_file() or _sha256(path.read_bytes()) != expected:
            raise ReleaseError(f"checksum mismatch: {filename}")

    expected_checksum_files = {archive_meta["file"], "release-manifest.json", "sbom.cdx.json"}
    if set(checksum_records) != expected_checksum_files:
        raise ReleaseError("SHA256SUMS file set mismatch")
    archive_path = output_dir / archive_meta["file"]
    if not archive_path.is_file() or archive_path.stat().st_size != archive_meta["size"] or _sha256(archive_path.read_bytes()) != archive_meta["sha256"]:
        raise ReleaseError("archive digest disagrees with release manifest")

    expected_records = {record["path"]: record for record in records}
    root = archive_meta["root"]
    archived_dependency_files: dict[str, bytes] = {}
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        expected_names = [f"{root}/{path}" for path in expected_records]
        if names != expected_names:
            raise ReleaseError("archive paths or order disagree with release manifest")
        for name in names:
            relative = name.removeprefix(f"{root}/")
            for issue in validate_portable_path(relative):
                raise ReleaseError(f"unsafe archive path {name!r}: {issue}")
            record = expected_records[relative]
            data = archive.read(name)
            if len(data) != record["size"] or _sha256(data) != record["sha256"]:
                raise ReleaseError(f"archive member disagrees with manifest: {relative}")
            observed_mode = f"{(archive.getinfo(name).external_attr >> 16) & 0o7777:04o}"
            if observed_mode != record["mode"]:
                raise ReleaseError(f"archive member mode disagrees with manifest: {relative}")
            trusted_data = _git(repository_root, "show", f"{expected_commit}:{relative}")
            trusted_tree = _git(repository_root, "ls-tree", expected_commit, "--", relative).decode("utf-8").strip()
            trusted_mode = "0755" if trusted_tree.startswith("100755 ") else "0644" if trusted_tree.startswith("100644 ") else None
            if data != trusted_data or record["mode"] != trusted_mode:
                raise ReleaseError(f"archive member differs from trusted Git commit: {relative}")
            if relative in {
                "requirements.txt", "requirements-dev.txt", "requirements.lock",
                "requirements-dev.lock", "pyproject.toml", "THIRD_PARTY_NOTICES.md",
                "control-plane/manifests/dependency-inventory.json",
                "control-plane/manifests/external-runtime-dependencies.json",
                ".claude-plugin/plugin.json",
            } or relative.startswith("control-plane/dependency-evidence/"):
                archived_dependency_files[relative] = data

    sbom = json.loads((output_dir / "sbom.cdx.json").read_text(encoding="utf-8"))
    required_archived = {
        "requirements.txt", "requirements-dev.txt", "requirements.lock",
        "requirements-dev.lock", "pyproject.toml", "THIRD_PARTY_NOTICES.md",
        "control-plane/manifests/dependency-inventory.json",
        "control-plane/manifests/external-runtime-dependencies.json",
        ".claude-plugin/plugin.json",
        *{
            f"control-plane/dependency-evidence/{profile}-{platform}-{abi}.json"
            for profile in ("runtime", "development")
            for platform in ("linux", "macos-arm", "macos-x86", "windows")
            for abi in ("cp311", "cp312")
        },
    }
    if set(archived_dependency_files) != required_archived:
        raise ReleaseError("release archive lacks dependency inventory inputs")
    try:
        archived_plugin = json.loads(archived_dependency_files[".claude-plugin/plugin.json"])
    except json.JSONDecodeError as exc:
        raise ReleaseError("archived plugin manifest is invalid") from exc
    if not isinstance(archived_plugin, dict) or archived_plugin.get("name") != product["name"] or archived_plugin.get("version") != product["version"]:
        raise ReleaseError("release product identity disagrees with archived plugin manifest")
    inventory = json.loads(archived_dependency_files["control-plane/manifests/dependency-inventory.json"])
    manifest_records = inventory.get("manifests", []) if isinstance(inventory, dict) else []
    if len(manifest_records) != 5:
        raise ReleaseError("archived dependency manifest coverage is incomplete")
    for record in manifest_records:
        content = archived_dependency_files.get(record.get("path"))
        if content is None or record.get("sha256") != _sha256(content):
            raise ReleaseError(f"archived dependency manifest hash mismatch: {record.get('path')}")
    with tempfile.TemporaryDirectory(prefix="claude-ads-release-verify-") as temporary:
        dependency_root = Path(temporary)
        for relative, content in archived_dependency_files.items():
            destination = dependency_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        verified_inventory = _load_dependency_inventory(dependency_root)
        _load_external_runtime_dependencies(dependency_root)
    if verified_inventory != inventory:
        raise ReleaseError("archived dependency inventory semantic verification mismatch")
    properties = sbom.get("metadata", {}).get("properties", []) if isinstance(sbom, dict) else []
    property_map = {item.get("name"): item.get("value") for item in properties if isinstance(item, dict)}
    if property_map.get("claude-ads:dependency-inventory-sha256") != _sha256(archived_dependency_files["control-plane/manifests/dependency-inventory.json"]):
        raise ReleaseError("SBOM dependency inventory binding mismatch")
    _verify_sbom_document(sbom, inventory, expected_commit)
    expected_sbom = _build_sbom_from_inventory(
        inventory,
        manifest["product"]["name"],
        manifest["product"]["version"],
        expected_commit,
        _sha256(archived_dependency_files["control-plane/manifests/dependency-inventory.json"]),
    )
    if sbom != expected_sbom:
        raise ReleaseError("SBOM does not equal the canonical archived-inventory projection")


def _json_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"{label} must be a JSON object")
    return value


def _check_grounding_and_capabilities(root: Path, as_of: date) -> dict[str, object]:
    source_doc = _json_object(
        root / "control-plane/manifests/source-ledger.json", "source ledger"
    )
    claim_doc = _json_object(
        root / "control-plane/manifests/claim-ledger.json", "claim ledger"
    )
    capability_doc = _json_object(
        root / "control-plane/manifests/capability-manifest.json", "capability manifest"
    )
    sources_raw = source_doc.get("sources")
    claims_raw = claim_doc.get("claims")
    platforms_raw = capability_doc.get("platforms")
    if not isinstance(sources_raw, list) or not isinstance(claims_raw, list):
        raise ReleaseError("source and claim ledgers require arrays")
    if not isinstance(platforms_raw, list):
        raise ReleaseError("capability manifest requires a platforms array")
    sources = {
        item.get("id"): item
        for item in sources_raw
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    claims = {
        item.get("id"): item
        for item in claims_raw
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if len(sources) != len(sources_raw) or len(claims) != len(claims_raw):
        raise ReleaseError("source or claim ledger contains an invalid or duplicate ID")
    load_bearing = 0
    load_bearing_source_ids: set[str] = set()
    for claim_id, claim in claims.items():
        source_ids = claim.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            raise ReleaseError(f"claim {claim_id} has no sources")
        for source_id in source_ids:
            source = sources.get(source_id)
            if source is None or claim_id not in source.get("claim_ids", []):
                raise ReleaseError(f"claim/source reciprocity failed: {claim_id} -> {source_id}")
        if claim.get("load_bearing") is True:
            load_bearing += 1
            if claim.get("verdict") != "verified":
                raise ReleaseError(f"load-bearing claim is not verified: {claim_id}")
            try:
                verified = date.fromisoformat(str(claim["last_verified"]))
                due = date.fromisoformat(str(claim["refresh_due"]))
            except (KeyError, ValueError) as exc:
                raise ReleaseError(f"load-bearing claim has invalid refresh date: {claim_id}") from exc
            if verified > as_of or due < verified:
                raise ReleaseError(
                    f"load-bearing claim has an invalid verification window: {claim_id}"
                )
            if due < as_of:
                raise ReleaseError(f"load-bearing claim is stale: {claim_id}")
            load_bearing_source_ids.update(source_ids)
    if load_bearing == 0:
        raise ReleaseError("no load-bearing claims are registered")
    for source_id, source in sources.items():
        for claim_id in source.get("claim_ids", []):
            if claim_id not in claims or source_id not in claims[claim_id].get("source_ids", []):
                raise ReleaseError(f"source/claim reciprocity failed: {source_id} -> {claim_id}")
        if not source.get("license") or source.get("redistribution") == "prohibited":
            raise ReleaseError(f"source lacks releasable license metadata: {source_id}")
        if source_id in load_bearing_source_ids:
            try:
                retrieved = date.fromisoformat(str(source["retrieved_at"]))
                due = date.fromisoformat(str(source["refresh_due"]))
            except (KeyError, ValueError) as exc:
                raise ReleaseError(
                    f"load-bearing source has invalid refresh date: {source_id}"
                ) from exc
            if retrieved > as_of or due < retrieved:
                raise ReleaseError(
                    f"load-bearing source has an invalid verification window: {source_id}"
                )
            if due < as_of:
                raise ReleaseError(f"load-bearing source is stale: {source_id}")

    verified_capabilities = 0
    disabled_capabilities = 0
    platform_ids: set[str] = set()
    for platform in platforms_raw:
        if not isinstance(platform, dict) or not isinstance(platform.get("id"), str):
            raise ReleaseError("capability platform is invalid")
        platform_id = platform["id"]
        if platform_id in platform_ids:
            raise ReleaseError(f"duplicate capability platform: {platform_id}")
        platform_ids.add(platform_id)
        capabilities = platform.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            raise ReleaseError(f"platform has no capabilities: {platform_id}")
        capability_ids: set[str] = set()
        for capability in capabilities:
            if not isinstance(capability, dict) or not isinstance(capability.get("id"), str):
                raise ReleaseError(f"invalid capability for {platform_id}")
            capability_id = capability["id"]
            if capability_id in capability_ids:
                raise ReleaseError(f"duplicate {platform_id} capability: {capability_id}")
            capability_ids.add(capability_id)
            status = capability.get("status")
            implementation = capability.get("implementation_paths", [])
            fixtures = capability.get("fixture_paths", [])
            tests = capability.get("test_paths", [])
            source_ids = capability.get("source_ids", [])
            for relative in [*implementation, *fixtures, *tests]:
                if not isinstance(relative, str) or not (root / relative).is_file():
                    raise ReleaseError(
                        f"{platform_id}.{capability_id} evidence path is missing: {relative!r}"
                    )
            for source_id in source_ids:
                if source_id not in sources:
                    raise ReleaseError(
                        f"{platform_id}.{capability_id} references unknown source {source_id}"
                    )
            if status == "fixture-verified":
                if not implementation or not fixtures or not tests or not source_ids:
                    raise ReleaseError(
                        f"fixture-verified capability lacks complete evidence: {platform_id}.{capability_id}"
                    )
                verified_capabilities += 1
            elif status == "disabled":
                if not capability.get("disabled_reason"):
                    raise ReleaseError(
                        f"disabled capability lacks reason: {platform_id}.{capability_id}"
                    )
                disabled_capabilities += 1
    if len(platform_ids) != 12:
        raise ReleaseError(f"capability manifest covers {len(platform_ids)} platforms, expected 12")
    root_on_path = str(root)
    inserted_path = root_on_path not in sys.path
    if inserted_path:
        sys.path.insert(0, root_on_path)
    try:
        try:
            from claude_ads_core.control_registry import RegistryError, load_control_registry
        except ImportError as exc:
            raise ReleaseError(f"control registry loader is unavailable: {exc}") from exc
        try:
            registry = load_control_registry(root)
        except RegistryError as exc:
            raise ReleaseError(f"control registry integrity failed: {exc}") from exc
    finally:
        if inserted_path:
            sys.path.remove(root_on_path)
    enabled_profiles = sum(profile.status == "enabled" for profile in registry.profiles)
    disabled_profiles = sum(profile.status == "disabled" for profile in registry.profiles)
    grounded_controls = sum(bool(entry.source_claim_ids) for entry in registry.entries)
    return {
        "source_count": len(sources),
        "claim_count": len(claims),
        "load_bearing_claim_count": load_bearing,
        "platform_count": len(platform_ids),
        "fixture_verified_capability_count": verified_capabilities,
        "disabled_capability_count": disabled_capabilities,
        "registered_control_count": len(registry.entries),
        "source_grounded_control_count": grounded_controls,
        "enabled_scoring_profile_count": enabled_profiles,
        "disabled_scoring_profile_count": disabled_profiles,
    }


def _check_vulnerability_exceptions(root: Path, as_of: date) -> dict[str, object]:
    module = _load_local_module(
        root, "scripts/audit_dependencies.py", "claude_ads_dependency_audit"
    )
    try:
        records, scope = module.load_exceptions(root, as_of)
    except module.DependencyAuditError as exc:
        raise ReleaseError(f"vulnerability exception integrity failed: {exc}") from exc
    document = _json_object(
        root / "control-plane/manifests/vulnerability-exceptions.json",
        "vulnerability exception ledger",
    )
    evidence_paths = sorted(
        {
            path
            for record in document["exceptions"]
            for path in record["evidence_paths"]
        }
    )
    required_release_paths = {
        "control-plane/manifests/vulnerability-exceptions.json",
        "control-plane/schemas/vulnerability-exceptions.schema.json",
        "scripts/audit_dependencies.py",
        *evidence_paths,
    }
    excluded = sorted(
        required_release_paths - set(package_files(sorted(required_release_paths)))
    )
    if excluded:
        raise ReleaseError(
            "vulnerability evidence is excluded from the release package: "
            + ", ".join(excluded)
        )
    packages = sorted({record.package for record in records.values()})
    return {
        "disposition": "not_affected",
        "exception_count": len(records),
        "packages": packages,
        "guarded_code_scope": scope,
        "packaged_evidence_paths": evidence_paths,
    }


def _schema_contract(
    schema: dict[str, object], definition: str, value: object, label: str
) -> dict[str, object]:
    definitions = schema.get("$defs")
    if not isinstance(definitions, dict) or not isinstance(definitions.get(definition), dict):
        raise ReleaseError(f"repository review schema lacks {definition!r}")
    contract = definitions[definition]
    required = contract.get("required")
    properties = contract.get("properties")
    if not isinstance(required, list) or not isinstance(properties, dict):
        raise ReleaseError(f"repository review schema definition is invalid: {definition}")
    if not isinstance(value, dict):
        raise ReleaseError(f"{label} must be an object")
    fields = set(value)
    missing = sorted(set(required) - fields)
    extra = sorted(fields - set(properties))
    if missing or extra:
        raise ReleaseError(f"{label} violates schema fields; missing={missing}, extra={extra}")
    return value


def _check_repository_review_ledger(root: Path) -> dict[str, object]:
    schema = _json_object(
        root / "control-plane/schemas/repository-review-ledger.schema.json",
        "repository review schema",
    )
    document = _json_object(
        root / "control-plane/manifests/repository-review-ledger.json",
        "repository review ledger",
    )
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ReleaseError("repository review schema must use JSON Schema Draft 2020-12")
    if not str(schema.get("$id", "")).endswith("repository-review-ledger.v1.json"):
        raise ReleaseError("repository review schema ID is not the v1 contract")
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not isinstance(properties, dict):
        raise ReleaseError("repository review schema has no top-level field contract")
    if set(document) != set(required) or set(document) != set(properties):
        raise ReleaseError("repository review ledger does not match its top-level schema")
    if document.get("schema_version") != "1.0.0":
        raise ReleaseError("repository review ledger schema version is unsupported")
    if document.get("reviewed_at") != "2026-07-11":
        raise ReleaseError("repository review ledger is not the required 2026-07-11 audit")
    if document.get("clean_room_policy") != "concepts-only-no-code-or-prose":
        raise ReleaseError("repository review ledger violates the clean-room policy")

    definitions = schema.get("$defs")
    disposition_contract = (
        definitions.get("disposition") if isinstance(definitions, dict) else None
    )
    dispositions = (
        set(disposition_contract.get("enum", []))
        if isinstance(disposition_contract, dict)
        else set()
    )
    if dispositions != {"adopt", "already-addressed", "defer", "reject"}:
        raise ReleaseError("repository review disposition vocabulary is incomplete")
    semantics = document.get("disposition_semantics")
    if not isinstance(semantics, dict) or set(semantics) != dispositions:
        raise ReleaseError("repository review disposition semantics are incomplete")

    repositories_raw = document.get("repositories")
    if not isinstance(repositories_raw, list) or len(repositories_raw) != 33:
        raise ReleaseError("repository review ledger must contain all 33 pinned repositories")
    repository_ids: set[str] = set()
    repository_names: set[str] = set()
    concept_ids: set[str] = set()
    fork_ids: set[str] = set()
    adopted_concepts = 0
    unlicensed_repositories = 0
    for index, raw_review in enumerate(repositories_raw):
        review = _schema_contract(
            schema, "repository_review", raw_review, f"repository review {index}"
        )
        review_id = review.get("id")
        repository = review.get("repository")
        if not isinstance(review_id, str) or review_id in repository_ids:
            raise ReleaseError(f"invalid or duplicate repository review ID: {review_id!r}")
        if not isinstance(repository, str) or repository in repository_names:
            raise ReleaseError(f"invalid or duplicate reviewed repository: {repository!r}")
        repository_ids.add(review_id)
        repository_names.add(repository)
        if review.get("source_url") != f"https://github.com/{repository}":
            raise ReleaseError(f"repository source URL is not canonical: {review_id}")
        if not re.fullmatch(r"[0-9a-f]{40}", str(review.get("reviewed_head_sha", ""))):
            raise ReleaseError(f"repository head is not pinned: {review_id}")
        if review.get("reviewed_at") != document["reviewed_at"]:
            raise ReleaseError(f"repository review date is inconsistent: {review_id}")
        if review.get("copy_policy") != document["clean_room_policy"]:
            raise ReleaseError(f"repository copy policy is unsafe: {review_id}")
        disposition = review.get("primary_disposition")
        if disposition not in dispositions:
            raise ReleaseError(f"repository disposition is missing: {review_id}")

        relationship = review.get("relationship")
        license_spdx = review.get("license_spdx")
        license_use = review.get("license_use")
        if license_spdx == "NOASSERTION":
            unlicensed_repositories += 1
            if license_use != "unverified-metadata-only" or disposition == "adopt":
                raise ReleaseError(f"unlicensed repository is not fail-closed: {review_id}")
        elif license_spdx in {"MIT", "Apache-2.0"}:
            expected_use = (
                "same-project-metadata-only"
                if relationship == "fork"
                else "compatible-metadata-only"
            )
            if license_use != expected_use:
                raise ReleaseError(f"repository license use is inconsistent: {review_id}")
        else:
            raise ReleaseError(f"repository license is unsupported: {review_id}")

        head_review = _schema_contract(
            schema, "head_review", review.get("head_review"), f"head review {review_id}"
        )
        if not isinstance(head_review.get("surfaces"), list) or not head_review["surfaces"]:
            raise ReleaseError(f"repository head review has no surfaces: {review_id}")
        if relationship == "fork":
            fork_ids.add(review_id)
            status = head_review.get("compare_status")
            if status not in {"ahead", "diverged", "no-common-ancestor"}:
                raise ReleaseError(f"fork lacks compare evidence: {review_id}")
            if status == "no-common-ancestor":
                if head_review.get("method") != "github-rest-compare-plus-tree":
                    raise ReleaseError(f"unrelated fork lacks tree evidence: {review_id}")
            else:
                required_compare = {
                    "upstream_base_sha",
                    "merge_base_sha",
                    "ahead_by",
                    "behind_by",
                    "commit_count",
                    "changed_files",
                    "additions",
                    "deletions",
                }
                if not required_compare <= set(head_review):
                    raise ReleaseError(f"fork compare evidence is incomplete: {review_id}")
        elif relationship != "external":
            raise ReleaseError(f"repository relationship is invalid: {review_id}")

        concepts = review.get("actionable_concepts")
        if not isinstance(concepts, list) or not concepts:
            raise ReleaseError(f"repository has no actionable concepts: {review_id}")
        for raw_concept in concepts:
            concept = _schema_contract(
                schema, "actionable_concept", raw_concept, f"concept for {review_id}"
            )
            concept_id = concept.get("id")
            if not isinstance(concept_id, str) or concept_id in concept_ids:
                raise ReleaseError(f"invalid or duplicate repository concept: {concept_id!r}")
            concept_ids.add(concept_id)
            concept_disposition = concept.get("disposition")
            if concept_disposition not in dispositions:
                raise ReleaseError(f"concept disposition is missing: {concept_id}")
            requirement_ids = concept.get("requirement_ids")
            if not isinstance(requirement_ids, list) or not requirement_ids:
                raise ReleaseError(f"concept lacks requirement traceability: {concept_id}")
            if concept_disposition == "adopt":
                adopted_concepts += 1
                if license_spdx == "NOASSERTION":
                    raise ReleaseError(f"unlicensed concept cannot be adopted: {concept_id}")

    survey = _schema_contract(
        schema, "fork_survey", document.get("fork_survey"), "fork survey"
    )
    if (
        survey.get("upstream_repository") != "AgriciDaniel/claude-ads"
        or survey.get("upstream_default_branch") != "main"
        or survey.get("paginated_fork_count") != 1026
        or survey.get("ancestor_or_equal_count") != 1009
        or survey.get("non_ancestor_count") != 17
        or survey.get("completeness") != "complete"
    ):
        raise ReleaseError("fork survey does not prove the required complete census")
    if survey["ancestor_or_equal_count"] + survey["non_ancestor_count"] != survey["paginated_fork_count"]:
        raise ReleaseError("fork survey arithmetic is inconsistent")
    non_ancestor_ids = survey.get("non_ancestor_repository_ids")
    if not isinstance(non_ancestor_ids, list) or len(non_ancestor_ids) != len(set(non_ancestor_ids)):
        raise ReleaseError("fork survey divergent IDs are invalid or duplicated")
    if set(non_ancestor_ids) != fork_ids or len(fork_ids) != 17:
        raise ReleaseError("fork survey does not reconcile to all divergent reviews")

    tracker_items_raw = document.get("tracker_items")
    tracker_scopes_raw = document.get("tracker_scopes")
    if not isinstance(tracker_items_raw, list) or not isinstance(tracker_scopes_raw, list):
        raise ReleaseError("repository tracker evidence is missing")
    tracker_items: dict[str, dict[str, object]] = {}
    tracker_keys: set[tuple[object, object, object]] = set()
    for index, raw_item in enumerate(tracker_items_raw):
        item = _schema_contract(schema, "tracker_item", raw_item, f"tracker item {index}")
        item_id = item.get("id")
        key = (item.get("repository"), item.get("kind"), item.get("number"))
        if not isinstance(item_id, str) or item_id in tracker_items or key in tracker_keys:
            raise ReleaseError(f"invalid or duplicate tracker item: {item_id!r}")
        tracker_items[item_id] = item
        tracker_keys.add(key)
        if item.get("repository") not in repository_names:
            raise ReleaseError(f"tracker repository was not reviewed: {item_id}")
        if item.get("disposition") not in dispositions:
            raise ReleaseError(f"tracker disposition is missing: {item_id}")
        links = item.get("linked_concept_ids")
        if not isinstance(links, list) or not links or not set(links) <= concept_ids:
            raise ReleaseError(f"tracker concept links are incomplete: {item_id}")
        if item.get("merged") is True and (
            item.get("kind") != "pull-request" or item.get("state") != "closed"
        ):
            raise ReleaseError(f"tracker merge state is inconsistent: {item_id}")

    covered_tracker_ids: set[str] = set()
    scoped_repositories: set[str] = set()
    for index, raw_scope in enumerate(tracker_scopes_raw):
        scope = _schema_contract(schema, "tracker_scope", raw_scope, f"tracker scope {index}")
        repository = scope.get("repository")
        if not isinstance(repository, str) or repository in scoped_repositories:
            raise ReleaseError(f"invalid or duplicate tracker scope: {repository!r}")
        scoped_repositories.add(repository)
        if scope.get("state_filter") != "all" or scope.get("completeness") != "complete":
            raise ReleaseError(f"tracker scope is not exhaustive: {repository}")
        item_ids = scope.get("item_ids")
        if not isinstance(item_ids, list) or len(item_ids) != len(set(item_ids)):
            raise ReleaseError(f"tracker scope IDs are invalid: {repository}")
        if covered_tracker_ids & set(item_ids):
            raise ReleaseError(f"tracker item appears in multiple scopes: {repository}")
        scoped_items = [tracker_items.get(item_id) for item_id in item_ids]
        if any(item is None or item.get("repository") != repository for item in scoped_items):
            raise ReleaseError(f"tracker scope does not resolve: {repository}")
        issue_count = sum(item.get("kind") == "issue" for item in scoped_items if item)
        pull_count = sum(item.get("kind") == "pull-request" for item in scoped_items if item)
        if scope.get("issue_count") != issue_count or scope.get("pull_request_count") != pull_count:
            raise ReleaseError(f"tracker scope arithmetic is inconsistent: {repository}")
        covered_tracker_ids.update(item_ids)
    if covered_tracker_ids != set(tracker_items) or len(tracker_items) != 14:
        raise ReleaseError("tracker scopes do not cover the complete 14-item review")

    blockers_raw = document.get("critical_blockers")
    if not isinstance(blockers_raw, list):
        raise ReleaseError("repository critical-blocker register is missing")
    blocker_ids: set[str] = set()
    open_blockers: list[str] = []
    for index, raw_blocker in enumerate(blockers_raw):
        blocker = _schema_contract(
            schema, "critical_blocker", raw_blocker, f"critical blocker {index}"
        )
        blocker_id = blocker.get("id")
        if not isinstance(blocker_id, str) or blocker_id in blocker_ids:
            raise ReleaseError(f"invalid or duplicate repository blocker: {blocker_id!r}")
        blocker_ids.add(blocker_id)
        if blocker.get("severity") != "critical":
            raise ReleaseError(f"repository blocker severity is invalid: {blocker_id}")
        if blocker.get("status") == "open":
            open_blockers.append(blocker_id)
        elif blocker.get("status") == "resolved":
            evidence_paths = blocker.get("evidence_paths")
            if not isinstance(evidence_paths, list) or not evidence_paths:
                raise ReleaseError(f"resolved repository blocker lacks evidence: {blocker_id}")
            for relative in evidence_paths:
                if (
                    not isinstance(relative, str)
                    or validate_portable_path(relative)
                    or not (root / relative).is_file()
                ):
                    raise ReleaseError(
                        f"repository blocker evidence path is missing: {blocker_id}: {relative!r}"
                    )
        else:
            raise ReleaseError(f"repository blocker status is invalid: {blocker_id}")
    if open_blockers:
        raise ReleaseError(f"critical repository review blockers remain open: {open_blockers}")

    return {
        "repository_count": len(repositories_raw),
        "fork_count": len(fork_ids),
        "paginated_fork_count": survey["paginated_fork_count"],
        "external_repository_count": len(repositories_raw) - len(fork_ids),
        "concept_count": len(concept_ids),
        "adopted_concept_count": adopted_concepts,
        "unlicensed_repository_count": unlicensed_repositories,
        "tracker_item_count": len(tracker_items),
        "critical_blocker_count": len(blocker_ids),
    }


def _check_ecosystem(root: Path, as_of: date | None = None) -> dict[str, object]:
    document = _json_object(
        root / "control-plane/manifests/ecosystem-dispositions.json",
        "ecosystem disposition ledger",
    )
    if set(document) != {
        "schema_version",
        "reviewed_at",
        "public_snapshot",
        "canonical_snapshot",
        "entries",
    }:
        raise ReleaseError("ecosystem disposition ledger has unsupported or missing fields")
    if document.get("schema_version") != "2.0.0":
        raise ReleaseError("ecosystem disposition ledger schema version is unsupported")
    try:
        reviewed_at = date.fromisoformat(str(document["reviewed_at"]))
    except ValueError as exc:
        raise ReleaseError("ecosystem disposition review date is invalid") from exc
    as_of = as_of or datetime.now(timezone.utc).date()
    if reviewed_at > as_of or (as_of - reviewed_at).days > 30:
        raise ReleaseError("ecosystem disposition review is stale or future-dated")

    snapshot_fields = {
        "repository",
        "observed_at",
        "source_url",
        "issue_numbers",
        "pull_request_numbers",
        "pull_request_heads",
    }

    def validated_snapshot(
        field: str,
        expected_repository: str,
        *,
        require_issues: bool,
    ) -> tuple[dict[str, object], list[int], list[int]]:
        snapshot = document.get(field)
        label = field.removesuffix("_snapshot")
        expected_url = f"https://github.com/{expected_repository}"
        if not isinstance(snapshot, dict) or set(snapshot) != snapshot_fields:
            raise ReleaseError(
                f"{label} ecosystem snapshot has unsupported or missing fields"
            )
        if (
            snapshot.get("repository") != expected_repository
            or snapshot.get("source_url") != expected_url
            or snapshot.get("observed_at") != document["reviewed_at"]
        ):
            raise ReleaseError(
                f"{label} ecosystem snapshot identity or date is inconsistent"
            )

        def numbers(name: str, *, required: bool) -> list[int]:
            values = snapshot.get(name)
            if (
                not isinstance(values, list)
                or (required and not values)
                or any(type(value) is not int or value < 1 for value in values)
                or values != sorted(set(values))
            ):
                raise ReleaseError(f"{label} ecosystem snapshot {name} is invalid")
            return values

        issues = numbers("issue_numbers", required=require_issues)
        pulls = numbers("pull_request_numbers", required=True)
        heads = snapshot.get("pull_request_heads")
        if (
            not isinstance(heads, dict)
            or set(heads) != {str(number) for number in pulls}
            or any(
                not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha)
                for sha in heads.values()
            )
        ):
            raise ReleaseError(f"{label} pull-request head snapshot is invalid")
        return snapshot, issues, pulls

    public_snapshot, public_issues, public_pulls = validated_snapshot(
        "public_snapshot", "AgriciDaniel/claude-ads", require_issues=True
    )
    canonical_snapshot, canonical_issues, canonical_pulls = validated_snapshot(
        "canonical_snapshot", "AI-Marketing-Hub/claude-ads", require_issues=False
    )
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ReleaseError("ecosystem disposition ledger is empty")
    required_fields = {
        "id",
        "repository",
        "kind",
        "number",
        "title",
        "url",
        "state",
        "decision",
        "license_review",
        "rationale",
        "requirement_ids",
    }
    allowed_fields = required_fields | {"regression_tests"}
    decisions = {
        "adopt-reimplement",
        "adopt-concept",
        "already-addressed",
        "defer",
        "reject",
        "superseded",
    }
    ids: set[str] = set()
    snapshots = {
        public_snapshot["repository"]: (public_snapshot, public_issues, public_pulls),
        canonical_snapshot["repository"]: (
            canonical_snapshot,
            canonical_issues,
            canonical_pulls,
        ),
    }
    observed_items: dict[str, set[tuple[str, int]]] = {
        repository: set() for repository in snapshots
    }
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not required_fields <= set(entry)
            or set(entry) - allowed_fields
            or not isinstance(entry.get("id"), str)
        ):
            raise ReleaseError("ecosystem disposition entry is invalid")
        if entry["id"] in ids:
            raise ReleaseError(f"duplicate ecosystem disposition: {entry['id']}")
        ids.add(entry["id"])
        if (
            entry.get("kind") not in {"issue", "pull-request"}
            or type(entry.get("number")) is not int
            or entry["number"] < 1
            or entry.get("state") not in {"open", "closed", "merged"}
            or entry.get("decision") not in decisions
            or entry.get("license_review") not in {"same-project-mit", "metadata-only"}
            or not isinstance(entry.get("title"), str)
            or not entry["title"].strip()
            or not isinstance(entry.get("rationale"), str)
            or not entry["rationale"].strip()
            or not isinstance(entry.get("requirement_ids"), list)
            or not entry["requirement_ids"]
            or not all(
                isinstance(requirement_id, str)
                and re.fullmatch(r"REQ-[A-Z]+-[0-9]{3}", requirement_id)
                for requirement_id in entry["requirement_ids"]
            )
            or len(entry["requirement_ids"]) != len(set(entry["requirement_ids"]))
        ):
            raise ReleaseError(f"ecosystem entry remains pending: {entry['id']}")
        regression_tests = entry.get("regression_tests")
        if regression_tests is not None and (
            not isinstance(regression_tests, list)
            or not regression_tests
            or not all(isinstance(item, str) and item.strip() for item in regression_tests)
            or len(regression_tests) != len(set(regression_tests))
        ):
            raise ReleaseError(f"ecosystem regression evidence is invalid: {entry['id']}")
        repository = entry.get("repository")
        if repository not in snapshots:
            raise ReleaseError(f"ecosystem entry repository is not snapshotted: {entry['id']}")
        item = (entry["kind"], entry["number"])
        if item in observed_items[repository]:
            raise ReleaseError(f"duplicate ecosystem tracker item: {repository}/{item}")
        observed_items[repository].add(item)
        snapshot = snapshots[repository][0]
        item_path = "issues" if entry["kind"] == "issue" else "pull"
        expected_url = f"{snapshot['source_url']}/{item_path}/{entry['number']}"
        expected_license = (
            "metadata-only" if entry["kind"] == "issue" else "same-project-mit"
        )
        if entry.get("url") != expected_url or entry.get("license_review") != expected_license:
            raise ReleaseError(f"ecosystem entry URL or license is invalid: {entry['id']}")

    for repository, (_, issues, pulls) in snapshots.items():
        expected_items = {
            *(("issue", number) for number in issues),
            *(("pull-request", number) for number in pulls),
        }
        if observed_items[repository] != expected_items:
            missing = sorted(expected_items - observed_items[repository])
            extra = sorted(observed_items[repository] - expected_items)
            raise ReleaseError(
                f"{repository} ecosystem snapshot coverage mismatch; "
                f"missing={missing}, extra={extra}"
            )
    repository_evidence = _check_repository_review_ledger(root)
    return {
        "issue_and_pull_request_count": len(entries),
        "public_issue_count": len(public_issues),
        "public_pull_request_count": len(public_pulls),
        "canonical_issue_count": len(canonical_issues),
        "canonical_pull_request_count": len(canonical_pulls),
        "public_reviewed_at": reviewed_at.isoformat(),
        **repository_evidence,
    }


def _gh_json(root: Path, endpoint: str) -> dict[str, object]:
    result = subprocess.run(
        ["gh", "api", endpoint],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode:
        raise ReleaseError(f"GitHub evidence query failed for {endpoint}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"GitHub evidence is not JSON for {endpoint}") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"GitHub evidence must be an object for {endpoint}")
    return value


def verify_github_run(root: Path, run_id: str, commit_sha: str) -> dict[str, object]:
    if not re.fullmatch(r"[1-9][0-9]*", run_id):
        raise ReleaseError("GitHub Actions run ID must be a positive integer")
    repository = "AI-Marketing-Hub/claude-ads"
    repo = _gh_json(root, f"repos/{repository}")
    if repo.get("visibility") != "private" or repo.get("private") is not True:
        raise ReleaseError("canonical repository is not private")
    run = _gh_json(root, f"repos/{repository}/actions/runs/{run_id}")
    if (
        run.get("head_sha") != commit_sha
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("path") != ".github/workflows/ci.yml"
        or run.get("head_branch") != "v2"
    ):
        raise ReleaseError("GitHub Actions run does not prove the exact private v2 subject")
    jobs_doc = _gh_json(root, f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=100")
    jobs = jobs_doc.get("jobs")
    if not isinstance(jobs, list):
        raise ReleaseError("GitHub Actions jobs evidence is missing")
    required = {
        "Live ecosystem reconciliation",
        "Repository audit",
        "Core tests (Python 3.11)",
        "Core tests (Python 3.12)",
        "Full test suite",
        "Installer tests (ubuntu-latest, Python 3.11)",
        "Installer tests (ubuntu-latest, Python 3.12)",
        "Installer tests (macos-15, Python 3.11)",
        "Installer tests (macos-15, Python 3.12)",
        "Installer tests (macos-15-intel, Python 3.11)",
        "Installer tests (macos-15-intel, Python 3.12)",
        "Installer tests (windows-latest, Python 3.11)",
        "Installer tests (windows-latest, Python 3.12)",
        "Reproducible package smoke test",
        "validate",
    }
    conclusions = {
        job.get("name"): job.get("conclusion")
        for job in jobs
        if isinstance(job, dict) and isinstance(job.get("name"), str)
    }
    missing = sorted(required - conclusions.keys())
    failed = sorted(name for name in required if conclusions.get(name) != "success")
    if missing or failed:
        raise ReleaseError(
            f"required GitHub jobs are incomplete; missing={missing}, non_success={failed}"
        )
    return {
        "repository": repository,
        "run_id": int(run_id),
        "url": run.get("html_url"),
        "head_sha": commit_sha,
        "jobs": sorted(required),
        "repository_visibility": "private",
    }


def evaluate_release_gate(
    root: Path,
    *,
    model_report: Path | None,
    review_evidence_dir: Path | None,
    github_run_id: str | None,
    trust_bundle_json: str | None = None,
    implementation_principals_json: str | None = None,
    model_trust_bundle_json: str | None = None,
    model_implementation_principals_json: str | None = None,
) -> dict[str, object]:
    """Evaluate every locally and externally verifiable release gate."""
    commit_sha = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    tree_sha = _git(root, "rev-parse", "HEAD^{tree}").decode("ascii").strip()
    checks: list[dict[str, object]] = []

    def check(check_id: str, operation) -> None:
        try:
            evidence = operation()
            checks.append({"id": check_id, "status": "pass", "evidence": evidence})
        except Exception as exc:  # each independent gate must remain visible
            checks.append({"id": check_id, "status": "fail", "error": str(exc)})

    check(
        "repository-audit",
        lambda: (
            {"tracked_file_count": len(tracked_files(root))}
            if not audit_repository(root)
            else (_ for _ in ()).throw(
                ReleaseError("repository audit failed: " + "; ".join(audit_repository(root)))
            )
        ),
    )
    check(
        "clean-subject",
        lambda: (
            {"commit_sha": commit_sha, "tree_sha": tree_sha}
            if not _git(root, "status", "--porcelain").strip()
            else (_ for _ in ()).throw(ReleaseError("release subject worktree is not clean"))
        ),
    )
    check(
        "source-capability-integrity",
        lambda: _check_grounding_and_capabilities(root, datetime.now(timezone.utc).date()),
    )
    check(
        "vulnerability-exception-integrity",
        lambda: _check_vulnerability_exceptions(root, datetime.now(timezone.utc).date()),
    )
    check(
        "ecosystem-ledger-integrity",
        lambda: _check_ecosystem(root, datetime.now(timezone.utc).date()),
    )

    def model_evidence() -> dict[str, object]:
        if model_report is None or not model_report.is_file():
            raise ReleaseError("canonical Claude model-gate report is required")
        module = _load_local_module(root, "evals/model_eval_gate.py", "claude_ads_model_gate")
        return module.verify_release_report(
            model_report,
            root / "evals/model-eval-contract.json",
            root,
            commit_sha,
            tree_sha,
            trust_bundle_json=model_trust_bundle_json,
            implementation_principals_json=model_implementation_principals_json,
        )

    check("canonical-model-evaluation", model_evidence)

    def independent_reviews() -> dict[str, object]:
        if review_evidence_dir is None:
            raise ReleaseError("external signed review evidence directory is required")
        module = _load_local_module(
            root, "scripts/review_evidence.py", "claude_ads_review_gate"
        )
        return module.verify_independent_reviews(
            root,
            review_evidence_dir,
            trust_bundle_json=trust_bundle_json,
            implementation_principals_json=implementation_principals_json,
            commit_sha=commit_sha,
            tree_sha=tree_sha,
        )

    check("independent-reviews", independent_reviews)
    check(
        "remote-ci",
        lambda: verify_github_run(root, github_run_id or "", commit_sha)
        if github_run_id
        else (_ for _ in ()).throw(ReleaseError("GitHub Actions run ID is required")),
    )
    satisfied = all(item["status"] == "pass" for item in checks)
    return {
        "schema_version": "2.0.0",
        "evidence_class": "release-gate-assessment",
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "subject": {"commit_sha": commit_sha, "tree_sha": tree_sha},
        "checks": checks,
        "release_gate_satisfied": satisfied,
    }


def _root(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="repository root (defaults to script parent)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audit", help="audit tracked repository files")
    package_parser = subparsers.add_parser("package", help="build deterministic artifacts")
    package_parser.add_argument("--output-dir", default="dist")
    verify_parser = subparsers.add_parser("verify", help="verify built artifacts")
    verify_parser.add_argument("--output-dir", default="dist")
    verify_parser.add_argument("--expected-commit", required=True, help="trusted full Git commit expected in the release")
    gate_parser = subparsers.add_parser(
        "gate", help="evaluate the exact candidate against every release gate"
    )
    gate_parser.add_argument(
        "--model-report", default="evals/results/canonical-model-gate.json"
    )
    gate_parser.add_argument(
        "--review-evidence-dir",
        default=os.environ.get("CLAUDE_ADS_REVIEW_EVIDENCE_DIR"),
    )
    gate_parser.add_argument("--github-run-id", default=os.environ.get("GITHUB_RUN_ID"))
    gate_parser.add_argument(
        "--output",
        help="optional repository-relative path for the redacted gate assessment",
    )
    args = parser.parse_args(argv)
    root = _root(args.root)

    try:
        if args.command == "audit":
            errors = audit_repository(root)
            if errors:
                raise ReleaseError("repository audit failed:\n- " + "\n- ".join(errors))
            print(f"release audit passed ({len(tracked_files(root))} tracked files)")
        elif args.command == "package":
            artifacts = build_release(root, (root / args.output_dir).resolve())
            verify_release((root / args.output_dir).resolve(), _git(root, "rev-parse", "HEAD").decode("ascii").strip(), root)
            for kind, path in artifacts.items():
                print(f"{kind}: {path}")
        elif args.command == "verify":
            verify_release((root / args.output_dir).resolve(), args.expected_commit, root)
            print("release artifacts verified")
        else:
            report = evaluate_release_gate(
                root,
                model_report=(root / args.model_report).resolve() if args.model_report else None,
                review_evidence_dir=(
                    Path(args.review_evidence_dir).expanduser().resolve()
                    if args.review_evidence_dir
                    else None
                ),
                github_run_id=args.github_run_id,
                trust_bundle_json=os.environ.get("CLAUDE_ADS_REVIEW_TRUST_KEYS_JSON"),
                implementation_principals_json=os.environ.get(
                    "CLAUDE_ADS_IMPLEMENTATION_PRINCIPALS_JSON"
                ),
                model_trust_bundle_json=os.environ.get(
                    "CLAUDE_ADS_MODEL_EVAL_TRUST_BUNDLE_JSON"
                ),
                model_implementation_principals_json=os.environ.get(
                    "CLAUDE_ADS_MODEL_EVAL_IMPLEMENTATION_PRINCIPALS_JSON"
                ),
            )
            rendered = _json_bytes(report).decode("utf-8")
            if args.output:
                issues = validate_portable_path(args.output)
                if issues:
                    raise ReleaseError("unsafe gate output path: " + "; ".join(issues))
                output = (root / args.output).resolve()
                try:
                    output.relative_to(root)
                except ValueError as exc:
                    raise ReleaseError("gate output escapes repository root") from exc
                parent = output.parent
                parent.mkdir(parents=True, exist_ok=True)
                if any(path.is_symlink() for path in (parent, output) if path.exists()):
                    raise ReleaseError("gate output path must not be a symlink")
                output.write_text(rendered, encoding="utf-8", newline="\n")
            print(rendered, end="")
            if not report["release_gate_satisfied"]:
                return 1
    except (OSError, KeyError, TypeError, ValueError, ReleaseError, zipfile.BadZipFile) as exc:
        print(f"release error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
