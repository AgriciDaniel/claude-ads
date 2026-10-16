"""Installer ownership and dependency-isolation regression tests."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BASH_INSTALLER_ONLY = pytest.mark.skipif(
    os.name == "nt", reason="Bash installer behavior is exercised on Unix runners"
)
POWERSHELL_ONLY = pytest.mark.skipif(
    shutil.which("pwsh") is None, reason="PowerShell is not installed"
)
WINDOWS_POWERSHELL = shutil.which("powershell.exe") if os.name == "nt" else None
WINDOWS_POWERSHELL_ONLY = pytest.mark.skipif(
    WINDOWS_POWERSHELL is None, reason="Windows PowerShell 5.1 is not installed"
)
LEGACY_INSTALL_MESSAGE = "Existing Claude Ads files without an ownership manifest detected"
EMPTY_POWERSHELL_MANIFEST = {
    "version": 1,
    "target": "claude",
    "files": [],
    "directories": [],
    "recursive_directories": [],
}


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    if os.name == "nt":
        pytest.skip("Bash installer behavior is exercised on Linux and macOS runners")
    return subprocess.run(
        ["bash", str(ROOT / script), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _fake_python(tmp_path: Path, target: str, fail_venv: bool = False) -> Path:
    directory = tmp_path / "fake-bin"
    directory.mkdir()
    script = directory / "python3"
    delegate = shlex.quote(sys.executable)
    if target.count("|") == 3:
        target += "|glibc|2.28|supported" if "|linux|" in target else "|none|11.0|supported"
    script.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = \"-c\" ]; then printf '%s\\n' '{target}'; exit 0; fi\n"
        + ("exit 42\n" if fail_venv else f"exec {delegate} \"$@\"\n"),
        encoding="utf-8",
    )
    script.chmod(0o755)
    return directory


def _install(tmp_path: Path) -> tuple[Path, Path]:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    result = _run(
        "install.sh",
        "--target=claude",
        "--source=local",
        "--no-deps",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return skills, agents


def _managed_install(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    if sys.version_info[:2] not in {(3, 11), (3, 12)}:
        pytest.skip("Managed installs are declared for CPython 3.11 and 3.12")
    host_bin = tmp_path / "host-bin"
    host_bin.mkdir()
    (host_bin / "python3").symlink_to(Path(sys.executable).resolve())
    environment = {
        **os.environ,
        "PATH": f"{host_bin}{os.pathsep}{os.environ['PATH']}",
    }
    environment.pop("PYTHONPATH", None)
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    result = subprocess.run(
        [
            "bash",
            str(ROOT / "install.sh"),
            "--target=claude",
            "--source=local",
            f"--skill-dir={skills}",
            f"--agent-dir={agents}",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return skills, agents, environment


def _runtime_resources() -> list[str]:
    return [
        line
        for line in (ROOT / "control-plane/runtime-resources.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line and not line.startswith("#")
    ]


def _powershell_install(
    skills: Path,
    agents: Path,
    *,
    no_deps: bool = True,
    repo_dir: Path = ROOT,
    executable: str = "pwsh",
) -> subprocess.CompletedProcess[str]:
    command = [
        executable,
        "-NoProfile",
        "-File",
        str(ROOT / "install.ps1"),
        "-Target",
        "claude",
        "-SkillDir",
        str(skills),
        "-AgentDir",
        str(agents),
        "-Source",
        "local",
        "-RepoDir",
        str(repo_dir),
    ]
    if no_deps:
        command.append("-NoDeps")
    return subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _powershell_uninstall(
    skills: Path, agents: Path, *, executable: str = "pwsh"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            executable,
            "-NoProfile",
            "-File",
            str(ROOT / "uninstall.ps1"),
            "-Target",
            "claude",
            "-SkillDir",
            str(skills),
            "-AgentDir",
            str(agents),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )




def _minimal_distribution(path: Path, *, with_scripts: bool = False) -> Path:
    (path / "ads/references").mkdir(parents=True)
    (path / "ads/SKILL.md").write_text("---\nname: ads\n---\n", encoding="utf-8")
    (path / "skills/ads-demo").mkdir(parents=True)
    (path / "skills/ads-demo/SKILL.md").write_text(
        "---\nname: ads-demo\n---\n", encoding="utf-8"
    )
    (path / "agents").mkdir()
    (path / "agents/legacy-agent.md").write_text("legacy\n", encoding="utf-8")
    (path / "control-plane").mkdir()
    (path / "control-plane/README.md").write_text(
        "# Runtime resource fixture\n", encoding="utf-8"
    )
    (path / "control-plane/runtime-resources.txt").write_text(
        "control-plane/README.md\n", encoding="utf-8"
    )
    if with_scripts:
        (path / "scripts").mkdir()
        (path / "scripts/tool.py").write_text("VALUE = 1\n", encoding="utf-8")
        (path / "requirements.txt").write_text("example>=1\n", encoding="utf-8")
        (path / "requirements.lock").write_text(
            "example==1 --hash=sha256:" + "0" * 64 + "\n", encoding="utf-8"
        )
        (path / "claude_ads_core/adapters").mkdir(parents=True)
        (path / "claude_ads_core/schemas/v1").mkdir(parents=True)
        (path / "claude_ads_core/__init__.py").write_text("", encoding="utf-8")
        (path / "claude_ads_core/adapters/__init__.py").write_text("", encoding="utf-8")
        (path / "claude_ads_core/schemas/v1/sample.json").write_text(
            "{}\n", encoding="utf-8"
        )
    return path


def test_minimal_distribution_declares_real_runtime_resources(tmp_path):
    source = _minimal_distribution(tmp_path / "distribution")
    entries = [
        line
        for line in (source / "control-plane/runtime-resources.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line and not line.startswith("#")
    ]

    assert entries
    assert all((source / entry).is_file() for entry in entries)
    assert all(
        (source / entry).resolve().is_relative_to(source.resolve()) for entry in entries
    )


def _tree_snapshot(*roots: Path) -> dict[str, tuple[str, bytes]]:
    snapshot: dict[str, tuple[str, bytes]] = {}
    for root in roots:
        if not root.exists():
            snapshot[str(root)] = ("missing", b"")
            continue
        for path in [root, *sorted(root.rglob("*"))]:
            kind = "symlink" if path.is_symlink() else "directory" if path.is_dir() else "file"
            payload = path.read_bytes() if kind == "file" else b""
            snapshot[str(path)] = (kind, payload)
    return snapshot


@BASH_INSTALLER_ONLY
def test_bash_late_collision_fails_before_any_destination_mutation(tmp_path):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    skills.mkdir()
    agents.mkdir()
    manifest = skills / ".claude-ads-claude.manifest"
    manifest.write_text("V\t1\nT\tclaude\n", encoding="utf-8")
    late_agent = agents / sorted((ROOT / "agents").glob("*.md"))[-1].name
    late_agent.write_text("user-owned\n", encoding="utf-8")
    before = _tree_snapshot(skills, agents)

    result = _run(
        "install.sh", "--target=claude", "--source=local", "--no-deps",
        f"--skill-dir={skills}", f"--agent-dir={agents}",
    )

    assert result.returncode != 0
    assert "Refusing to overwrite unowned file" in result.stderr
    assert _tree_snapshot(skills, agents) == before


@pytest.mark.parametrize(
    "manifest_rows",
    [
        "F\t{file}\n",
        "V\t2\nT\tclaude\nF\t{file}\n",
        "V\t1\nT\tcodex\nF\t{file}\n",
        "V\t1\nT\tclaude\nF\t{file}\nF\t{file}\n",
        "V\t1\nV\t1\nT\tclaude\nF\t{file}\n",
        "T\tclaude\nV\t1\nF\t{file}\n",
    ],
    ids=["missing-headers", "wrong-version", "wrong-target", "duplicate-path", "duplicate-header", "reordered-headers"],
)
@BASH_INSTALLER_ONLY
def test_bash_install_rejects_forged_manifest_authority(tmp_path, manifest_rows):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    main_skill = skills / "ads/SKILL.md"
    main_skill.parent.mkdir(parents=True)
    main_skill.write_text("user-owned\n", encoding="utf-8")
    manifest = skills / ".claude-ads-claude.manifest"
    manifest.write_text(manifest_rows.format(file=main_skill.resolve()), encoding="utf-8")
    before = _tree_snapshot(skills, agents)

    result = _run(
        "install.sh", "--target=claude", "--source=local", "--no-deps",
        f"--skill-dir={skills}", f"--agent-dir={agents}",
    )

    assert result.returncode != 0
    assert _tree_snapshot(skills, agents) == before


@pytest.mark.parametrize(
    "manifest_rows",
    [
        "F\t{file}\n",
        "V\t2\nT\tclaude\nF\t{file}\n",
        "V\t1\nT\tcodex\nF\t{file}\n",
        "V\t1\nT\tclaude\nF\t{file}\nF\t{file}\n",
        "V\t1\nV\t1\nT\tclaude\nF\t{file}\n",
        "T\tclaude\nV\t1\nF\t{file}\n",
    ],
    ids=["missing-headers", "wrong-version", "wrong-target", "duplicate-path", "duplicate-header", "reordered-headers"],
)
@BASH_INSTALLER_ONLY
def test_bash_uninstall_rejects_invalid_manifest_identity(tmp_path, manifest_rows):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    main_skill = skills / "ads/SKILL.md"
    main_skill.parent.mkdir(parents=True)
    agents.mkdir()
    main_skill.write_text("owned\n", encoding="utf-8")
    manifest = skills / ".claude-ads-claude.manifest"
    manifest.write_text(manifest_rows.format(file=main_skill.resolve()), encoding="utf-8")
    before = _tree_snapshot(skills, agents)

    result = _run(
        "uninstall.sh", "--target=claude",
        f"--skill-dir={skills}", f"--agent-dir={agents}",
    )

    assert result.returncode != 0
    assert _tree_snapshot(skills, agents) == before


@BASH_INSTALLER_ONLY
def test_bash_repeat_preserves_dropped_owned_file_for_uninstall(tmp_path):
    source = _minimal_distribution(tmp_path / "distribution")
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    first = _run(
        "install.sh", "--target=claude", "--source=local", "--no-deps",
        f"--repo-dir={source}", f"--skill-dir={skills}", f"--agent-dir={agents}",
    )
    assert first.returncode == 0, first.stdout + first.stderr
    installed_legacy = agents / "legacy-agent.md"
    assert installed_legacy.is_file()
    (source / "agents/legacy-agent.md").unlink()

    repeat = _run(
        "install.sh", "--target=claude", "--source=local", "--no-deps",
        f"--repo-dir={source}", f"--skill-dir={skills}", f"--agent-dir={agents}",
    )
    assert repeat.returncode == 0, repeat.stdout + repeat.stderr
    manifest = (skills / ".claude-ads-claude.manifest").read_text(encoding="utf-8")
    assert f"F\t{installed_legacy.resolve()}\n" in manifest

    uninstall = _run(
        "uninstall.sh", "--target=claude",
        f"--skill-dir={skills}", f"--agent-dir={agents}",
    )
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not installed_legacy.exists()


@pytest.mark.parametrize(
    "missing",
    ["main-skill", "sub-skill", "requirements", "core-tree", "runtime-resource"],
)
@BASH_INSTALLER_ONLY
def test_bash_missing_planned_source_fails_without_destination_mutation(tmp_path, missing):
    source = _minimal_distribution(tmp_path / "distribution", with_scripts=True)
    if missing == "main-skill":
        (source / "ads/SKILL.md").unlink()
    elif missing == "sub-skill":
        (source / "skills/ads-demo/SKILL.md").unlink()
    elif missing == "requirements":
        (source / "requirements.txt").unlink()
    elif missing == "core-tree":
        shutil.rmtree(source / "claude_ads_core/adapters")
    else:
        (source / "control-plane/runtime-resources.txt").write_text(
            "control-plane/missing.json\n", encoding="utf-8"
        )
    skills, agents = tmp_path / "skills", tmp_path / "agents"

    result = _run(
        "install.sh", "--target=claude", "--source=local", "--no-deps",
        f"--repo-dir={source}", f"--skill-dir={skills}", f"--agent-dir={agents}",
    )

    assert result.returncode != 0
    assert not skills.exists()
    assert not agents.exists()


@POWERSHELL_ONLY
def test_powershell_missing_planned_source_fails_without_destination_mutation(tmp_path):
    source = _minimal_distribution(tmp_path / "distribution", with_scripts=True)
    (source / "requirements.txt").unlink()
    skills, agents = tmp_path / "skills", tmp_path / "agents"

    result = _powershell_install(skills, agents, repo_dir=source)

    assert result.returncode != 0
    assert not skills.exists()
    assert not agents.exists()


@BASH_INSTALLER_ONLY
def test_bash_installer_syntax_and_no_global_pip_escape_hatch():
    for script in ("install.sh", "uninstall.sh"):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / script)], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr

    installer = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "--break-system-packages" not in installer
    assert "curl -fsSL" not in installer
    assert "python3 -m venv" in installer
    assert "--require-hashes --only-binary=:all:" in installer
    assert "-m pip check" in installer
    assert "requirements.lock" in installer
    assert "--report" in installer
    assert "write_install_receipt.py" in installer
    assert "managed-runtime-receipt.json" in installer
    assert "control-plane/runtime-resources.txt" in installer
    assert 'verify_managed_install.py" ] && continue' in installer
    assert "banana-claude" not in installer
    assert LEGACY_INSTALL_MESSAGE in installer

    powershell = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert LEGACY_INSTALL_MESSAGE in powershell
    assert "--require-hashes --only-binary=:all:" in powershell
    assert "-m pip check" in powershell
    assert "requirements.lock" in powershell
    assert "--report" in powershell
    assert "write_install_receipt.py" in powershell
    assert "managed-runtime-receipt.json" in powershell
    assert "control-plane\\runtime-resources.txt" in powershell
    assert "banana-claude" not in powershell
    assert "Read-ValidPriorManifest" in powershell
    assert "Assert-ConfiguredDestination" in powershell
    assert "Assert-NoReparseChain" in powershell
    assert "Assert-CurrentUserOwnedFile" in powershell
    assert "Get-CompatibleRelativePath" in powershell
    assert "[System.IO.Path]::GetRelativePath" not in powershell
    assert "Get-NormalizedInstallRoot" in powershell
    assert "System.IO.File]::GetAccessControl" in powershell
    assert "System.IO.FileSystemAclExtensions]::GetAccessControl" in powershell
    assert "Get-Acl" not in powershell
    assert "Refusing to overwrite unowned file" in powershell
    assert "Missing or reparse-point install source" in powershell
    assert 'Name -ne "verify_managed_install.py"' in powershell
    assert "Bash ownership manifest detected" in powershell
    assert "-band [IO.FileAttributes]::ReparsePoint" in powershell
    assert powershell.count("Copy-Item") == 1

    powershell_uninstall = (ROOT / "uninstall.ps1").read_text(encoding="utf-8")
    assert "ExpectedProperties" in powershell_uninstall
    assert "Duplicate ownership-manifest path" in powershell_uninstall
    assert "Assert-SafeRecursiveTree" in powershell_uninstall
    assert "Refusing reparse-point uninstall path" in powershell_uninstall
    assert "System.IO.File]::GetAccessControl" in powershell_uninstall
    assert "System.IO.FileSystemAclExtensions]::GetAccessControl" in powershell_uninstall
    assert "Get-Acl" not in powershell_uninstall


@BASH_INSTALLER_ONLY
def test_manifest_owned_uninstall_preserves_unrelated_ads_skill(tmp_path):
    skills, agents = _install(tmp_path)
    assert (skills / "ads" / "requirements.lock").is_file()
    installed_resources = [skills / "ads" / relative for relative in _runtime_resources()]
    assert all(path.is_file() for path in installed_resources)
    unrelated = skills / "ads-user-owned"
    unrelated.mkdir()
    (unrelated / "SKILL.md").write_text("user data", encoding="utf-8")

    result = _run(
        "uninstall.sh",
        "--target=claude",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (skills / "ads" / "SKILL.md").exists()
    assert not (skills / "ads" / "requirements.lock").exists()
    assert not any(path.exists() for path in installed_resources)
    assert unrelated.joinpath("SKILL.md").read_text(encoding="utf-8") == "user data"
    assert not (skills / ".claude-ads-claude.manifest").exists()


@BASH_INSTALLER_ONLY
def test_installer_includes_portable_interface_and_all_platform_surfaces(tmp_path):
    skills, agents = _install(tmp_path)
    assert (skills / "ads" / "agents" / "openai.yaml").is_file()
    for platform in (
        "google", "meta", "youtube", "linkedin", "tiktok", "microsoft",
        "apple", "amazon", "reddit", "pinterest", "snapchat", "x",
    ):
        assert (skills / f"ads-{platform}" / "SKILL.md").is_file()
        assert (agents / f"audit-{platform}.md").is_file()


@BASH_INSTALLER_ONLY
@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (["control-plane/../private.json"], "Unsafe runtime resource path"),
        (
            [
                "control-plane/README.md",
                "control-plane/readme.md",
            ],
            "Duplicate runtime resource path",
        ),
    ],
)
def test_runtime_resource_allowlist_fails_before_install_mutation(
    tmp_path, entries, message
):
    source = tmp_path / "source"
    (source / "ads").mkdir(parents=True)
    (source / "skills").mkdir()
    (source / "control-plane").mkdir()
    (source / "ads/SKILL.md").write_text("test skill\n", encoding="utf-8")
    (source / "control-plane/README.md").write_text("public\n", encoding="utf-8")
    (source / "control-plane/runtime-resources.txt").write_text(
        "\n".join(entries) + "\n", encoding="utf-8"
    )
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"

    result = _run(
        "install.sh",
        "--target=claude",
        "--source=local",
        "--no-deps",
        f"--repo-dir={source}",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )

    assert result.returncode != 0
    assert message in result.stderr
    assert not skills.exists()
    assert not agents.exists()


@BASH_INSTALLER_ONLY
def test_installer_copies_only_curated_runtime_resources_with_ownership(tmp_path):
    skills, _agents = _install(tmp_path)
    skill_root = skills / "ads"
    manifest = (skills / ".claude-ads-claude.manifest").read_text(encoding="utf-8")
    expected = _runtime_resources()

    assert len(expected) == len(set(expected))
    for relative in expected:
        source = ROOT / relative
        installed = skill_root / relative
        assert installed.read_bytes() == source.read_bytes()
        assert f"F\t{installed.resolve()}\n" in manifest

    installed_files = {
        path.relative_to(skill_root).as_posix()
        for path in (skill_root / "control-plane").rglob("*")
        if path.is_file()
    }
    assert installed_files == set(expected)


@BASH_INSTALLER_ONLY
def test_installed_runtime_resolves_public_policy_from_arbitrary_cwd(tmp_path):
    skills, _agents = _install(tmp_path)
    skill_root = skills / "ads"
    assert not (skill_root / "scripts/verify_managed_install.py").exists()
    elsewhere = tmp_path / "arbitrary-cwd"
    elsewhere.mkdir()
    findings = elsewhere / "empty-findings.json"
    findings.write_text("[]\n", encoding="utf-8")
    environment = {**os.environ, "PYTHONPATH": str(skill_root / "scripts")}

    def run_core(*arguments: str) -> dict:
        result = subprocess.run(
            [os.sys.executable, "-m", "claude_ads_core", *arguments],
            cwd=elsewhere,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    status = run_core("status", "--as-of", "2026-10-07")
    assert status["as_of"] == "2026-10-07"
    assert "next_blocker" in status
    next_blocker = run_core("next", "--as-of", "2026-10-07")
    assert next_blocker["as_of"] == "2026-10-07"
    assert "next_blocker" in next_blocker
    score = run_core("score", "--platform", "google", "--findings", str(findings))
    assert score["health_score"] is None
    assert score["evidence_coverage"] == 0.0
    assert score["status"] == "insufficient_evidence"
    assert score["categories"] == []
    explicit = run_core(
        "score", "--platform", "google", "--findings", str(findings),
        "--policy-root", str(skill_root),
    )
    assert explicit == score

    schema_path = skill_root / "control-plane/schemas/creative-worker-result.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema_id = schema["$id"]
    assert schema_id == (
        "urn:ai-marketing-hub:claude-ads:schema:control:v1:"
        "creative-worker-result.v1.json"
    )
    from referencing import Registry, Resource

    registry = Registry().with_resource(schema_id, Resource.from_contents(schema))
    assert registry.contents(schema_id) == schema


@BASH_INSTALLER_ONLY
def test_managed_runtime_bytecode_is_owned_selectively_across_repeat_and_uninstall(
    tmp_path,
):
    skills, agents, environment = _managed_install(tmp_path)
    skill_root = skills / "ads"
    interpreter = skill_root / ".venv/bin/python"
    elsewhere = tmp_path / "arbitrary-cwd"
    elsewhere.mkdir()
    runtime_environment = os.environ.copy()
    runtime_environment.pop("PYTHONDONTWRITEBYTECODE", None)

    for command in ("status", "next"):
        result = subprocess.run(
            [str(interpreter), "-m", "claude_ads_core", command, "--as-of", "2026-10-07"],
            cwd=elsewhere,
            env=runtime_environment,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(result.stdout)["as_of"] == "2026-10-07"

    core_cache = skill_root / "scripts/claude_ads_core/__pycache__"
    adapter_cache = skill_root / "scripts/claude_ads_core/adapters/__pycache__"
    generated = sorted(core_cache.glob("*.pyc")) + sorted(adapter_cache.glob("*.pyc"))
    assert generated
    manifest = (skills / ".claude-ads-claude.manifest").read_text(encoding="utf-8")
    assert f"B\t{core_cache.resolve()}\n" in manifest
    assert f"B\t{adapter_cache.resolve()}\n" in manifest

    cache_sentinel = core_cache / "user-owned.txt"
    cache_sentinel.write_text("preserve cache content\n", encoding="utf-8")
    unknown_pyc = core_cache / f"unrelated.{sys.implementation.cache_tag}.pyc"
    unknown_pyc.write_bytes(b"preserve unrelated bytecode name\n")
    sibling_cache = skill_root / "scripts/user-owned/__pycache__"
    sibling_cache.mkdir(parents=True)
    sibling_sentinel = sibling_cache / f"module.{sys.implementation.cache_tag}.pyc"
    sibling_sentinel.write_bytes(b"preserve sibling cache\n")
    unrelated_skill = skills / "ads-weather/keep.txt"
    unrelated_skill.parent.mkdir()
    unrelated_skill.write_text("preserve unrelated skill\n", encoding="utf-8")

    repeat = subprocess.run(
        [
            "bash",
            str(ROOT / "install.sh"),
            "--target=claude",
            "--source=local",
            f"--skill-dir={skills}",
            f"--agent-dir={agents}",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert repeat.returncode == 0, repeat.stdout + repeat.stderr
    assert cache_sentinel.read_text(encoding="utf-8") == "preserve cache content\n"
    assert unknown_pyc.read_bytes() == b"preserve unrelated bytecode name\n"

    uninstall = _run(
        "uninstall.sh",
        "--target=claude",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert all(not path.exists() for path in generated)
    assert cache_sentinel.read_text(encoding="utf-8") == "preserve cache content\n"
    assert unknown_pyc.read_bytes() == b"preserve unrelated bytecode name\n"
    assert sibling_sentinel.read_bytes() == b"preserve sibling cache\n"
    assert unrelated_skill.read_text(encoding="utf-8") == "preserve unrelated skill\n"
    assert not adapter_cache.exists()
    assert not (skills / ".claude-ads-claude.manifest").exists()


@BASH_INSTALLER_ONLY
@pytest.mark.parametrize("operation", ["repeat", "uninstall"])
def test_bash_rejects_bytecode_authority_outside_exact_package_roots(
    tmp_path, operation
):
    skills, agents = _install(tmp_path)
    unsafe_cache = skills / "ads/scripts/user-owned/__pycache__"
    unsafe_cache.mkdir(parents=True)
    sentinel = unsafe_cache / "keep.txt"
    sentinel.write_text("user-owned\n", encoding="utf-8")
    manifest = skills / ".claude-ads-claude.manifest"
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(f"B\t{unsafe_cache.resolve()}\n")
    before = _tree_snapshot(skills, agents)

    arguments = [
        "--target=claude",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    ]
    if operation == "repeat":
        arguments += ["--source=local", "--no-deps"]
    result = _run("install.sh" if operation == "repeat" else "uninstall.sh", *arguments)

    assert result.returncode != 0
    assert _tree_snapshot(skills, agents) == before


@BASH_INSTALLER_ONLY
def test_tampered_manifest_fails_before_removing_files(tmp_path):
    skills, agents = _install(tmp_path)
    manifest = skills / ".claude-ads-claude.manifest"
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(f"F\t{tmp_path.parent / 'outside.txt'}\n")

    result = _run(
        "uninstall.sh",
        "--target=claude",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )
    assert result.returncode != 0
    assert "Unsafe ownership-manifest path" in result.stderr
    assert (skills / "ads" / "SKILL.md").exists()


@BASH_INSTALLER_ONLY
def test_bash_uninstall_rejects_symlinked_manifest_before_any_mutation(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    victim = skills / "ads/SKILL.md"
    victim.parent.mkdir(parents=True)
    agents.mkdir()
    victim.write_text("preserve owned-looking file\n", encoding="utf-8")
    external_manifest = tmp_path / "external.manifest"
    external_manifest.write_text(
        f"V\t1\nT\tclaude\nF\t{victim.resolve()}\n",
        encoding="utf-8",
    )
    manifest = skills / ".claude-ads-claude.manifest"
    manifest.symlink_to(external_manifest)
    before = _tree_snapshot(skills, agents)
    external_before = external_manifest.read_bytes()

    result = _run(
        "uninstall.sh",
        "--target=claude",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )

    assert result.returncode != 0
    assert _tree_snapshot(skills, agents) == before
    assert external_manifest.read_bytes() == external_before
    assert "Ownership manifest not found or unsafe" in result.stderr


@BASH_INSTALLER_ONLY
def test_installer_refuses_symlink_escape(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    outside = tmp_path / "outside"
    skills.mkdir()
    outside.mkdir()
    (skills / "ads").symlink_to(outside, target_is_directory=True)

    result = _run(
        "install.sh",
        "--target=claude",
        "--source=local",
        "--no-deps",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )
    assert result.returncode != 0
    assert "Refusing symlinked install directory" in result.stderr
    assert not (outside / "SKILL.md").exists()


@BASH_INSTALLER_ONLY
def test_unsupported_python_fails_before_any_destination_mutation(tmp_path):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    fake_bin = _fake_python(tmp_path, "cpython|3.14|linux|x86_64")
    result = subprocess.run(
        ["bash", str(ROOT / "install.sh"), "--target=claude", "--source=local", f"--skill-dir={skills}", f"--agent-dir={agents}"],
        cwd=ROOT, env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "No verified dependency lock target" in result.stderr
    assert not skills.exists()
    assert not agents.exists()


@BASH_INSTALLER_ONLY
def test_windows_bash_install_redirects_to_powershell_before_mutation(tmp_path):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    fake_bin = _fake_python(
        tmp_path, "cpython|3.12|windows|amd64|none|none|unsupported"
    )
    result = subprocess.run(
        [
            "bash",
            str(ROOT / "install.sh"),
            "--target=claude",
            "--source=local",
            f"--skill-dir={skills}",
            f"--agent-dir={agents}",
        ],
        cwd=ROOT,
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Use install.ps1" in result.stderr
    assert not skills.exists()
    assert not agents.exists()


@BASH_INSTALLER_ONLY
def test_bash_installer_rejects_powershell_manifest_before_mutation(tmp_path):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    main_skill = skills / "ads" / "SKILL.md"
    main_skill.parent.mkdir(parents=True)
    main_skill.write_text("power-shell-owned\n", encoding="utf-8")
    manifest = skills / ".claude-ads-claude.manifest.json"
    manifest.write_text('{"version":1}\n', encoding="utf-8")

    result = _run(
        "install.sh",
        "--target=claude",
        "--source=local",
        "--no-deps",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )

    assert result.returncode != 0
    assert "PowerShell ownership manifest detected" in result.stderr
    assert main_skill.read_text(encoding="utf-8") == "power-shell-owned\n"
    assert not agents.exists()


@BASH_INSTALLER_ONLY
def test_bash_installer_reports_legacy_install_once_before_mutation(tmp_path):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    # v1.x installers copied files without writing any ownership manifest.
    main_skill = skills / "ads" / "SKILL.md"
    main_skill.parent.mkdir(parents=True)
    main_skill.write_text("legacy v1 skill\n", encoding="utf-8")
    sub_skill = skills / "ads-google" / "SKILL.md"
    sub_skill.parent.mkdir(parents=True)
    sub_skill.write_text("legacy v1 sub-skill\n", encoding="utf-8")
    agent_name = sorted((ROOT / "agents").glob("*.md"))[0].name
    agent_file = agents / agent_name
    agent_file.parent.mkdir(parents=True)
    agent_file.write_text("legacy v1 agent\n", encoding="utf-8")

    result = _run(
        "install.sh",
        "--target=claude",
        "--source=local",
        "--no-deps",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )

    assert result.returncode == 1
    assert result.stderr.count("✗") == 1
    assert LEGACY_INSTALL_MESSAGE in result.stderr
    assert "Refusing to overwrite unowned file" not in result.stderr
    assert "older than v2.0.0" in result.stderr
    assert str(main_skill) in result.stderr
    assert str(agent_file) in result.stderr
    assert f"{skills / 'ads-google'}/" in result.stderr
    assert str(skills / ".claude-ads-claude.manifest") in result.stderr
    assert main_skill.read_text(encoding="utf-8") == "legacy v1 skill\n"
    assert sub_skill.read_text(encoding="utf-8") == "legacy v1 sub-skill\n"
    assert agent_file.read_text(encoding="utf-8") == "legacy v1 agent\n"
    assert not (skills / "ads" / "references").exists()
    assert not (skills / ".claude-ads-claude.manifest").exists()


@BASH_INSTALLER_ONLY
def test_bash_installer_upgrades_managed_install_in_place(tmp_path):
    skills, agents = _install(tmp_path)
    installed_main = skills / "ads" / "SKILL.md"
    expected_main = (ROOT / "ads" / "SKILL.md").read_text(encoding="utf-8")
    installed_main.write_text("stale owned content\n", encoding="utf-8")
    installed_agent = sorted(agents.glob("*.md"))[0]
    expected_agent = (ROOT / "agents" / installed_agent.name).read_text(encoding="utf-8")
    installed_agent.write_text("stale owned agent\n", encoding="utf-8")

    repeat = _run(
        "install.sh",
        "--target=claude",
        "--source=local",
        "--no-deps",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )

    assert repeat.returncode == 0, repeat.stdout + repeat.stderr
    assert LEGACY_INSTALL_MESSAGE not in repeat.stderr
    assert installed_main.read_text(encoding="utf-8") == expected_main
    assert installed_agent.read_text(encoding="utf-8") == expected_agent
    assert (skills / ".claude-ads-claude.manifest").is_file()


def _owned_stdlib_venv(skills: Path) -> Path:
    if sys.version_info[:2] not in {(3, 11), (3, 12)}:
        pytest.skip("Managed venv layouts are declared for CPython 3.11 and 3.12")
    environment = skills / "ads" / ".venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(environment)],
        check=True, capture_output=True, text=True,
    )
    with (skills / ".claude-ads-claude.manifest").open("a", encoding="utf-8") as manifest:
        manifest.write(f"R\t{environment.resolve()}\n")
    return environment


@BASH_INSTALLER_ONLY
def test_bash_stdlib_venv_links_allow_repeat_install_and_uninstall(tmp_path):
    skills, agents = _install(tmp_path)
    environment = _owned_stdlib_venv(skills)
    interpreter = (environment / "bin/python").resolve()
    unrelated = skills / "ads-weather" / "keep.txt"
    unrelated.parent.mkdir()
    unrelated.write_text("unrelated skill\n", encoding="utf-8")

    repeat = _run(
        "install.sh", "--target=claude", "--source=local", "--no-deps",
        f"--skill-dir={skills}", f"--agent-dir={agents}",
    )
    assert repeat.returncode == 0, repeat.stdout + repeat.stderr
    assert environment.is_dir()
    uninstall = _run(
        "uninstall.sh", "--target=claude",
        f"--skill-dir={skills}", f"--agent-dir={agents}",
    )
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not environment.exists()
    assert interpreter.is_file()
    assert unrelated.read_text(encoding="utf-8") == "unrelated skill\n"


@BASH_INSTALLER_ONLY
@pytest.mark.parametrize("operation", ["repeat", "uninstall"])
@pytest.mark.parametrize("link_path", ["lib64", "share/escape", "bin/python3"])
def test_bash_managed_venv_rejects_unexpected_links_before_mutation(
    tmp_path, operation, link_path,
):
    skills, agents = _install(tmp_path)
    environment = _owned_stdlib_venv(skills)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("outside sentinel\n", encoding="utf-8")
    link = environment / link_path
    link.parent.mkdir(parents=True, exist_ok=True)
    link.unlink(missing_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    before = _tree_snapshot(skills, agents, outside)
    arguments = ["--target=claude", f"--skill-dir={skills}", f"--agent-dir={agents}"]
    if operation == "repeat":
        arguments += ["--source=local", "--no-deps"]
    result = _run("install.sh" if operation == "repeat" else "uninstall.sh", *arguments)
    assert result.returncode != 0
    assert _tree_snapshot(skills, agents, outside) == before


@BASH_INSTALLER_ONLY
@pytest.mark.parametrize("interpreter_kind", ["symlink", "copy"])
def test_bash_managed_repeat_rejects_forged_interpreter_before_execution(
    tmp_path, interpreter_kind,
):
    skills, agents = _install(tmp_path)
    environment = _owned_stdlib_venv(skills)
    marker = tmp_path / "forged-interpreter-ran"
    forged = tmp_path / "forged-python"
    forged.write_text(
        f"#!/bin/sh\ntouch {shlex.quote(str(marker))}\nexit 0\n", encoding="utf-8"
    )
    forged.chmod(0o755)
    interpreter = environment / "bin/python"
    interpreter.unlink()
    if interpreter_kind == "symlink":
        interpreter.symlink_to(forged)
    else:
        shutil.copy2(forged, interpreter)
    before = _tree_snapshot(skills, agents)
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    fake_bin = _fake_python(
        tmp_path,
        f"cpython|{python_version}|linux|x86_64|glibc|2.43|supported",
    )
    result = subprocess.run(
        ["bash", str(ROOT / "install.sh"), "--target=claude", "--source=local",
         f"--skill-dir={skills}", f"--agent-dir={agents}"],
        cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"},
    )
    assert result.returncode != 0
    assert "managed interpreter" in result.stdout + result.stderr
    assert not marker.exists()
    assert _tree_snapshot(skills, agents) == before


@BASH_INSTALLER_ONLY
def test_musl_linux_fails_before_any_destination_mutation(tmp_path):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    fake_bin = _fake_python(tmp_path, "cpython|3.12|linux|x86_64|musl|1.2.5|unsupported")
    result = subprocess.run(
        ["bash", str(ROOT / "install.sh"), "--target=claude", "--source=local", f"--skill-dir={skills}", f"--agent-dir={agents}"],
        cwd=ROOT, env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "musl Linux is unsupported" in result.stderr
    assert not skills.exists()
    assert not agents.exists()


@BASH_INSTALLER_ONLY
def test_dependency_failure_leaves_complete_ownership_manifest_for_uninstall(tmp_path):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    stale_receipt = skills / "ads" / "managed-runtime-receipt.json"
    stale_receipt.parent.mkdir(parents=True)
    stale_receipt.write_text('{"stale": true}\n', encoding="utf-8")
    (skills / ".claude-ads-claude.manifest").write_text(
        f"V\t1\nT\tclaude\nF\t{stale_receipt.resolve()}\n",
        encoding="utf-8",
    )
    fake_bin = _fake_python(tmp_path, "cpython|3.12|linux|x86_64", fail_venv=True)
    result = subprocess.run(
        ["bash", str(ROOT / "install.sh"), "--target=claude", "--source=local", f"--skill-dir={skills}", f"--agent-dir={agents}"],
        cwd=ROOT, env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert (skills / ".claude-ads-claude.manifest").is_file()
    assert (skills / "ads" / "requirements.lock").is_file()
    assert not stale_receipt.exists()
    uninstall = _run("uninstall.sh", "--target=claude", f"--skill-dir={skills}", f"--agent-dir={agents}")
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not (skills / "ads" / "requirements.lock").exists()


@BASH_INSTALLER_ONLY
def test_manifest_traversal_is_rejected_before_removal(tmp_path):
    skills, agents = _install(tmp_path)
    manifest = skills / ".claude-ads-claude.manifest"
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(f"F\t{skills / 'ads' / '..' / '..' / 'outside.txt'}\n")

    result = _run(
        "uninstall.sh",
        "--target=claude",
        f"--skill-dir={skills}",
        f"--agent-dir={agents}",
    )
    assert result.returncode != 0
    assert (skills / "ads" / "SKILL.md").exists()


@POWERSHELL_ONLY
@pytest.mark.parametrize("script", ["install.ps1", "uninstall.ps1"])
def test_powershell_scripts_parse(script):
    command = f"[void][scriptblock]::Create((Get-Content -Raw '{ROOT / script}'))"
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@POWERSHELL_ONLY
def test_powershell_installer_rejects_unowned_main_file_before_any_mutation(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    main_skill = skills / "ads" / "SKILL.md"
    main_skill.parent.mkdir(parents=True)
    main_skill.write_text("user-owned\n", encoding="utf-8")
    # A valid manifest that owns nothing keeps this on the per-file guard
    # rather than the legacy-install preflight.
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest_path.write_text(json.dumps(EMPTY_POWERSHELL_MANIFEST), encoding="utf-8")

    install = _powershell_install(skills, agents)

    assert install.returncode != 0
    assert "Refusing to overwrite unowned file" in install.stdout + install.stderr
    assert main_skill.read_text(encoding="utf-8") == "user-owned\n"
    assert not (skills / "ads" / "references").exists()
    assert not agents.exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == EMPTY_POWERSHELL_MANIFEST


@POWERSHELL_ONLY
def test_powershell_installer_reports_legacy_install_once_before_mutation(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    main_skill = skills / "ads" / "SKILL.md"
    main_skill.parent.mkdir(parents=True)
    main_skill.write_text("legacy v1 skill\n", encoding="utf-8")
    agent_name = sorted((ROOT / "agents").glob("*.md"))[0].name
    agent_file = agents / agent_name
    agent_file.parent.mkdir(parents=True)
    agent_file.write_text("legacy v1 agent\n", encoding="utf-8")

    install = _powershell_install(skills, agents)

    output = install.stdout + install.stderr
    assert install.returncode != 0
    assert output.count(LEGACY_INSTALL_MESSAGE) == 1
    assert "Refusing to overwrite unowned file" not in output
    assert "older than v2.0.0" in output
    assert str(main_skill.resolve()) in output
    assert str(agent_file.resolve()) in output
    assert str((skills / ".claude-ads-claude.manifest.json").resolve()) in output
    assert main_skill.read_text(encoding="utf-8") == "legacy v1 skill\n"
    assert agent_file.read_text(encoding="utf-8") == "legacy v1 agent\n"
    assert not (skills / "ads" / "references").exists()
    assert not (skills / ".claude-ads-claude.manifest.json").exists()


@POWERSHELL_ONLY
def test_powershell_installer_rejects_bash_manifest_before_any_mutation(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    main_skill = skills / "ads" / "SKILL.md"
    main_skill.parent.mkdir(parents=True)
    main_skill.write_text("bash-owned\n", encoding="utf-8")
    (skills / ".claude-ads-claude.manifest").write_text(
        "F|/bash-owned-placeholder\n", encoding="utf-8"
    )

    install = _powershell_install(skills, agents)

    assert install.returncode != 0
    assert "Bash ownership manifest detected" in install.stdout + install.stderr
    assert main_skill.read_text(encoding="utf-8") == "bash-owned\n"
    assert not agents.exists()
    assert not (skills / ".claude-ads-claude.manifest.json").exists()


@POWERSHELL_ONLY
def test_powershell_installer_preflights_late_agent_collision_before_skill_mutation(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agent_name = next((ROOT / "agents").glob("*.md")).name
    agent_file = agents / agent_name
    agent_file.parent.mkdir(parents=True)
    agent_file.write_text("user-owned agent\n", encoding="utf-8")
    # A valid manifest that owns nothing keeps this on the per-file guard
    # rather than the legacy-install preflight.
    skills.mkdir()
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest_path.write_text(json.dumps(EMPTY_POWERSHELL_MANIFEST), encoding="utf-8")

    install = _powershell_install(skills, agents)

    assert install.returncode != 0
    assert "Refusing to overwrite unowned file" in install.stdout + install.stderr
    assert agent_file.read_text(encoding="utf-8") == "user-owned agent\n"
    assert not (skills / "ads").exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == EMPTY_POWERSHELL_MANIFEST


@POWERSHELL_ONLY
def test_powershell_installer_invalid_manifest_cannot_authorize_overwrite(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    main_skill = skills / "ads" / "SKILL.md"
    main_skill.parent.mkdir(parents=True)
    main_skill.write_text("user-owned\n", encoding="utf-8")
    manifest = skills / ".claude-ads-claude.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "target": "claude",
                "files": [str(main_skill.resolve())],
                "directories": [str(tmp_path.parent / "outside")],
                "recursive_directories": [],
            }
        ),
        encoding="utf-8",
    )

    install = _powershell_install(skills, agents)

    assert install.returncode != 0
    assert "Install destination escapes configured roots" in install.stdout + install.stderr
    assert main_skill.read_text(encoding="utf-8") == "user-owned\n"
    assert not (skills / "ads" / "references").exists()
    assert not agents.exists()


@POWERSHELL_ONLY
@pytest.mark.parametrize(
    "invalid_case", ["cross-category-duplicate", "boolean-version", "configured-root"]
)
def test_powershell_installer_rejects_prior_manifest_uninstall_would_reject(
    tmp_path, invalid_case
):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    main_skill = skills / "ads" / "SKILL.md"
    main_skill.parent.mkdir(parents=True)
    main_skill.write_text("user-owned\n", encoding="utf-8")
    manifest = {
        "version": True if invalid_case == "boolean-version" else 1,
        "target": "claude",
        "files": [str(main_skill.resolve())],
        "directories": (
            [str(main_skill.resolve())]
            if invalid_case == "cross-category-duplicate"
            else ([str(skills.resolve())] if invalid_case == "configured-root" else [])
        ),
        "recursive_directories": [],
    }
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    install = _powershell_install(skills, agents)

    assert install.returncode != 0
    assert main_skill.read_text(encoding="utf-8") == "user-owned\n"
    assert not (skills / "ads" / "references").exists()
    assert not agents.exists()


@POWERSHELL_ONLY
def test_powershell_installer_rejects_reparse_destination(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    outside = tmp_path / "outside"
    skills.mkdir()
    outside.mkdir()
    try:
        (skills / "ads").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    install = _powershell_install(skills, agents)

    assert install.returncode != 0
    assert "reparse-point install path" in install.stdout + install.stderr
    assert not (outside / "SKILL.md").exists()
    assert not agents.exists()


@POWERSHELL_ONLY
def test_powershell_root_normalization_preserves_filesystem_root():
    command = r"""
