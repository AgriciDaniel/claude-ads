"""Opt-in `--ref` pin for the git installer source (install.sh and install.ps1)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BASH_INSTALLER_ONLY = pytest.mark.skipif(
    os.name == "nt", reason="Bash installer behavior is exercised on Unix runners"
)
REAL_GIT_ONLY = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
REPO_URL = "https://github.com/AgriciDaniel/claude-ads"
TAG_SHA = "a" * 40
BRANCH_SHA = "b" * 40


def _distribution(path: Path, marker: str = "legacy") -> Path:
    (path / "ads/references").mkdir(parents=True)
    # Git does not track empty directories, so give the real-git fixtures a file.
    (path / "ads/references/note.md").write_text("note\n", encoding="utf-8")
    (path / "ads/SKILL.md").write_text("---\nname: ads\n---\n", encoding="utf-8")
    (path / "skills/ads-demo").mkdir(parents=True)
    (path / "skills/ads-demo/SKILL.md").write_text(
        "---\nname: ads-demo\n---\n", encoding="utf-8"
    )
    (path / "agents").mkdir()
    (path / "agents/legacy-agent.md").write_text(f"{marker}\n", encoding="utf-8")
    (path / "control-plane").mkdir()
    (path / "control-plane/README.md").write_text("# fixture\n", encoding="utf-8")
    (path / "control-plane/runtime-resources.txt").write_text(
        "control-plane/README.md\n", encoding="utf-8"
    )
    return path


def _fake_git(tmp_path: Path, distribution: Path, refs: dict[str, str]) -> dict[str, str]:
    """Fake git that copies a distribution on clone and resolves a fixed ref table."""
    directory = tmp_path / "fake-git-bin"
    directory.mkdir()
    log = tmp_path / "fake-git.log"
    table = tmp_path / "fake-refs"
    table.write_text("".join(f"{name} {sha}\n" for name, sha in refs.items()), encoding="utf-8")
    script = directory / "git"
    script.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$FAKE_GIT_LOG"\n'
        'repo=""\n'
        "while [ $# -gt 0 ]; do\n"
        '  case "$1" in\n'
        "    -c) shift 2 ;;\n"
        '    -C) repo="$2"; shift 2 ;;\n'
        "    *) break ;;\n"
        "  esac\n"
        "done\n"
        'sub="$1"; shift\n'
        'case "$sub" in\n'
        "  clone)\n"
        '    for last; do :; done\n'
        '    cp -R "$FAKE_GIT_SOURCE" "$last"\n'
        "    ;;\n"
        "  rev-parse)\n"
        '    for last; do :; done\n'
        '    if [ "$last" = HEAD ]; then cat "$repo/.fake-head"; exit 0; fi\n'
        "    suffix='^{commit}'\n"
        '    name="${last%"$suffix"}"\n'
        '    while read -r known sha; do\n'
        '      if [ "$known" = "$name" ]; then echo "$sha"; exit 0; fi\n'
        '    done < "$FAKE_GIT_REFS"\n'
        "    exit 1\n"
        "    ;;\n"
        "  checkout)\n"
        '    while [ $# -gt 0 ]; do\n'
        '      if [ "$1" = --end-of-options ]; then printf "%s" "$2" > "$repo/.fake-head"; fi\n'
        "      shift\n"
        "    done\n"
        "    ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return {
        "PATH": f"{directory}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GIT_LOG": str(log),
        "FAKE_GIT_SOURCE": str(distribution),
        "FAKE_GIT_REFS": str(table),
    }


def _install(tmp_path: Path, *args: str, env: dict[str, str] | None = None):
    scratch = tmp_path / "scratch-tmp"
    scratch.mkdir(exist_ok=True)
    return subprocess.run(
        [
            "bash", str(ROOT / "install.sh"), "--target=claude", "--no-deps",
            f"--skill-dir={tmp_path / 'skills'}", f"--agent-dir={tmp_path / 'agents'}",
            *args,
        ],
        cwd=ROOT,
        env={**os.environ, **(env or {}), "TMPDIR": str(scratch)},
        check=False,
        capture_output=True,
        text=True,
    )


def _log_lines(tmp_path: Path) -> list[str]:
    log = tmp_path / "fake-git.log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def _assert_nothing_installed(tmp_path: Path) -> None:
    assert not (tmp_path / "skills").exists()
    assert not (tmp_path / "agents").exists()
    assert list((tmp_path / "scratch-tmp").iterdir()) == [], "temporary directory leaked"


@BASH_INSTALLER_ONLY
@pytest.mark.parametrize(
    "source_args",
    [
        ["--source=local"],
        ["--source=auto"],
        ["--source=local", "--repo-dir=DIST"],
        ["--repo-dir=DIST"],
    ],
)
def test_ref_is_rejected_with_a_non_git_source(tmp_path, source_args):
    distribution = _distribution(tmp_path / "dist")
    fake = _fake_git(tmp_path, distribution, {"v2.0.2": TAG_SHA})
    args = [a.replace("DIST", str(distribution)) for a in source_args]

    result = _install(tmp_path, *args, "--ref=v2.0.2", env=fake)

    assert result.returncode != 0
    assert "--ref is only valid with --source=git" in result.stderr
    assert _log_lines(tmp_path) == []
    _assert_nothing_installed(tmp_path)


@BASH_INSTALLER_ONLY
@pytest.mark.parametrize(
    "value",
    [
        "",
        "-x",
        "--upload-pack=evil",
        "-",
        ".hidden",
        "a..b",
        "..",
        "a b",
        "a\tb",
        "a\nb",
        "a\rb",
        "a\x01b",
        "x" * 101,
        "a;b",
        "a$b",
        "a`b",
        "a^b",
        "a~1",
        "a:b",
        "a@{1}",
        "/abs",
        "a//b",
        "a/",
        "v1é",
    ],
    ids=lambda v: repr(v)[:30],
)
@pytest.mark.parametrize("form", ["equals", "separate"])
def test_invalid_ref_is_rejected_before_any_git_call(tmp_path, value, form):
    distribution = _distribution(tmp_path / "dist")
    fake = _fake_git(tmp_path, distribution, {"v2.0.2": TAG_SHA})
    ref_args = [f"--ref={value}"] if form == "equals" else ["--ref", value]

    result = _install(tmp_path, "--source=git", *ref_args, env=fake)

    assert result.returncode != 0
    assert "Invalid --ref" in result.stderr
    assert _log_lines(tmp_path) == [], "git was invoked for an invalid ref"
    _assert_nothing_installed(tmp_path)


@BASH_INSTALLER_ONLY
def test_ref_requires_a_value(tmp_path):
    distribution = _distribution(tmp_path / "dist")
    fake = _fake_git(tmp_path, distribution, {})

    result = _install(tmp_path, "--source=git", "--ref", env=fake)

    assert result.returncode != 0
    assert "--ref requires a value" in result.stderr
    assert _log_lines(tmp_path) == []


@BASH_INSTALLER_ONLY
@pytest.mark.parametrize(
    "value", ["v2.0.2", "release/2.0", "feature_x-1.2", "a" * 100, "V1", "2026.10"]
)
def test_valid_ref_values_pass_validation(tmp_path, value):
    distribution = _distribution(tmp_path / "dist")
    fake = _fake_git(tmp_path, distribution, {value: TAG_SHA})

    result = _install(tmp_path, "--source=git", f"--ref={value}", env=fake)

    assert result.returncode == 0, result.stdout + result.stderr


@BASH_INSTALLER_ONLY
def test_valid_tag_is_checked_out_detached_after_clone_and_sha_is_printed(tmp_path):
    distribution = _distribution(tmp_path / "dist", marker="pinned-tag")
    fake = _fake_git(tmp_path, distribution, {"v2.0.2": TAG_SHA})

    result = _install(tmp_path, "--source=git", "--ref=v2.0.2", env=fake)

    assert result.returncode == 0, result.stdout + result.stderr
    lines = _log_lines(tmp_path)
    assert lines[0].startswith(f"clone --no-checkout {REPO_URL} ")
    assert "--depth" not in lines[0]
    assert any(
        line.endswith("rev-parse --verify --quiet --end-of-options v2.0.2^{commit}")
        for line in lines
    )
    checkout = [line for line in lines if " checkout " in line]
    assert len(checkout) == 1
    assert checkout[0].startswith("-c advice.detachedHead=false -C ")
    assert checkout[0].endswith(f"checkout --detach --end-of-options {TAG_SHA} --")
    assert lines.index(checkout[0]) > 0, "checkout must follow the clone"

    assert "Pinned git ref: v2.0.2" in result.stdout
    assert f"Resolved commit: {TAG_SHA}" in result.stdout
    assert "git ref, not a checksum-verified release" in result.stdout
    assert "default branch HEAD" not in result.stdout
    assert "signed release archive" not in (result.stdout + result.stderr).lower()
    assert (tmp_path / "agents/legacy-agent.md").read_text(encoding="utf-8") == "pinned-tag\n"
    assert not list((tmp_path / "skills").glob(".claude-ads-manifest.*"))
    assert list((tmp_path / "scratch-tmp").iterdir()) == []


@BASH_INSTALLER_ONLY
def test_branch_ref_resolves_through_the_remote_tracking_ref(tmp_path):
    distribution = _distribution(tmp_path / "dist")
    fake = _fake_git(tmp_path, distribution, {"refs/remotes/origin/feature/x": BRANCH_SHA})

    result = _install(tmp_path, "--source=git", "--ref=feature/x", env=fake)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Resolved commit: {BRANCH_SHA}" in result.stdout
    assert any(
        line.endswith(f"checkout --detach --end-of-options {BRANCH_SHA} --")
        for line in _log_lines(tmp_path)
    )


@BASH_INSTALLER_ONLY
def test_unresolvable_ref_fails_closed_without_mutation_or_temp_leak(tmp_path):
    distribution = _distribution(tmp_path / "dist")
    fake = _fake_git(tmp_path, distribution, {"v2.0.2": TAG_SHA})

    result = _install(tmp_path, "--source=git", "--ref=v9.9.9", env=fake)

    assert result.returncode != 0
    assert "Git ref does not resolve to a commit: v9.9.9" in result.stderr
    assert "Nothing was installed" in result.stderr
    assert not any(" checkout " in line for line in _log_lines(tmp_path))
    assert "Resolved commit" not in result.stdout
    _assert_nothing_installed(tmp_path)


@BASH_INSTALLER_ONLY
def test_unresolvable_ref_does_not_touch_an_existing_install(tmp_path):
    distribution = _distribution(tmp_path / "dist")
    fake = _fake_git(tmp_path, distribution, {"v2.0.2": TAG_SHA})
    first = _install(tmp_path, "--source=git", "--ref=v2.0.2", env=fake)
    assert first.returncode == 0, first.stdout + first.stderr
    before = {
        str(p.relative_to(tmp_path)): p.read_bytes()
        for root in ("skills", "agents")
        for p in (tmp_path / root).rglob("*")
        if p.is_file()
    }

    result = _install(tmp_path, "--source=git", "--ref=nope", env=fake)

    assert result.returncode != 0
    after = {
        str(p.relative_to(tmp_path)): p.read_bytes()
        for root in ("skills", "agents")
        for p in (tmp_path / root).rglob("*")
        if p.is_file()
    }
    assert after == before
    assert list((tmp_path / "scratch-tmp").iterdir()) == []


@BASH_INSTALLER_ONLY
def test_clone_failure_with_ref_surfaces_error_and_leaks_nothing(tmp_path):
    distribution = _distribution(tmp_path / "dist")
    fake = _fake_git(tmp_path, distribution, {"v2.0.2": TAG_SHA})
    failing = tmp_path / "failing-bin"
    failing.mkdir()
    (failing / "git").write_text(
        '#!/bin/sh\necho "fatal: simulated clone failure" >&2\nexit 128\n', encoding="utf-8"
    )
    (failing / "git").chmod(0o755)
    fake["PATH"] = f"{failing}{os.pathsep}{os.environ['PATH']}"

    result = _install(tmp_path, "--source=git", "--ref=v2.0.2", env=fake)

    assert result.returncode != 0
    assert "simulated clone failure" in result.stderr
    _assert_nothing_installed(tmp_path)


@BASH_INSTALLER_ONLY
def test_without_ref_keeps_the_unpinned_behavior_and_wording(tmp_path):
    distribution = _distribution(tmp_path / "dist")
    fake = _fake_git(tmp_path, distribution, {})

    result = _install(tmp_path, "--source=git", env=fake)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "default branch HEAD, unpinned, not a verified release" in result.stdout
    assert "Pinned git ref" not in result.stdout
    lines = _log_lines(tmp_path)
    assert len(lines) == 1 and lines[0].startswith("clone --depth 1 ")


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull},
    ).stdout.strip()


def _real_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """A real repository with a tag on the first commit and a later branch commit."""
    repo = tmp_path / "upstream"
    _distribution(repo, marker="tagged-release")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "release")
    _git(repo, "tag", "v9.9.9")
    first = _git(repo, "rev-parse", "HEAD")
    (repo / "agents/legacy-agent.md").write_text("moved-on\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "next")
    _git(repo, "branch", "feature/x", "HEAD")
    return repo, first, _git(repo, "rev-parse", "HEAD")


def _real_git_env(repo: Path) -> dict[str, str]:
    return {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": f"url.file://{repo}.insteadOf",
        "GIT_CONFIG_VALUE_0": REPO_URL,
    }


@BASH_INSTALLER_ONLY
@REAL_GIT_ONLY
@pytest.mark.parametrize("which", ["tag", "branch", "full-sha", "short-sha"])
def test_real_git_pins_tag_branch_and_commit(tmp_path, which):
    repo, first, head = _real_repo(tmp_path)
    ref, expected_sha, expected_marker = {
        "tag": ("v9.9.9", first, "tagged-release\n"),
        "branch": ("feature/x", head, "moved-on\n"),
        "full-sha": (first, first, "tagged-release\n"),
        "short-sha": (first[:10], first, "tagged-release\n"),
    }[which]

    result = _install(tmp_path, "--source=git", f"--ref={ref}", env=_real_git_env(repo))

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Resolved commit: {expected_sha}" in result.stdout
    assert (tmp_path / "agents/legacy-agent.md").read_text(encoding="utf-8") == expected_marker
    assert list((tmp_path / "scratch-tmp").iterdir()) == []


@BASH_INSTALLER_ONLY
@REAL_GIT_ONLY
@pytest.mark.parametrize("ref", ["v0.0.0", "deadbeefdeadbeef", "feature/missing"])
def test_real_git_unresolvable_ref_installs_nothing(tmp_path, ref):
    repo, _first, _head = _real_repo(tmp_path)

    result = _install(tmp_path, "--source=git", f"--ref={ref}", env=_real_git_env(repo))

    assert result.returncode != 0
    assert "Git ref does not resolve to a commit" in result.stderr
    _assert_nothing_installed(tmp_path)


@BASH_INSTALLER_ONLY
@REAL_GIT_ONLY
def test_real_git_full_sha_ref_is_not_confused_by_a_same_named_file(tmp_path):
    # The checkout form ends options and paths explicitly, so a file whose name
    # equals the commit does not change what is checked out.
    repo, first, _head = _real_repo(tmp_path)
    (repo / first).write_text("a file named like the commit\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "decoy file")

    result = _install(tmp_path, "--source=git", f"--ref={first}", env=_real_git_env(repo))

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Resolved commit: {first}" in result.stdout
    assert (tmp_path / "agents/legacy-agent.md").read_text(encoding="utf-8") == "tagged-release\n"


def test_install_sh_help_and_header_document_the_pin():
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "--ref=<tag|branch|commit>" in text
    assert "bash install.sh --source=git --ref=v2.0.2" in text
    assert "not a checksum-verified release" in text
    assert "unpinned" in text
    assert "default branch HEAD, unpinned, not a verified release" in text
    assert "--end-of-options" in text


def test_readme_documents_the_pin_and_keeps_the_verified_release_path():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "bash install.sh --source=git --ref=v2.1.0" in text
    assert "A git ref is not a checksum-verified release" in text
    assert "sha256sum -c SHA256SUMS" in text


# ---------------------------------------------------------------------------
# install.ps1 static checks (PowerShell is not required on the test host)
# ---------------------------------------------------------------------------


def _ps1() -> str:
    return (ROOT / "install.ps1").read_text(encoding="utf-8")


def test_powershell_declares_the_ref_parameter_and_validator():
    text = _ps1()
    assert re.search(r"\[string\]\$Ref = ''", text)
    assert "$RefWasSupplied = $PSBoundParameters.ContainsKey('Ref')" in text
    assert "function Test-GitRef" in text
    assert r"-cnotmatch '\A[A-Za-z0-9._/-]+\z'" in text
    assert "$Value.Length -gt 100" in text
    assert "'^[-./]'" in text
    assert "$Value.Contains('..')" in text
    assert "-Source git -Ref v2.0.2" in text


def test_powershell_validates_ref_before_any_git_call_and_requires_git_source():
    text = _ps1()
    validation = text.index("-not (Test-GitRef -Value $Ref)")
    source_check = text.index("-Ref is only valid with -Source git")
    first_git = text.index("& git ")
    assert validation < first_git
    assert source_check < first_git
    assert "$RefWasSupplied -and $Source -ne 'git'" in text


def test_powershell_checks_out_the_resolved_ref_detached_and_fails_closed():
    text = _ps1()
    clone = text.index("git clone --no-checkout $RepoUrl $CloneDir")
    resolve = text.index("rev-parse --verify --quiet --end-of-options $Candidate")
    checkout = text.index(
        "git -c advice.detachedHead=false -C $CloneDir checkout --detach "
        "--end-of-options $PinnedSha --"
    )
    assert clone < resolve < checkout
    assert "Git ref does not resolve to a commit: $Ref. Nothing was installed." in text
    assert "${Ref}^{commit}" in text and "refs/remotes/origin/${Ref}^{commit}" in text
    assert "$HeadSha -cne $PinnedSha" in text
    assert "Resolved commit: $PinnedSha" in text
    # Temporary directory cleanup stays in the finally block.
    assert "Remove-Item -Path $TempDir -Recurse -Force" in text


def test_powershell_wording_is_honest_with_and_without_ref():
    text = _ps1()
    lowered = text.lower()
    assert "default branch HEAD, unpinned, not a verified release" in text
    assert "git clone --depth 1 $RepoUrl" in text
    assert "pinned to git ref $Ref; a git ref is not a checksum-verified release" in text
    assert "not a checksum-verified release, and it is not signed" in text
    assert "signed release archive" not in lowered
    assert "authenticated git" not in lowered
