from __future__ import annotations

import copy
import hashlib
import importlib.util
import itertools
import json
from datetime import date, timedelta
from pathlib import Path
import re
import subprocess
import sys
import tomllib
import zipfile

import pytest
import yaml
from jsonschema import Draft202012Validator

RELEASE_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "release.py"
SPEC = importlib.util.spec_from_file_location("claude_ads_release", RELEASE_SCRIPT)
assert SPEC and SPEC.loader
release = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release
SPEC.loader.exec_module(release)

ReleaseError = release.ReleaseError
audit_repository = release.audit_repository
build_release = release.build_release
build_sbom = release.build_sbom
evaluate_release_gate = release.evaluate_release_gate
validate_portable_path = release.validate_portable_path
verify_github_run = release.verify_github_run
verify_release = release.verify_release
check_grounding_and_capabilities = release._check_grounding_and_capabilities
check_ecosystem = release._check_ecosystem
check_vulnerability_exceptions = release._check_vulnerability_exceptions


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _commit(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet")
    _git(root, "config", "user.name", "Release Test")
    _git(root, "config", "user.email", "release-test@example.invalid")
    # The fixture can run inside a managed worktree with repository hooks that
    # create local packaging state during ``git commit``. Keep those products
    # out of the synthetic repository's clean-subject assertion.
    _write(root, ".gitignore", "*.egg-info/\nuv.lock\n")
    _write(
        root,
        ".claude-plugin/plugin.json",
        json.dumps(
            {
                "name": "claude-ads",
                "version": "2.0.0",
                "license": "MIT",
                "repository": "https://example.invalid/claude-ads",
                "skills": ["./ads/", "./skills/"],
            }
        ),
    )
    _write(
        root,
        ".claude-plugin/marketplace.json",
        json.dumps(
            {
                "plugins": [
                    {
                        "name": "claude-ads",
                        "version": "2.0.0",
                        "license": "MIT",
                        "repository": "https://example.invalid/claude-ads",
                    }
                ]
            }
        ),
    )
    _write(root, "ads/SKILL.md", "---\nname: ads\ndescription: Main skill.\n---\n# Ads\n")
    _write(
        root,
        "skills/ads-google/SKILL.md",
        "---\nname: ads-google\ndescription: Google Ads.\n---\n# Google\n",
    )
    (root / "skills").mkdir(exist_ok=True)
    _write(root, "README.md", "# Claude Ads\n")
    _write(root, "LICENSE", "MIT\n")
    source_root = RELEASE_SCRIPT.parents[1]
    for relative in (
        "pyproject.toml", "requirements.txt", "requirements-dev.txt",
        "requirements.lock", "requirements-dev.lock",
        "THIRD_PARTY_NOTICES.md", "control-plane/manifests/dependency-inventory.json",
        "control-plane/manifests/external-runtime-dependencies.json",
    ):
        _write(root, relative, (source_root / relative).read_text(encoding="utf-8"))
    for evidence in sorted((source_root / "control-plane/dependency-evidence").glob("*.json")):
        relative = evidence.relative_to(source_root).as_posix()
        _write(root, relative, evidence.read_text(encoding="utf-8"))
    _write(root, "ads/research-sources/raw.md", "Research output does not ship.\n")
    _write(root, "branding/internal.html", "Internal branding does not ship.\n")
    _write(root, "research/private.md", "This tracked research does not ship.\n")
    _write(root, "tests/not-packaged.txt", "Tracked tests do not ship.\n")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "fixture")
    return root


def _single_version(root: Path, relative: str, pattern: str) -> str:
    text = (root / relative).read_text(encoding="utf-8")
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    assert len(matches) == 1, f"expected exactly one version in {relative}"
    return matches[0]