$SourceText = Get-Content -LiteralPath $env:CLAUDE_ADS_INSTALLER -Raw
$SourceText = [regex]::Replace($SourceText, '(?m)^Main\s*$', '')
. ([scriptblock]::Create($SourceText))
$Root = [IO.Path]::GetPathRoot([IO.Path]::GetFullPath([IO.Path]::GetTempPath()))
$Normalized = Get-NormalizedInstallRoot $Root
if ($Normalized -ne $Root) { throw "filesystem root changed: $Root -> $Normalized" }
"""
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", command],
        env={**os.environ, "CLAUDE_ADS_INSTALLER": str(ROOT / "install.ps1")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@POWERSHELL_ONLY
def test_powershell_installer_rejects_overlapping_roots_before_mutation(tmp_path):
    skills = tmp_path / "shared"
    agents = skills / "ads"

    install = _powershell_install(skills, agents)

    assert install.returncode != 0
    assert "Skill and agent install roots must not overlap" in install.stdout + install.stderr
    assert not skills.exists()


@POWERSHELL_ONLY
@pytest.mark.skipif(os.name != "nt", reason="Managed PowerShell install target is Windows-only")
def test_powershell_installer_rejects_unowned_managed_environment_before_mutation(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    unowned_venv = skills / "ads" / ".venv"
    unowned_venv.mkdir(parents=True)
    sentinel = unowned_venv / "user.txt"
    sentinel.write_text("do not delete\n", encoding="utf-8")

    install = _powershell_install(skills, agents, no_deps=False)

    assert install.returncode != 0
    assert "Refusing to reuse unowned managed environment" in install.stdout + install.stderr
    assert sentinel.read_text(encoding="utf-8") == "do not delete\n"
    assert not (skills / "ads" / "SKILL.md").exists()
    assert not agents.exists()


@POWERSHELL_ONLY
def test_powershell_install_uninstall_round_trip_preserves_unrelated_skill(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    install = _powershell_install(skills, agents)
    assert install.returncode == 0, install.stdout + install.stderr
    assert (skills / "ads" / "SKILL.md").is_file()
    assert (skills / ".claude-ads-claude.manifest.json").is_file()

    # The exact path is now recorded by the validated prior manifest, so a
    # repeat install may replace it and must restore the distribution content.
    installed_main = skills / "ads" / "SKILL.md"
    expected_main = (ROOT / "ads" / "SKILL.md").read_text(encoding="utf-8")
    installed_main.write_text("stale owned content\n", encoding="utf-8")
    repeat = _powershell_install(skills, agents)
    assert repeat.returncode == 0, repeat.stdout + repeat.stderr
    assert installed_main.read_text(encoding="utf-8") == expected_main

    unrelated = skills / "ads-weather"
    unrelated.mkdir()
    unrelated.joinpath("SKILL.md").write_text("user-owned\n", encoding="utf-8")
    uninstall = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(ROOT / "uninstall.ps1"),
            "-Target",
            "claude",
            "-SkillDir",
            str(skills),
            "-AgentDir",
            str(agents),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not (skills / "ads").exists()
    assert unrelated.joinpath("SKILL.md").read_text(encoding="utf-8") == "user-owned\n"


@POWERSHELL_ONLY
def test_powershell_runtime_bytecode_is_owned_selectively_across_repeat_and_uninstall(
    tmp_path,
):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    install = _powershell_install(skills, agents)
    assert install.returncode == 0, install.stdout + install.stderr
    skill_root = skills / "ads"
    elsewhere = tmp_path / "arbitrary-cwd"
    elsewhere.mkdir()
    runtime_environment = {**os.environ, "PYTHONPATH": str(skill_root / "scripts")}
    runtime_environment.pop("PYTHONDONTWRITEBYTECODE", None)

    for command in ("status", "next"):
        result = subprocess.run(
            [sys.executable, "-m", "claude_ads_core", command, "--as-of", "2026-10-07"],
            cwd=elsewhere,
            env=runtime_environment,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(result.stdout)["as_of"] == "2026-10-07"

    core_cache = skill_root / "scripts/claude_ads_core/__pycache__"
    adapter_cache = skill_root / "scripts/claude_ads_core/adapters/__pycache__"
    generated = sorted(core_cache.glob("*.pyc")) + sorted(adapter_cache.glob("*.pyc"))
    assert generated
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    assert set(manifest["bytecode_directories"]) == {
        str(core_cache.resolve()),
        str(adapter_cache.resolve()),
    }

    cache_sentinel = core_cache / "user-owned.txt"
    cache_sentinel.write_text("preserve cache content\n", encoding="utf-8")
    unknown_pyc = core_cache / f"unrelated.{sys.implementation.cache_tag}.pyc"
    unknown_pyc.write_bytes(b"preserve unrelated bytecode name\n")
    sibling_cache = skill_root / "scripts/user-owned/__pycache__"
    sibling_cache.mkdir(parents=True)
    sibling_sentinel = sibling_cache / f"module.{sys.implementation.cache_tag}.pyc"
    sibling_sentinel.write_bytes(b"preserve sibling cache\n")

    repeat = _powershell_install(skills, agents)
    assert repeat.returncode == 0, repeat.stdout + repeat.stderr
    uninstall = _powershell_uninstall(skills, agents)
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert all(not path.exists() for path in generated)
    assert cache_sentinel.read_text(encoding="utf-8") == "preserve cache content\n"
    assert unknown_pyc.read_bytes() == b"preserve unrelated bytecode name\n"
    assert sibling_sentinel.read_bytes() == b"preserve sibling cache\n"
    assert not adapter_cache.exists()
    assert not manifest_path.exists()


@POWERSHELL_ONLY
def test_powershell_uninstall_accepts_legacy_five_property_manifest(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    owned = skills / "ads/SKILL.md"
    owned.parent.mkdir(parents=True)
    agents.mkdir()
    owned.write_text("owned\n", encoding="utf-8")
    manifest = {**EMPTY_POWERSHELL_MANIFEST, "files": [str(owned.resolve())]}
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    uninstall = _powershell_uninstall(skills, agents)

    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not owned.exists()
    assert not manifest_path.exists()


@POWERSHELL_ONLY
@pytest.mark.parametrize("operation", ["repeat", "uninstall"])
def test_powershell_rejects_bytecode_authority_outside_exact_package_roots(
    tmp_path, operation
):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    install = _powershell_install(skills, agents)
    assert install.returncode == 0, install.stdout + install.stderr
    unsafe_cache = skills / "ads/scripts/user-owned/__pycache__"
    unsafe_cache.mkdir(parents=True)
    sentinel = unsafe_cache / "keep.txt"
    sentinel.write_text("user-owned\n", encoding="utf-8")
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest["bytecode_directories"] = [str(unsafe_cache.resolve())]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    before = _tree_snapshot(skills, agents)

    result = (
        _powershell_install(skills, agents)
        if operation == "repeat"
        else _powershell_uninstall(skills, agents)
    )

    assert result.returncode != 0
    assert "Unsafe bytecode ownership root" in result.stdout + result.stderr
    assert _tree_snapshot(skills, agents) == before


@POWERSHELL_ONLY
def test_powershell_uninstall_rejects_duplicate_bytecode_authority(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    install = _powershell_install(skills, agents)
    assert install.returncode == 0, install.stdout + install.stderr
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest["directories"].append(manifest["bytecode_directories"][0])
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    before = _tree_snapshot(skills, agents)

    uninstall = _powershell_uninstall(skills, agents)

    assert uninstall.returncode != 0
    assert "Duplicate ownership-manifest path" in uninstall.stdout + uninstall.stderr
    assert _tree_snapshot(skills, agents) == before


@POWERSHELL_ONLY
@pytest.mark.parametrize("operation", ["repeat", "uninstall"])
def test_powershell_bytecode_root_reparse_is_rejected_before_mutation(
    tmp_path, operation
):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("outside\n", encoding="utf-8")
    install = _powershell_install(skills, agents)
    assert install.returncode == 0, install.stdout + install.stderr
    core_cache = skills / "ads/scripts/claude_ads_core/__pycache__"
    try:
        core_cache.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    before = _tree_snapshot(skills, agents, outside)

    result = (
        _powershell_install(skills, agents)
        if operation == "repeat"
        else _powershell_uninstall(skills, agents)
    )

    assert result.returncode != 0
    assert "reparse-point" in result.stdout + result.stderr
    assert _tree_snapshot(skills, agents, outside) == before


@POWERSHELL_ONLY
def test_powershell_installer_does_not_claim_preexisting_unowned_directories(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    references = skills / "ads" / "references"
    references.mkdir(parents=True)

    install = _powershell_install(skills, agents)
    assert install.returncode == 0, install.stdout + install.stderr
    manifest = json.loads(
        (skills / ".claude-ads-claude.manifest.json").read_text(encoding="utf-8-sig")
    )
    assert str(references.resolve()) not in manifest["directories"]
    assert str(references.parent.resolve()) not in manifest["directories"]

    uninstall = _powershell_uninstall(skills, agents)
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert references.is_dir()
    assert references.parent.is_dir()
    assert list(references.iterdir()) == []


@POWERSHELL_ONLY
def test_powershell_uninstall_rejects_non_exact_manifest_before_deletion(tmp_path):
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    install = _powershell_install(skills, agents)
    assert install.returncode == 0, install.stdout + install.stderr
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest["unexpected"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    uninstall = _powershell_uninstall(skills, agents)

    assert uninstall.returncode != 0
    assert "Invalid or mismatched ownership manifest" in uninstall.stdout + uninstall.stderr
    assert (skills / "ads" / "SKILL.md").is_file()
    assert manifest_path.is_file()


@WINDOWS_POWERSHELL_ONLY
def test_windows_uninstall_rejects_post_install_parent_junction_swap(tmp_path):
    executable = str(WINDOWS_POWERSHELL)
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("preserve\n", encoding="utf-8")
    install = _powershell_install(skills, agents, executable=executable)
    assert install.returncode == 0, install.stdout + install.stderr
    installed_agent = next(agents.glob("*.md"))
    (skills / "ads").rename(skills / "ads-owned")
    junction = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(skills / "ads"), str(outside)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert junction.returncode == 0, junction.stdout + junction.stderr

    uninstall = _powershell_uninstall(skills, agents, executable=executable)

    assert uninstall.returncode != 0
    assert "reparse-point uninstall path" in uninstall.stdout + uninstall.stderr
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
    assert installed_agent.is_file()
    assert (skills / ".claude-ads-claude.manifest.json").is_file()


@WINDOWS_POWERSHELL_ONLY
def test_windows_uninstall_rejects_junction_inside_recursive_owned_directory(tmp_path):
    executable = str(WINDOWS_POWERSHELL)
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("preserve\n", encoding="utf-8")
    install = _powershell_install(skills, agents, executable=executable)
    assert install.returncode == 0, install.stdout + install.stderr
    recursive = skills / "ads" / "owned-runtime"
    recursive.mkdir()
    junction = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(recursive / "escape"), str(outside)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert junction.returncode == 0, junction.stdout + junction.stderr
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest["recursive_directories"].append(str(recursive.resolve()))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    uninstall = _powershell_uninstall(skills, agents, executable=executable)

    assert uninstall.returncode != 0
    assert "reparse point inside recursive ownership directory" in uninstall.stdout + uninstall.stderr
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
    assert (skills / "ads" / "SKILL.md").is_file()
    assert manifest_path.is_file()


@WINDOWS_POWERSHELL_ONLY
def test_windows_installer_managed_repeat_rejects_descendant_junction(tmp_path):
    executable = str(WINDOWS_POWERSHELL)
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("preserve\n", encoding="utf-8")
    install = _powershell_install(skills, agents, executable=executable)
    assert install.returncode == 0, install.stdout + install.stderr
    venv = skills / "ads" / ".venv"
    (venv / "Lib").mkdir(parents=True)
    junction = subprocess.run(
        [
            "cmd.exe", "/d", "/c", "mklink", "/J",
            str(venv / "Lib" / "site-packages"), str(outside),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert junction.returncode == 0, junction.stdout + junction.stderr
    manifest_path = skills / ".claude-ads-claude.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest["recursive_directories"].append(str(venv.resolve()))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    repeat = _powershell_install(
        skills, agents, no_deps=False, executable=executable
    )

    assert repeat.returncode != 0
    assert "reparse point inside managed recursive directory" in repeat.stdout + repeat.stderr
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
    assert (skills / "ads" / "SKILL.md").is_file()
    assert manifest_path.is_file()


@WINDOWS_POWERSHELL_ONLY
def test_windows_powershell_51_parse_security_and_round_trip(tmp_path):
    executable = str(WINDOWS_POWERSHELL)
    for script in ("install.ps1", "uninstall.ps1"):
        command = f"[void][scriptblock]::Create((Get-Content -Raw '{ROOT / script}'))"
        parsed = subprocess.run(
            [executable, "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
        )
        assert parsed.returncode == 0, parsed.stdout + parsed.stderr

    blocked_skills = tmp_path / "blocked-skills"
    blocked_agents = tmp_path / "blocked-agents"
    unowned = blocked_skills / "ads" / "SKILL.md"
    unowned.parent.mkdir(parents=True)
    unowned.write_text("user-owned\n", encoding="utf-8")
    blocked = _powershell_install(
        blocked_skills, blocked_agents, executable=executable
    )
    assert blocked.returncode != 0
    assert unowned.read_text(encoding="utf-8") == "user-owned\n"
    assert not blocked_agents.exists()

    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    install = _powershell_install(skills, agents, executable=executable)
    assert install.returncode == 0, install.stdout + install.stderr
    uninstall = _powershell_uninstall(skills, agents, executable=executable)
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not (skills / "ads").exists()


@POWERSHELL_ONLY
def test_powershell_repeat_preserves_dropped_owned_file_for_uninstall(tmp_path):
    source = _minimal_distribution(tmp_path / "distribution")
    legacy_source = source / "agents" / "legacy-agent.md"
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"

    first = _powershell_install(skills, agents, repo_dir=source)
    assert first.returncode == 0, first.stdout + first.stderr
    installed_legacy = agents / legacy_source.name
    assert installed_legacy.is_file()
    legacy_source.unlink()

    repeat = _powershell_install(skills, agents, repo_dir=source)
    assert repeat.returncode == 0, repeat.stdout + repeat.stderr
    manifest = json.loads(
        (skills / ".claude-ads-claude.manifest.json").read_text(encoding="utf-8-sig")
    )
    assert str(installed_legacy.resolve()) in manifest["files"]

    uninstall = subprocess.run(
        [
            "pwsh", "-NoProfile", "-File", str(ROOT / "uninstall.ps1"),
            "-Target", "claude", "-SkillDir", str(skills), "-AgentDir", str(agents),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not installed_legacy.exists()


# ---------------------------------------------------------------------------
# Temporary-directory cleanup, path handling, and honest source wording
# ---------------------------------------------------------------------------


def _fake_git(tmp_path: Path, distribution: Path) -> tuple[Path, Path]:
    """Install a fake `git clone` that copies a local distribution.

    Returns the directory to prepend to PATH and the file that logs invocations.
    """
    directory = tmp_path / "fake-git-bin"
    directory.mkdir()
    log = tmp_path / "fake-git.log"
    script = directory / "git"
    script.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$FAKE_GIT_LOG"\n'
        'if [ -n "$FAKE_GIT_FAIL" ]; then\n'
        '  echo "fatal: simulated clone failure" >&2\n'
        "  exit 128\n"
        "fi\n"
        "for last; do :; done\n"
        'cp -R "$FAKE_GIT_SOURCE" "$last"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    return directory, log


def _run_installer(
    script: str, tmp_path: Path, *args: str, **extra_env: str
) -> subprocess.CompletedProcess[str]:
    if os.name == "nt":
        pytest.skip("Bash installer behavior is exercised on Linux and macOS runners")
    return subprocess.run(
        ["bash", str(ROOT / script), *args],
        cwd=ROOT,
        env={**os.environ, **extra_env},
        check=False,
        capture_output=True,
        text=True,
    )


@BASH_INSTALLER_ONLY
@pytest.mark.parametrize("scenario", ["success", "collision", "clone-failure"])
@pytest.mark.parametrize("source_mode", ["git", "local"])
def test_bash_installer_removes_temp_dirs_on_every_exit_path(
    tmp_path, scenario, source_mode
):
    if source_mode == "local" and scenario == "clone-failure":
        pytest.skip("A clone failure only exists for --source=git")
    distribution = _minimal_distribution(tmp_path / "distribution")
    fake_bin, log = _fake_git(tmp_path, distribution)
    scratch = tmp_path / "scratch-tmp"
    scratch.mkdir()
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    if scenario == "collision":
        # An unowned file makes main() return 1 after the plan directory exists.
        (skills / "ads").mkdir(parents=True)
        (skills / "ads/SKILL.md").write_text("user-owned\n", encoding="utf-8")
    source_args = (
        ["--source=git"]
        if source_mode == "git"
        else ["--source=local", f"--repo-dir={distribution}"]
    )

    result = _run_installer(
        "install.sh", tmp_path, "--target=claude", "--no-deps", *source_args,
        f"--skill-dir={skills}", f"--agent-dir={agents}",
        PATH=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        TMPDIR=str(scratch),
        FAKE_GIT_LOG=str(log),
        FAKE_GIT_SOURCE=str(distribution),
        FAKE_GIT_FAIL="1" if scenario == "clone-failure" else "",
    )

    if scenario == "success":
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
    if source_mode == "git":
        assert log.read_text(encoding="utf-8").startswith("clone --depth 1 ")
    assert list(scratch.iterdir()) == [], "installer leaked temporary directories"
    assert not list(skills.glob(".claude-ads-manifest.*"))


@BASH_INSTALLER_ONLY
def test_bash_installer_git_source_works_when_tmpdir_is_a_symlink(tmp_path):
    """macOS temp dirs live under the /var symlink; a default git install must still work."""
    distribution = _minimal_distribution(tmp_path / "distribution")
    fake_bin, log = _fake_git(tmp_path, distribution)
    real_scratch = tmp_path / "real-tmp"
    real_scratch.mkdir()
    linked_scratch = tmp_path / "linked-tmp"
    linked_scratch.symlink_to(real_scratch, target_is_directory=True)
    skills, agents = tmp_path / "skills", tmp_path / "agents"

    result = _run_installer(
        "install.sh", tmp_path, "--target=claude", "--no-deps", "--source=git",
        f"--skill-dir={skills}", f"--agent-dir={agents}",
        PATH=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        TMPDIR=str(linked_scratch),
        FAKE_GIT_LOG=str(log),
        FAKE_GIT_SOURCE=str(distribution),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert list(real_scratch.iterdir()) == [], "installer leaked temporary directories"


@BASH_INSTALLER_ONLY
def test_bash_uninstall_removes_validation_dir_on_every_exit_path(tmp_path):
    skills, agents = _install(tmp_path)
    scratch = tmp_path / "scratch-tmp"
    scratch.mkdir()
    arguments = ("--target=claude", f"--skill-dir={skills}", f"--agent-dir={agents}")
    manifest = skills / ".claude-ads-claude.manifest"
    valid = manifest.read_text(encoding="utf-8")

    # Failure after the validation directory exists.
    manifest.write_text(valid + f"F\t{tmp_path.parent / 'outside.txt'}\n", encoding="utf-8")
    failed = _run_installer("uninstall.sh", tmp_path, *arguments, TMPDIR=str(scratch))
    assert failed.returncode != 0
    assert list(scratch.iterdir()) == []

    # Normal completion.
    manifest.write_text(valid, encoding="utf-8")
    ok = _run_installer("uninstall.sh", tmp_path, *arguments, TMPDIR=str(scratch))
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert list(scratch.iterdir()) == []


@BASH_INSTALLER_ONLY
def test_bash_git_source_failure_surfaces_git_error_and_is_unpinned(tmp_path):
    distribution = _minimal_distribution(tmp_path / "distribution")
    fake_bin, log = _fake_git(tmp_path, distribution)
    skills, agents = tmp_path / "skills", tmp_path / "agents"

    result = _run_installer(
        "install.sh", tmp_path, "--target=claude", "--no-deps", "--source=git",
        f"--skill-dir={skills}", f"--agent-dir={agents}",
        PATH=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        FAKE_GIT_LOG=str(log), FAKE_GIT_SOURCE=str(distribution), FAKE_GIT_FAIL="1",
    )

    assert result.returncode != 0
    assert "simulated clone failure" in result.stderr
    assert not skills.exists() and not agents.exists()
    output = result.stdout + result.stderr
    assert "unpinned" in output
    assert "authenticated" not in output.lower()


@BASH_INSTALLER_ONLY
def test_bash_installer_expands_leading_tilde_instead_of_creating_tilde_dir(tmp_path):
    distribution = _minimal_distribution(tmp_path / "distribution")
    home = tmp_path / "home"
    home.mkdir()
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    result = subprocess.run(
        ["bash", str(ROOT / "install.sh"), "--target=claude", "--no-deps",
         "--source=local", f"--repo-dir={distribution}",
         "--skill-dir=~/custom/skills", "--agent-dir=~/custom/agents"],
        cwd=workdir, env={**os.environ, "HOME": str(home)},
        check=False, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / "custom/skills/ads/SKILL.md").is_file()
    assert (home / "custom/agents/legacy-agent.md").is_file()
    assert not (workdir / "~").exists()

    uninstall = subprocess.run(
        ["bash", str(ROOT / "uninstall.sh"), "--target=claude",
         "--skill-dir=~/custom/skills", "--agent-dir=~/custom/agents"],
        cwd=workdir, env={**os.environ, "HOME": str(home)},
        check=False, capture_output=True, text=True,
    )
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not (home / "custom/skills/ads/SKILL.md").exists()


@BASH_INSTALLER_ONLY
@pytest.mark.parametrize("script", ["install.sh", "uninstall.sh"])
def test_bash_installers_reject_tilde_user_paths_without_mutation(tmp_path, script):
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    arguments = ["--target=claude", "--skill-dir=~someone/skills", f"--agent-dir={tmp_path / 'agents'}"]
    if script == "install.sh":
        arguments += ["--source=local", "--no-deps"]

    result = subprocess.run(
        ["bash", str(ROOT / script), *arguments],
        cwd=workdir, check=False, capture_output=True, text=True,
    )

    assert result.returncode != 0
    assert "Unsupported ~user path" in result.stderr
    assert list(workdir.iterdir()) == []
    assert not (tmp_path / "agents").exists()


@BASH_INSTALLER_ONLY
def test_bash_installer_rejects_only_dotdot_components_and_allows_spaces(tmp_path):
    distribution = _minimal_distribution(tmp_path / "distribution")

    def install(skills: str, agents: str) -> subprocess.CompletedProcess[str]:
        return _run_installer(
            "install.sh", tmp_path, "--target=claude", "--no-deps",
            "--source=local", f"--repo-dir={distribution}",
            f"--skill-dir={skills}", f"--agent-dir={agents}",
        )

    for rejected in (
        f"{tmp_path}/a/../b",
        f"{tmp_path}/a/..",
        "..",
        "../skills",
    ):
        result = install(rejected, str(tmp_path / "agents"))
        assert result.returncode != 0, rejected
        assert "Invalid --skill-dir" in result.stderr, rejected
    assert not (tmp_path / "agents").exists()

    legitimate_skills = tmp_path / "my..skills v1..2" / "with space"
    legitimate_agents = tmp_path / "agents..dir"
    result = install(str(legitimate_skills), str(legitimate_agents))
    assert result.returncode == 0, result.stdout + result.stderr
    assert (legitimate_skills / "ads/SKILL.md").is_file()

    uninstall = _run_installer(
        "uninstall.sh", tmp_path, "--target=claude",
        f"--skill-dir={legitimate_skills}", f"--agent-dir={legitimate_agents}",
    )
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not (legitimate_skills / "ads/SKILL.md").exists()

    traversal = _run_installer(
        "uninstall.sh", tmp_path, "--target=claude",
        f"--skill-dir={tmp_path}/a/../b", f"--agent-dir={legitimate_agents}",
    )
    assert traversal.returncode != 0
    assert "Invalid --skill-dir" in traversal.stderr


@BASH_INSTALLER_ONLY
def test_bash_installer_banner_template_count_is_derived_from_files(tmp_path):
    skills, agents = tmp_path / "skills", tmp_path / "agents"
    result = _run_installer(
        "install.sh", tmp_path, "--target=claude", "--source=local", "--no-deps",
        f"--skill-dir={skills}", f"--agent-dir={agents}",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    expected = len(list((ROOT / "skills/ads-plan/assets").glob("*.md")))
    assert expected > 0
    assert f"{expected} industry templates" in result.stdout

    minimal = _minimal_distribution(tmp_path / "distribution")
    bare = _run_installer(
        "install.sh", tmp_path, "--target=claude", "--source=local", "--no-deps",
        f"--repo-dir={minimal}", f"--skill-dir={tmp_path / 'skills2'}",
        f"--agent-dir={tmp_path / 'agents2'}",
    )
    assert bare.returncode == 0, bare.stdout + bare.stderr
    assert "industry templates" not in bare.stdout


def test_installer_wording_does_not_claim_signatures_or_authenticated_git():
    for script in ("install.sh", "install.ps1"):
        text = (ROOT / script).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "authenticated git" not in lowered, script
        assert "signed release archive" not in lowered, script
        assert "12 industry templates" not in lowered, script
        assert "unpinned" in lowered, script
        assert "SHA256SUMS" in text, script


def test_powershell_installer_surfaces_git_clone_error_text():
    text = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "git clone --depth 1 $RepoUrl" in text
    assert "Out-Null" not in "".join(
        line for line in text.splitlines() if "git clone" in line
    )
    assert "Git clone failed (exit code $GitExitCode): $GitText" in text
    assert "$TemplateCount industry templates" in text
