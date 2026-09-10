"""Installer ownership and dependency-isolation regression tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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
    if target.count("|") == 3:
        target += "|glibc|2.17|supported" if "|linux|" in target else "|none|11.0|supported"
    script.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = \"-c\" ]; then printf '%s\\n' '{target}'; exit 0; fi\n"
        + ("exit 42\n" if fail_venv else "exec /usr/bin/python3 \"$@\"\n"),
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
    source = tmp_path / "distribution"
    (source / "ads" / "references").mkdir(parents=True)
    (source / "ads" / "SKILL.md").write_text("---\nname: ads\n---\n", encoding="utf-8")
    (source / "skills" / "ads-demo").mkdir(parents=True)
    (source / "skills" / "ads-demo" / "SKILL.md").write_text(
        "---\nname: ads-demo\n---\n", encoding="utf-8"
    )
    (source / "agents").mkdir()
    legacy_source = source / "agents" / "legacy-agent.md"
    legacy_source.write_text("legacy\n", encoding="utf-8")
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