def test_product_and_core_version_contracts_are_consistent() -> None:
    root = RELEASE_SCRIPT.parents[1]
    plugin = json.loads(
        (root / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    )
    marketplace = json.loads(
        (root / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    product_versions = {
        plugin["version"],
        marketplace["metadata"]["version"],
        marketplace["plugins"][0]["version"],
        _single_version(root, "CITATION.cff", r'^version: "([^"]+)"$'),
        _single_version(
            root, "scripts/generate_report.py", r'^__version__ = "([^"]+)"$'
        ),
    }
    core_versions = {
        project["project"]["version"],
        _single_version(
            root, "claude_ads_core/__init__.py", r'^__version__ = "([^"]+)"$'
        ),
    }

    assert product_versions == {plugin["version"]}
    assert core_versions == {project["project"]["version"]}


def test_dependabot_workflow_is_read_only() -> None:
    root = RELEASE_SCRIPT.parents[1]
    workflow = (root / ".github/workflows/dependabot-automerge.yml").read_text(
        encoding="utf-8"
    )

    assert "gh pr review" not in workflow
    assert "--approve" not in workflow
    assert "gh pr merge" not in workflow
    assert "contents: write" not in workflow
    assert "pull-requests: write" not in workflow
    assert "contents: read" in workflow
    assert "pull-requests: read" in workflow


@pytest.mark.parametrize(
    "path",
    ["../escape", "/absolute", r"windows\separator", "aux.txt", "safe/../escape"],
)
def test_portable_paths_reject_unsafe_names(path: str) -> None:
    assert validate_portable_path(path)


def test_audit_checks_frontmatter_and_sensitive_content(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    assert audit_repository(root) == []

    skill = root / "skills/ads-google/SKILL.md"
    skill.write_text(
        "---\nname: wrong-name\ndescription: Google Ads.\n---\n",
        encoding="utf-8",
    )
    errors = audit_repository(root)
    assert any("frontmatter name" in error for error in errors)

    skill.write_text(
        "---\nname: ads-google\ndescription: Google Ads.\n---\n"
        "Local file: /var/ho" + "me/someone/private.txt\n",
        encoding="utf-8",
    )
    errors = audit_repository(root)
    assert any("Unix home path" in error for error in errors)

    skill.write_text(
        "---\nname: ads-google\ndescription: Google Ads.\n---\n"
        "Private source: ~/Docu" + "ments/client-research.txt\n",
        encoding="utf-8",
    )
    errors = audit_repository(root)
    assert any("personal tilde path" in error for error in errors)


def test_audit_rejects_sensitive_artifacts_and_binary_tokens(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    database = root / "assets/cache.sqlite3"
    database.parent.mkdir(parents=True, exist_ok=True)
    database.write_bytes(b"SQLite format 3\x00")
    _git(root, "add", "-f", "assets/cache.sqlite3")
    assert any("sensitive artifact" in error for error in audit_repository(root))

    binary_root = tmp_path / "binary"
    binary_root.mkdir()
    root = _repository(binary_root)
    binary = root / "assets/provider-response.bin"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_bytes(b"\x00\x01gh" + b"p_" + b"A" * 24 + b"\x00")
    _git(root, "add", "assets/provider-response.bin")
    assert any("possible GitHub token" in error for error in audit_repository(root))


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be", "utf-16"])
def test_audit_rejects_utf16_encoded_tokens(tmp_path: Path, encoding: str) -> None:
    root = _repository(tmp_path)
    token = "gh" + "p_" + "A" * 24
    fixture = root / "assets/exported-settings.bin"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_bytes(f"token={token}\n".encode(encoding))
    assert token.encode("utf-8") not in fixture.read_bytes()
    _git(root, "add", "assets/exported-settings.bin")
    errors = audit_repository(root)
    assert any(
        "possible GitHub token" in error and "utf-16" in error for error in errors
    ), errors


def test_sensitive_artifact_ignore_patterns_are_present() -> None:
    root = RELEASE_SCRIPT.parents[1]
    patterns = {
        line.strip()
        for line in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert {
        "*.log",
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        "credentials*",
        "secrets*",
        "config.local.*",
        ".audit-venv/",
        "venv/",
        "google-ads.yaml",
        "*.p8",
        "token.json",
        ".netrc",
        ".npmrc",
        ".mypy_cache/",
        ".ruff_cache/",
        ".coverage",
    } <= patterns


def test_audit_rejects_case_insensitive_path_collisions(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    # Stage the colliding path through the index only. Writing it would replace
    # the existing path on a case-insensitive filesystem before Git could see
    # both spellings.
    blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=root,
        input=b"---\nname: Ads-Google\ndescription: collision fixture.\n---\n",
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").strip()
    _git(
        root,
        "update-index",
        "--add",
        "--cacheinfo",
        f"100644,{blob},skills/Ads-Google/SKILL.md",
    )
    errors = audit_repository(root)
    assert any("case-insensitive path collision" in error for error in errors)


def test_marketplace_install_identifier_is_normalized() -> None:
    root = RELEASE_SCRIPT.parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    marketplace = json.loads(
        (root / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )
    assert "/plugin marketplace add agricidaniel/claude-ads" in readme
    assert "/plugin marketplace add AgriciDaniel/claude-ads" not in readme
    assert f"/plugin install claude-ads@{marketplace['name']}" in readme


def test_package_is_deterministic_public_safe_and_verifiable(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    first = build_release(root, tmp_path / "dist-a")
    second = build_release(root, tmp_path / "dist-b")

    assert hashlib.sha256(first["archive"].read_bytes()).digest() == hashlib.sha256(
        second["archive"].read_bytes()
    ).digest()
    assert first["manifest"].read_bytes() == second["manifest"].read_bytes()
    assert first["sbom"].read_bytes() == second["sbom"].read_bytes()
    verify_release(tmp_path / "dist-a", _commit(root), root)

    with zipfile.ZipFile(first["archive"]) as archive:
        names = archive.namelist()
        assert "claude-ads-2.0.0/ads/SKILL.md" in names
        assert not any(
            excluded in name
            for name in names
            for excluded in ("research/", "research-sources/", "tests/", "branding/")
        )
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())

    sbom = json.loads(first["sbom"].read_text(encoding="utf-8"))
    assert sbom["bomFormat"] == "CycloneDX"
    assert len(sbom["components"]) == 33
    assert "pytest" not in {component["name"] for component in sbom["components"]}
    assert all(component["scope"] == "required" for component in sbom["components"])


def test_verify_detects_tampering(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    artifacts = build_release(root, tmp_path / "dist")
    artifacts["archive"].write_bytes(artifacts["archive"].read_bytes() + b"tampered")
    with pytest.raises(ReleaseError, match="checksum mismatch"):
        verify_release(tmp_path / "dist", _commit(root), root)


@pytest.mark.parametrize("case", ["top-field", "bool-size", "float-size", "archive-field", "product"])
def test_release_manifest_schema_and_types_fail_closed(tmp_path: Path, case: str) -> None:
    root = _repository(tmp_path)
    artifacts = build_release(root, tmp_path / "dist")
    manifest = json.loads(artifacts["manifest"].read_text(encoding="utf-8"))
    if case == "top-field":
        manifest["unexpected"] = True
    elif case == "bool-size":
        manifest["files"][0]["size"] = True
    elif case == "float-size":
        manifest["archive"]["size"] = float(manifest["archive"]["size"])
    elif case == "archive-field":
        manifest["archive"]["unexpected"] = "x"
    else:
        manifest["product"]["name"] = "forged"
    artifacts["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = artifacts["checksums"].read_text(encoding="utf-8").splitlines()
    artifacts["checksums"].write_text("\n".join(f"{hashlib.sha256(artifacts['manifest'].read_bytes()).hexdigest()}  release-manifest.json" if line.endswith("  release-manifest.json") else line for line in lines) + "\n", encoding="utf-8")
    with pytest.raises(ReleaseError):
        verify_release(tmp_path / "dist", _commit(root), root)


def test_release_verifier_requires_trusted_commit_and_exact_checksum_set(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    artifacts = build_release(root, tmp_path / "dist")
    with pytest.raises(ReleaseError, match="trusted expected commit"):
        verify_release(tmp_path / "dist", "A" * 40, root)
    with artifacts["checksums"].open("a", encoding="utf-8") as handle:
        handle.write(f"{'0' * 64}  extra.json\n")
    with pytest.raises(ReleaseError, match="checksum mismatch|file set"):
        verify_release(tmp_path / "dist", _commit(root), root)


def test_external_runtime_manifest_is_exact_and_archived(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    document = release._load_external_runtime_dependencies(root)
    assert {item["id"] for item in document["dependencies"]} == {"playwright-browser-payload", "weasyprint-native-libraries"}
    build_release(root, tmp_path / "dist")
    verify_release(tmp_path / "dist", _commit(root), root)
    path = root / "control-plane/manifests/external-runtime-dependencies.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["dependencies"][0]["included_in_python_sbom"] = True
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ReleaseError, match="reviewed document|boundary"):
        release._load_external_runtime_dependencies(root)


def test_sbom_uses_actual_manifests(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    sbom = build_sbom(root, "claude-ads", "2.0.0")
    components = {component["name"]: component for component in sbom["components"]}
    assert len(components) == 33
    assert components["requests"]["version"] == "2.34.2"
    assert components["requests"]["licenses"] == [{"expression": "Apache-2.0"}]
    assert components["urllib3"]["licenses"] == [{"expression": "MIT"}]
    assert "pytest" not in components
    app = sbom["dependencies"][0]
    assert "pkg:pypi/pytest@9.0.3" not in app["dependsOn"]


def _rewrite_inventory(root: Path, mutate) -> None:
    path = root / "control-plane/manifests/dependency-inventory.json"
    inventory = json.loads(path.read_text(encoding="utf-8"))
    mutate(inventory)
    _write(root, "control-plane/manifests/dependency-inventory.json", json.dumps(inventory, indent=2, sort_keys=True) + "\n")


@pytest.mark.parametrize("field", ["version", "license_expression"])
def test_sbom_fails_closed_on_missing_version_or_license(tmp_path: Path, field: str) -> None:
    root = _repository(tmp_path)
    _rewrite_inventory(root, lambda inventory: inventory["component_catalog"][0].__setitem__(field, ""))
    with pytest.raises(ReleaseError, match="invalid name/version|lacks a reviewed license"):
        build_sbom(root, "claude-ads", "2.0.0")


def test_sbom_rejects_duplicate_components(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _rewrite_inventory(root, lambda inventory: inventory["component_catalog"].append(copy.deepcopy(inventory["component_catalog"][0])))
    with pytest.raises(ReleaseError, match="duplicate or multi-version"):
        build_sbom(root, "claude-ads", "2.0.0")


def test_sbom_rejects_direct_requirement_coverage_or_constraint_mismatch(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _rewrite_inventory(root, lambda inventory: inventory["direct_requirements"].pop())
    with pytest.raises(ReleaseError, match="direct requirement coverage mismatch"):
        build_sbom(root, "claude-ads", "2.0.0")

    second = tmp_path / "second"
    second.mkdir()
    root = _repository(second)
    def mismatch(inventory):
        for item in inventory["direct_requirements"]:
            if item["name"] == "requests":
                item["requirement"] = "requests>=3,<4"
                break
    _rewrite_inventory(root, mismatch)
    with pytest.raises(ReleaseError, match="direct requirement coverage mismatch"):
        build_sbom(root, "claude-ads", "2.0.0")


def test_lock_target_hash_and_marker_parity_fail_closed(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _rewrite_inventory(root, lambda inventory: inventory["targets"][0]["components"][0]["artifact"].__setitem__("sha256", "0" * 64))
    with pytest.raises(ReleaseError, match="target component evidence mismatch|lock target artifact mismatch"):
        build_sbom(root, "claude-ads", "2.0.0")

    parsed = release._parse_hash_lock(RELEASE_SCRIPT.parents[1] / "requirements-dev.lock")
    assert parsed["colorama"]["marker"] == 'sys_platform == "win32"'


def test_ci_only_tooling_is_isolated_and_hash_locked() -> None:
    root = RELEASE_SCRIPT.parents[1]
    audit_lock = release._parse_hash_lock(
        root / ".github/requirements-pip-audit.lock"
    )
    schema_lock = release._parse_hash_lock(
        root / ".github/requirements-schema-tests.lock"
    )
    schema_source = (
        root / ".github/requirements-schema-tests.in"
    ).read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert len(audit_lock) == 29
    assert audit_lock["pip-audit"]["version"] == "2.10.1"
    assert all(entry["hashes"] for entry in audit_lock.values())
    assert set(schema_lock) == {
        "attrs",
        "jsonschema",
        "jsonschema-specifications",
        "referencing",
        "rpds-py",
        "typing-extensions",
    }
    assert schema_lock["jsonschema"]["version"] == "4.26.0"
    assert all(entry["hashes"] for entry in schema_lock.values())
    assert [
        line for line in schema_source.splitlines() if line and not line.startswith("#")
    ] == ["jsonschema==4.26.0"]
    assert "python -m pip install pip-audit==" not in workflow
    assert "python -m venv .pip-audit-venv" in workflow
    assert (
        ".pip-audit-venv/bin/python -m pip install --require-hashes "
        "--only-binary=:all: -r .github/requirements-pip-audit.lock"
    ) in workflow
    schema_install = (
        "python -m pip install --require-hashes --only-binary=:all: "
        "-r .github/requirements-schema-tests.lock"
    )
    jobs = yaml.safe_load(workflow)["jobs"]
    for job_name in ("core-tests", "full-tests", "installer-matrix"):
        commands = [step.get("run", "") for step in jobs[job_name]["steps"]]
        assert any(schema_install in command.splitlines() for command in commands)
    native_matrix = jobs["installer-matrix"]["strategy"]["matrix"]
    assert native_matrix["shard-index"] == [0, 1]
    managed_matrix = jobs["managed-install-matrix"]["strategy"]["matrix"]
    assert managed_matrix == {
        key: value for key, value in native_matrix.items() if key != "shard-index"
    }
    verifier_tooling_install = (
        "python -m pip install --require-hashes --only-binary=:all: "
        "-r requirements-dev.lock"
    )
    for job_name in ("managed-install-matrix", "linux-floor"):
        lines = [
            line for step in jobs[job_name]["steps"]
            for line in step.get("run", "").splitlines()
        ]
        tooling_index = lines.index(verifier_tooling_install)
        verifier_index = next(
            index for index, line in enumerate(lines)
            if line.startswith("python scripts/verify_target_lock.py ")
        )
        assert tooling_index < verifier_index
    floor_lines = [
        line for step in jobs["linux-floor"]["steps"]
        for line in step.get("run", "").splitlines()
    ]
    assert 'git config --global --add safe.directory "$GITHUB_WORKSPACE"' in floor_lines
    assert 'git -C "$GITHUB_WORKSPACE" rev-parse --verify HEAD' in floor_lines
    floor = jobs["linux-floor"]
    assert re.fullmatch(
        r"quay\.io/pypa/manylinux_2_28_x86_64@sha256:[0-9a-f]{64}",
        floor["container"]["image"],
    )
    assert floor["strategy"]["matrix"]["python-tag"] == [
        "cp311-cp311", "cp312-cp312",
    ]
    assert floor["defaults"]["run"]["shell"] == "bash"
    assert not any("actions/setup-python@" in step.get("uses", "") for step in floor["steps"])
    for job_name in ("package-smoke", "validate"):
        assert "linux-floor" in jobs[job_name]["needs"]
        assert "managed-install-matrix" in jobs[job_name]["needs"]
    gate = jobs["validate"]["steps"][0]
    assert gate["env"]["LINUX_FLOOR_RESULT"] == "${{ needs.linux-floor.result }}"
    assert '"$LINUX_FLOOR_RESULT"' in gate["run"]
    assert gate["env"]["MANAGED_INSTALL_MATRIX_RESULT"] == (
        "${{ needs.managed-install-matrix.result }}"
    )
    assert '"$MANAGED_INSTALL_MATRIX_RESULT"' in gate["run"]
    repository_audit_lock = release._parse_hash_lock(
        root / ".github/requirements-repository-audit.lock"
    )
    assert set(repository_audit_lock) == {"pyyaml"}
    assert repository_audit_lock["pyyaml"]["version"] == "6.0.3"
    assert repository_audit_lock["pyyaml"]["hashes"]
    assert (
        "python -m pip install --require-hashes --only-binary=:all: "
        "-r .github/requirements-repository-audit.lock"
    ) in workflow
    assert 'python -m pip install "pyyaml>=6.0,<7.0"' not in workflow


def test_notice_inventory_has_no_dangling_references_and_records_bundled_terms() -> None:
    root = RELEASE_SCRIPT.parents[1]
    inventory = release._load_dependency_inventory(root)
    notices = {item["id"] for item in inventory["bundled_notices"]}
    assert len(notices) == len(inventory["component_catalog"]) == 39
    assert {"pyphen-selected-wheel-documents", "reportlab-selected-wheel-documents", "matplotlib-selected-wheel-documents"} <= notices
    artifacts = {component["artifact"]["sha256"] for target in inventory["targets"] for component in target["components"]}
    covered = {digest for notice in inventory["bundled_notices"] for document in notice["documents"] for digest in document["artifact_sha256s"]} | {digest for notice in inventory["bundled_notices"] for digest in notice["documentless_artifact_sha256s"]}
    assert covered == artifacts and len(artifacts) == 119
    webencodings = next(item for item in inventory["bundled_notices"] if item["component"] == "webencodings")
    assert not webencodings["documents"] and len(webencodings["documentless_artifact_sha256s"]) == 1
    urllib3 = next(item for item in inventory["component_catalog"] if item["name"] == "urllib3")
    assert urllib3["license_expression"] == "MIT"
    notices_text = (root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "urllib3: MIT" in notices_text
    assert "LicenseRef-Matplotlib-1.3" in notices_text


@pytest.mark.parametrize("case", ["header", "target-evidence", "artifact-filename", "dangling-edge", "dangling-notice"])
def test_inventory_provenance_and_graph_tampering_fail_closed(tmp_path: Path, case: str) -> None:
    root = _repository(tmp_path)
    def mutate(inventory):
        if case == "header":
            inventory["schema_version"] = "9.0.0"
        elif case == "target-evidence":
            inventory["targets"][0]["resolution_evidence_sha256"] = "missing"
        elif case == "artifact-filename":
            inventory["targets"][0]["components"][0]["artifact"]["filename"] = "wrong.whl"
        elif case == "dangling-edge":
            inventory["dependency_edges"].append({"profile": "runtime", "from": "requests", "to": "missing", "specifier": "", "marker": None, "extras": []})
        else:
            inventory["component_catalog"][0]["bundled_notice_ids"] = ["missing-notice"]
    _rewrite_inventory(root, mutate)
    with pytest.raises(ReleaseError):
        build_sbom(root, "claude-ads", "2.0.0")


def test_standalone_verify_rejects_self_consistent_sbom_semantic_tamper(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    artifacts = build_release(root, tmp_path / "dist")
    sbom = json.loads(artifacts["sbom"].read_text(encoding="utf-8"))
    sbom["components"][0]["scope"] = "optional"
    artifacts["sbom"].write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksum_lines = artifacts["checksums"].read_text(encoding="utf-8").splitlines()
    checksum_lines = [
        f"{hashlib.sha256(artifacts['sbom'].read_bytes()).hexdigest()}  sbom.cdx.json"
        if line.endswith("  sbom.cdx.json") else line
        for line in checksum_lines
    ]
    artifacts["checksums"].write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    with pytest.raises(ReleaseError, match="canonical archived-inventory projection"):
        verify_release(tmp_path / "dist", _commit(root), root)


@pytest.mark.parametrize(
    ("filename", "target_id"),
    [
        ("example-1.0-cp312-cp312-win_amd64.whl", "runtime-linux-cp312"),
        ("example-1.0-cp312-cp312-musllinux_1_2_x86_64.whl", "runtime-linux-cp312"),
        ("example-1.0-cp312-cp312-manylinux_2_29_x86_64.whl", "runtime-linux-cp312"),
        ("example-1.0-cp312-cp312-macosx_12_0_arm64.whl", "runtime-macos-arm-cp312"),
        ("example-1.0-cp312-cp312-macosx_11_0_x86_64.whl", "runtime-macos-arm-cp312"),
    ],
)
def test_wheel_tag_policy_rejects_cross_target_and_boundary_swaps(filename: str, target_id: str) -> None:
    inventory = release._load_dependency_inventory(RELEASE_SCRIPT.parents[1])
    target = next(item for item in inventory["targets"] if item["id"] == target_id)
    with pytest.raises(ReleaseError, match="wheel platform|newer"):
        release._wheel_is_compatible(filename, target, "example", "1.0")


def test_glibc_228_wheel_boundary_is_accepted() -> None:
    inventory = release._load_dependency_inventory(RELEASE_SCRIPT.parents[1])
    target = next(item for item in inventory["targets"] if item["id"] == "runtime-linux-cp312")
    release._wheel_is_compatible(
        "example-1.0-cp312-cp312-manylinux_2_28_x86_64.whl",
        target,
        "example",
        "1.0",
    )


def test_inventory_rejects_direct_flag_and_empty_graph_forgery(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    def forge(inventory):
        inventory["dependency_edges"] = []
        for target in inventory["targets"]:
            for component in target["components"]:
                component["direct"] = True
    _rewrite_inventory(root, forge)
    with pytest.raises(ReleaseError, match="direct component flags mismatch"):
        build_sbom(root, "claude-ads", "2.0.0")


@pytest.mark.parametrize("case", ["remove", "rename", "assignment", "text", "omit-document", "extra-artifact", "documentless"])
def test_inventory_rejects_bundled_notice_forgery(tmp_path: Path, case: str) -> None:
    root = _repository(tmp_path)
    def forge(inventory):
        if case == "remove":
            inventory["bundled_notices"].pop()
        elif case == "rename":
            inventory["bundled_notices"][0]["id"] = "renamed"
        elif case == "assignment":
            next(item for item in inventory["component_catalog"] if item["name"] == "fonttools")["bundled_notice_ids"] = []
        elif case == "text":
            inventory["bundled_notices"][0]["documents"][0]["text"] += "tampered"
        elif case == "omit-document":
            inventory["bundled_notices"][0]["documents"].pop()
        elif case == "extra-artifact":
            inventory["bundled_notices"][0]["documents"][0]["artifact_sha256s"].append("0" * 64)
        else:
            next(item for item in inventory["bundled_notices"] if item["component"] == "webencodings")["documentless_artifact_sha256s"] = []
    _rewrite_inventory(root, forge)
    with pytest.raises(ReleaseError, match="notice"):
        build_sbom(root, "claude-ads", "2.0.0")


def test_inventory_rejects_arbitrary_license_and_header_policy(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _rewrite_inventory(root, lambda inventory: inventory["component_catalog"][0].__setitem__("license_expression", "Definitely-A-License"))
    with pytest.raises(ReleaseError, match="reviewed license"):
        build_sbom(root, "claude-ads", "2.0.0")

    for field, value in (("managed_lock_python_range", ">=3.11"), ("source_date_epoch", 0), ("policy", "looks fine")):
        nested = tmp_path / field
        nested.mkdir()
        candidate = _repository(nested)
        _rewrite_inventory(candidate, lambda inventory, field=field, value=value: inventory["resolution"].__setitem__(field, value))
        with pytest.raises(ReleaseError, match="policy mismatch"):
            build_sbom(candidate, "claude-ads", "2.0.0")


def test_normalized_target_evidence_is_honest_about_foreign_source_and_native_ci_requirement() -> None:
    root = RELEASE_SCRIPT.parents[1]
    linux = json.loads((root / "control-plane/dependency-evidence/runtime-linux-cp311.json").read_text(encoding="utf-8"))
    windows = json.loads((root / "control-plane/dependency-evidence/development-windows-cp311.json").read_text(encoding="utf-8"))
    assert linux["evidence_class"] == "cross-target-pip-resolution-requiring-native-ci-confirmation"
    assert linux["source_environment"]["python_version"] == "3.12"
    assert linux["source_environment"]["sys_platform"] == "linux"
    assert linux["source_environment"]["python_version"] != linux["environment"]["python_version"]
    assert windows["source_environment"]["sys_platform"] != windows["environment"]["os"]
    assert any("colorama" in note for note in windows["normalization_notes"])


def test_standalone_verify_rejects_self_consistent_archive_inventory_tamper(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    artifacts = build_release(root, tmp_path / "dist")
    archive_path = artifacts["archive"]
    manifest = json.loads(artifacts["manifest"].read_text(encoding="utf-8"))
    archive_root = manifest["archive"]["root"]
    inventory_member = f"{archive_root}/control-plane/manifests/dependency-inventory.json"
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        contents = {info.filename: archive.read(info.filename) for info in infos}
    inventory = json.loads(contents[inventory_member])
    inventory["component_catalog"].reverse()  # Semantically equivalent, but not the reviewed bytes.
    inventory_bytes = (json.dumps(inventory, indent=2, sort_keys=True) + "\n").encode()
    contents[inventory_member] = inventory_bytes
    replacement = archive_path.with_suffix(".replacement")
    with zipfile.ZipFile(replacement, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for old in infos:
            info = zipfile.ZipInfo(old.filename, old.date_time)
            info.create_system = old.create_system
            info.external_attr = old.external_attr
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, contents[old.filename], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    replacement.replace(archive_path)
    record = next(item for item in manifest["files"] if item["path"] == "control-plane/manifests/dependency-inventory.json")
    record.update(size=len(inventory_bytes), sha256=hashlib.sha256(inventory_bytes).hexdigest())
    manifest["archive"].update(size=archive_path.stat().st_size, sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest())
    artifacts["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sbom = release._build_sbom_from_inventory(
        inventory, manifest["product"]["name"], manifest["product"]["version"],
        manifest["source"]["commit"], hashlib.sha256(inventory_bytes).hexdigest(),
    )
    artifacts["sbom"].write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts["checksums"].write_text(
        "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in (archive_path, artifacts["manifest"], artifacts["sbom"])),
        encoding="utf-8",
    )
    with pytest.raises(ReleaseError, match="trusted Git commit|independently reviewed document"):
        verify_release(tmp_path / "dist", _commit(root), root)


def test_package_requires_clean_head_subject(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    (root / "README.md").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ReleaseError, match="clean index and worktree"):
        build_release(root, tmp_path / "dist")


def test_claude_command_contract_distinguishes_plugin_namespace() -> None:
    root = RELEASE_SCRIPT.parents[1]
    product = json.loads(
        (root / "control-plane/manifests/product-manifest.json").read_text(encoding="utf-8")
    )
    assert product["canonical_command"] == "/ads"
    assert product["runtime_commands"] == {
        "claude_standalone_skill": "/ads",
        "claude_plugin": "/claude-ads:ads",
    }
    readme = (root / "README.md").read_text(encoding="utf-8")
    boundaries = (root / "control-plane/PRODUCT_BOUNDARIES.md").read_text(encoding="utf-8")
    for text in (readme, boundaries):
        assert "/ads" in text
        assert "/claude-ads:ads" in text


GROUNDING_WINDOW_AS_OF = release.date(2026, 9, 10)


def test_release_grounding_gate_validates_control_registry_and_profiles() -> None:
    """Exercise the live ledgers at the same UTC date used by the release gate."""
    root = RELEASE_SCRIPT.parents[1]
    as_of = release.datetime.now(release.timezone.utc).date()
    result = check_grounding_and_capabilities(root, as_of)
    assert result["registered_control_count"] == 414
    assert result["enabled_scoring_profile_count"] == 0
    assert result["disabled_scoring_profile_count"] == 12


def _ledgers_in_window(
    root: Path, verified: date, due: date
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    """Isolate date rules with synthetic verified claims and refresh windows."""
    manifests = root / "control-plane/manifests"
    source_doc = json.loads((manifests / "source-ledger.json").read_text(encoding="utf-8"))
    claim_doc = json.loads((manifests / "claim-ledger.json").read_text(encoding="utf-8"))
    load_bearing_source_ids: set[str] = set()
    target_claim = None
    for claim in claim_doc["claims"]:
        if claim["load_bearing"]:
            # This in-memory fixture is not canonical source evidence. A
            # provisional claim must not mask the date branch under test.
            claim["verdict"] = "verified"
            claim["last_verified"] = verified.isoformat()
            claim["refresh_due"] = due.isoformat()
            load_bearing_source_ids.update(claim["source_ids"])
            target_claim = target_claim or claim
    target_source = None
    for source in source_doc["sources"]:
        if source["id"] in load_bearing_source_ids:
            source["retrieved_at"] = verified.isoformat()
            source["refresh_due"] = due.isoformat()
            target_source = target_source or source
    assert target_claim is not None and target_source is not None
    return source_doc, claim_doc, target_claim, target_source


def _serve_ledgers(
    monkeypatch, source_doc: dict[str, object], claim_doc: dict[str, object]
) -> None:
    original_json_object = release._json_object

    def json_object(path: Path, label: str):
        if label == "source ledger":
            return source_doc
        if label == "claim ledger":
            return claim_doc
        return original_json_object(path, label)

    monkeypatch.setattr(release, "_json_object", json_object)


def test_release_grounding_gate_accepts_evidence_on_both_window_boundaries(
    monkeypatch,
) -> None:
    root = RELEASE_SCRIPT.parents[1]
    as_of = GROUNDING_WINDOW_AS_OF
    source_doc, claim_doc, _, _ = _ledgers_in_window(root, as_of, as_of)
    _serve_ledgers(monkeypatch, source_doc, claim_doc)
    result = check_grounding_and_capabilities(root, as_of)
    assert result["registered_control_count"] == 414


@pytest.mark.parametrize("verdict", ["provisional", "contested", "demoted", "retracted"])
def test_release_grounding_gate_rejects_unverified_load_bearing_claims(monkeypatch, verdict: str) -> None:
    root = RELEASE_SCRIPT.parents[1]
    as_of = GROUNDING_WINDOW_AS_OF
    source_doc, claim_doc, target_claim, _ = _ledgers_in_window(root, as_of, as_of)
    target_claim["verdict"] = verdict
    _serve_ledgers(monkeypatch, source_doc, claim_doc)
    with pytest.raises(ReleaseError, match=f"load-bearing claim is not verified: {target_claim['id']}$"):
        check_grounding_and_capabilities(root, as_of)


def test_release_grounding_gate_detects_expiry_from_the_date_alone(monkeypatch) -> None:
    root = RELEASE_SCRIPT.parents[1]
    as_of = GROUNDING_WINDOW_AS_OF
    source_doc, claim_doc, target_claim, _ = _ledgers_in_window(
        root, as_of - timedelta(days=10), as_of + timedelta(days=20)
    )
    _serve_ledgers(monkeypatch, source_doc, claim_doc)
    check_grounding_and_capabilities(root, as_of + timedelta(days=20))
    with pytest.raises(
        ReleaseError, match=f"load-bearing claim is stale: {target_claim['id']}"
    ):
        check_grounding_and_capabilities(root, as_of + timedelta(days=21))


@pytest.mark.parametrize(
    ("ledger", "verified_offset", "due_offset", "message"),
    [
        ("claim", 1, 20, "load-bearing claim has an invalid verification window"),
        ("claim", -2, -5, "load-bearing claim has an invalid verification window"),
        ("claim", -10, -1, "load-bearing claim is stale"),
        ("source", 1, 20, "load-bearing source has an invalid verification window"),
        ("source", -2, -5, "load-bearing source has an invalid verification window"),
        ("source", -10, -1, "load-bearing source is stale"),
    ],
    ids=[
        "claim-verified-after-as-of",
        "claim-window-inverted",
        "claim-expired",
        "source-retrieved-after-as-of",
        "source-window-inverted",
        "source-expired",
    ],
)
def test_release_grounding_gate_rejects_out_of_window_evidence(
    monkeypatch, ledger: str, verified_offset: int, due_offset: int, message: str
) -> None:
    root = RELEASE_SCRIPT.parents[1]
    as_of = GROUNDING_WINDOW_AS_OF
    source_doc, claim_doc, target_claim, target_source = _ledgers_in_window(
        root, as_of - timedelta(days=10), as_of + timedelta(days=20)
    )
    verified = (as_of + timedelta(days=verified_offset)).isoformat()
    due = (as_of + timedelta(days=due_offset)).isoformat()
    if ledger == "claim":
        target_claim["last_verified"], target_claim["refresh_due"] = verified, due
        target_id = target_claim["id"]
    else:
        target_source["retrieved_at"], target_source["refresh_due"] = verified, due
        target_id = target_source["id"]
    _serve_ledgers(monkeypatch, source_doc, claim_doc)
    with pytest.raises(ReleaseError, match=f"{message}: {target_id}$"):
        check_grounding_and_capabilities(root, as_of)


def test_vulnerability_exception_evidence_is_release_packaged() -> None:
    root = RELEASE_SCRIPT.parents[1]
    as_of = release.datetime.now(release.timezone.utc).date()
    result = check_vulnerability_exceptions(root, as_of)
    document = json.loads(
        (root / "control-plane/manifests/vulnerability-exceptions.json").read_text(
            encoding="utf-8"
        )
    )
    expected_paths = sorted(
        {
            path
            for exception in document["exceptions"]
            for path in exception["evidence_paths"]
        }
    )

    assert result["exception_count"] == len(document["exceptions"])
    assert result["packaged_evidence_paths"] == expected_paths
    assert set(expected_paths) <= set(release.package_files(expected_paths))


@pytest.mark.parametrize(
    ("kind", "license_review", "accepted"),
    [
        ("issue", "metadata-only", True),
        ("issue", "same-project-mit", False),
        ("pull-request", "metadata-only", True),
        ("pull-request", "same-project-mit", True),
        ("pull-request", "unreviewed", False),
    ],
)
def test_ecosystem_license_review_matches_metadata_or_reviewed_patch_use(
    tmp_path: Path, monkeypatch, kind: str, license_review: str, accepted: bool
) -> None:
    manifest = RELEASE_SCRIPT.parents[1] / "control-plane/manifests/ecosystem-dispositions.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    entry = next(item for item in document["entries"] if item["kind"] == kind)
    entry["license_review"] = license_review
    candidate = tmp_path / "control-plane/manifests/ecosystem-dispositions.json"
    candidate.parent.mkdir(parents=True)
    candidate.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(release, "_check_repository_review_ledger", lambda root: {})
    as_of = date.fromisoformat(document["reviewed_at"])
    if accepted:
        check_ecosystem(tmp_path, as_of)
    else:
        with pytest.raises(ReleaseError, match="license|pending"):
            check_ecosystem(tmp_path, as_of)


def test_ecosystem_gate_binds_public_snapshot_and_expires(
    tmp_path: Path, monkeypatch
) -> None:
    source_root = RELEASE_SCRIPT.parents[1]
    manifest = source_root / "control-plane/manifests/ecosystem-dispositions.json"
    candidate = tmp_path / "control-plane/manifests/ecosystem-dispositions.json"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(manifest.read_bytes())
    monkeypatch.setattr(
        release,
        "_check_repository_review_ledger",
        lambda root: {"repository_count": 33},
    )

    document = json.loads(manifest.read_text(encoding="utf-8"))
    reviewed_at = release.date.fromisoformat(document["reviewed_at"])
    public = document["public_snapshot"]
    canonical = document["canonical_snapshot"]

    result = check_ecosystem(tmp_path, reviewed_at)
    assert result["public_issue_count"] == len(public["issue_numbers"])
    assert result["public_pull_request_count"] == len(public["pull_request_numbers"])
    assert result["canonical_issue_count"] == len(canonical["issue_numbers"])
    assert result["canonical_pull_request_count"] == len(canonical["pull_request_numbers"])
    assert result["issue_and_pull_request_count"] == len(document["entries"]) == (
        len(public["issue_numbers"])
        + len(public["pull_request_numbers"])
        + len(canonical["issue_numbers"])
        + len(canonical["pull_request_numbers"])
    )
    assert "dependency-review" not in candidate.read_text(encoding="utf-8")

    with pytest.raises(ReleaseError, match="stale or future-dated"):
        check_ecosystem(tmp_path, reviewed_at + timedelta(days=31))
    with pytest.raises(ReleaseError, match="stale or future-dated"):
        check_ecosystem(tmp_path, reviewed_at - timedelta(days=1))

    dropped = public["pull_request_numbers"][-1]
    document = json.loads(candidate.read_text(encoding="utf-8"))
    document["public_snapshot"]["pull_request_numbers"].remove(dropped)
    del document["public_snapshot"]["pull_request_heads"][str(dropped)]
    candidate.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ReleaseError, match="coverage mismatch"):
        check_ecosystem(tmp_path, reviewed_at)

    document = json.loads(manifest.read_text(encoding="utf-8"))
    last_canonical = str(canonical["pull_request_numbers"][-1])
    document["canonical_snapshot"]["pull_request_heads"][last_canonical] = "not-a-sha"
    candidate.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ReleaseError, match="head snapshot"):
        check_ecosystem(tmp_path, reviewed_at)


def test_breaking_control_contracts_have_v1_compatibility_and_v2_instances() -> None:
    root = RELEASE_SCRIPT.parents[1]
    ecosystem_v1_schema = json.loads(
        (root / "control-plane/schemas/ecosystem-dispositions.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    ecosystem_v2_schema = json.loads(
        (root / "control-plane/schemas/ecosystem-dispositions.schema.json").read_text(
            encoding="utf-8"
        )
    )
    ecosystem_v2 = json.loads(
        (root / "control-plane/manifests/ecosystem-dispositions.json").read_text(
            encoding="utf-8"
        )
    )
    ecosystem_v1 = {
        "schema_version": "1.0.0",
        "reviewed_at": "2026-07-11",
        "entries": [],
    }

    assert not list(Draft202012Validator(ecosystem_v1_schema).iter_errors(ecosystem_v1))
    assert list(Draft202012Validator(ecosystem_v2_schema).iter_errors(ecosystem_v1))
    assert not list(Draft202012Validator(ecosystem_v2_schema).iter_errors(ecosystem_v2))


def test_release_gate_output_conforms_to_v2_schema() -> None:
    root = RELEASE_SCRIPT.parents[1]
    schema = json.loads(
        (root / "control-plane/schemas/release-gate-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    report = evaluate_release_gate(
        root,
        model_report=None,
        review_evidence_dir=None,
        github_run_id=None,
    )

    errors = list(Draft202012Validator(schema).iter_errors(report))
    assert errors == []
    assert report["schema_version"] == "2.0.0"
    assert len(report["checks"]) == 8
    assert len({item["id"] for item in report["checks"]}) == 8
    assert {item["id"] for item in report["checks"]} >= {
        "vulnerability-exception-integrity",
        "ecosystem-ledger-integrity",
    }


def test_release_gate_fails_closed_without_external_model_review_and_ci_evidence() -> None:
    root = RELEASE_SCRIPT.parents[1]
    report = evaluate_release_gate(
        root,
        model_report=None,
        review_evidence_dir=None,
        github_run_id=None,
    )
    checks = {item["id"]: item for item in report["checks"]}
    assert report["evidence_class"] == "release-gate-assessment"
    assert report["release_gate_satisfied"] is False
    assert checks["vulnerability-exception-integrity"]["status"] == "pass"
    assert checks["canonical-model-evaluation"]["status"] == "fail"
    assert checks["independent-reviews"]["status"] == "fail"
    assert checks["remote-ci"]["status"] == "fail"


def test_release_gate_forwards_external_model_trust_inputs(tmp_path: Path, monkeypatch) -> None:
    root = RELEASE_SCRIPT.parents[1]
    model_report = tmp_path / "model-report.json"
    model_report.write_text("{}", encoding="utf-8")
    captured = {}

    class ModelGate:
        @staticmethod
        def verify_release_report(*args, **kwargs):
            captured.update(kwargs)
            return {"release_gate_satisfied": True}

    original = release._load_local_module

    def load(root_arg, relative, module_name):
        if relative == "evals/model_eval_gate.py":
            return ModelGate
        return original(root_arg, relative, module_name)

    monkeypatch.setattr(release, "_load_local_module", load)
    evaluate_release_gate(
        root,
        model_report=model_report,
        review_evidence_dir=None,
        github_run_id=None,
        model_trust_bundle_json='{"external":true}',
        model_implementation_principals_json='["implementer"]',
    )
    assert captured == {
        "trust_bundle_json": '{"external":true}',
        "implementation_principals_json": '["implementer"]',
    }


def test_remote_ci_verifier_requires_exact_private_subject_and_all_jobs(
    tmp_path: Path, monkeypatch
) -> None:
    root = _repository(tmp_path)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    workflow = yaml.safe_load(
        (RELEASE_SCRIPT.parents[1] / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    required_jobs = []
    for job_id, job in workflow["jobs"].items():
        matrix = job.get("strategy", {}).get("matrix", {})
        assert not {"include", "exclude"} & matrix.keys()
        for values in itertools.product(*matrix.values()):
            parameters = dict(zip(matrix, values))
            name = re.sub(
                r"\$\{\{\s*matrix\.([a-zA-Z0-9_-]+)\s*\}\}",
                lambda match: str(parameters[match.group(1)]),
                job.get("name", job_id),
            )
            assert "${{" not in name
            required_jobs.append(name)
    assert len(required_jobs) == len(set(required_jobs))

    def evidence(_root: Path, endpoint: str) -> dict:
        if endpoint == "repos/AI-Marketing-Hub/claude-ads":
            return {"visibility": "private", "private": True}
        if endpoint.endswith("/jobs?per_page=100"):
            return {"jobs": [{"name": name, "conclusion": "success"} for name in required_jobs]}
        return {
            "head_sha": commit,
            "head_branch": "v2",
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "path": ".github/workflows/ci.yml",
            "html_url": "https://github.example.invalid/actions/runs/123",
        }

    monkeypatch.setattr(release, "_gh_json", evidence)
    result = verify_github_run(root, "123", commit)
    assert result["head_sha"] == commit
    assert result["repository_visibility"] == "private"
    assert result["event"] == "workflow_dispatch"
    assert result["ecosystem_reconciliation_mode"] == "strict"
    assert result["jobs"] == sorted(required_jobs)

    # Every actual workflow job must be present and successful, including every
    # native shard, each independent managed lifecycle, and both Linux floors.
    for job_name in required_jobs:
        for conclusion in (None, "failure", "skipped", "cancelled"):
            def incomplete_jobs(_root: Path, endpoint: str) -> dict:
                value = evidence(_root, endpoint)
                if endpoint.endswith("/jobs?per_page=100"):
                    remaining = [job for job in value["jobs"] if job["name"] != job_name]
                    if conclusion is not None:
                        remaining.append({"name": job_name, "conclusion": conclusion})
                    value = {"jobs": remaining}
                return value

            monkeypatch.setattr(release, "_gh_json", incomplete_jobs)
            with pytest.raises(ReleaseError, match="required GitHub jobs are incomplete"):
                verify_github_run(root, "123", commit)

    for malformed in (None, {"name": ""}, {"name": required_jobs[0], "conclusion": "success"}):
        def invalid_jobs(_root: Path, endpoint: str) -> dict:
            value = evidence(_root, endpoint)
            if endpoint.endswith("/jobs?per_page=100"):
                value = {"jobs": [*value["jobs"], malformed]}
            return value

        monkeypatch.setattr(release, "_gh_json", invalid_jobs)
        with pytest.raises(ReleaseError, match="invalid or duplicate names"):
            verify_github_run(root, "123", commit)

    def push_run(_root: Path, endpoint: str) -> dict:
        value = evidence(_root, endpoint)
        if endpoint.endswith("/actions/runs/123"):
            value = {**value, "event": "push"}
        return value

    monkeypatch.setattr(release, "_gh_json", push_run)
    with pytest.raises(ReleaseError, match="must be a workflow_dispatch run"):
        verify_github_run(root, "123", commit)

    def wrong_subject(_root: Path, endpoint: str) -> dict:
        value = evidence(_root, endpoint)
        if endpoint.endswith("/actions/runs/123"):
            value = {**value, "head_sha": "0" * 40}
        return value

    monkeypatch.setattr(release, "_gh_json", wrong_subject)
    with pytest.raises(ReleaseError, match="exact private v2 subject"):
        verify_github_run(root, "123", commit)
