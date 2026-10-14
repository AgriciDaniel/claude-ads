"""Optional companion archive safety and ordinary installer isolation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("package_cockpit", ROOT / "scripts/package_cockpit.py")
assert SPEC and SPEC.loader
packaging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packaging)


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    companion = root / packaging.COMPANION_ROOT
    for relative in packaging.RUNTIME_FILES:
        path = companion / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"// Public fixture: {relative}\n", encoding="utf-8")
    manifest = {"name": packaging.NAME, "version": packaging.VERSION, "license": "MIT", "types": "./types/index.d.ts"}
    (companion / ".claude-plugin/plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    (companion / "hooks/hooks.json").write_text(json.dumps({"modules": ["./register.mjs"]}), encoding="utf-8")
    (root / "LICENSE").write_text("MIT fixture license\n", encoding="utf-8")
    (companion / "LICENSE").write_bytes((root / "LICENSE").read_bytes())
    return root


def test_reproducible_curated_archive_and_checksum_manifest(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    first = packaging.build_companion(root, tmp_path / "first", source_date_epoch=1791417600)
    for relative in packaging.RUNTIME_FILES:
        os.utime(root / packaging.COMPANION_ROOT / relative, (1791504000, 1791504000))
    second = packaging.build_companion(root, tmp_path / "second", source_date_epoch=1791417600)
    assert {name: path.read_bytes() for name, path in first.items()} == {
        name: path.read_bytes() for name, path in second.items()
    }
    packaging.verify_companion(root, tmp_path / "first")
    manifest = json.loads(first[f"{packaging.NAME}-{packaging.VERSION}.manifest.json"].read_bytes())
    assert manifest["core_required"] is True
    with zipfile.ZipFile(first[f"{packaging.NAME}-{packaging.VERSION}.zip"]) as archive:
        assert archive.namelist() == [f"{packaging.NAME}/{item}" for item in sorted(packaging.RUNTIME_FILES)]
        for item in archive.infolist():
            assert not item.is_dir()
            assert stat.S_ISREG(item.external_attr >> 16)
            assert stat.S_IMODE(item.external_attr >> 16) == 0o644
            record = next(row for row in manifest["files"] if row["path"] == item.filename)
            assert record["sha256"] == hashlib.sha256(archive.read(item)).hexdigest()
    for line in first[f"{packaging.NAME}-{packaging.VERSION}.sha256"].read_text().splitlines():
        digest, filename = line.split("  ")
        assert hashlib.sha256(first[filename].read_bytes()).hexdigest() == digest


def test_no_recursive_snapshot_or_private_artifacts(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    companion = root / packaging.COMPANION_ROOT
    excluded = (
        ".claude-plugin/types/host.d.ts", "tests/session.json", "transcripts/session.txt",
        ".env", "vault/private.md", "runs/client/cockpit.json", "node_modules/pkg/index.js",
        "release-evidence/review.json", "fixtures/demo/client-export.csv", "__pycache__/x.pyc",
    )
    for relative in excluded:
        path = companion / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Never include this unregistered material.", encoding="utf-8")
    outputs = packaging.build_companion(root, tmp_path / "output")
    with zipfile.ZipFile(outputs[f"{packaging.NAME}-{packaging.VERSION}.zip"]) as archive:
        assert {item.removeprefix(f"{packaging.NAME}/") for item in archive.namelist()} == set(packaging.RUNTIME_FILES)
        assert all("claude_ads_core" not in item for item in archive.namelist())
    assert b"Never include" not in outputs[f"{packaging.NAME}-{packaging.VERSION}.zip"].read_bytes()


@pytest.mark.parametrize("relative", ["../escape", "foo/../escape", "/absolute", "foo//bar", "foo/./bar", "aux.txt", "C:/escape", "foo\\bar", "foo\x7fbar"])
def test_allowlist_rejects_unsafe_paths(tmp_path: Path, monkeypatch, relative: str) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(packaging, "RUNTIME_FILES", (*packaging.RUNTIME_FILES, relative))
    with pytest.raises(packaging.PackageError, match="unsafe archive path"):
        packaging.build_companion(root, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_allowlist_rejects_case_collisions(tmp_path: Path, monkeypatch) -> None:
    root = _repository(tmp_path)
    monkeypatch.setattr(packaging, "RUNTIME_FILES", (*packaging.RUNTIME_FILES, "readme.md"))
    with pytest.raises(packaging.PackageError, match="duplicate"):
        packaging.build_companion(root, tmp_path / "output")


@pytest.mark.skipif(os.name == "nt", reason="symbolic links need extra privileges on Windows")
@pytest.mark.parametrize("target", ["file", "ancestor", "output"])
def test_symlink_paths_are_rejected(tmp_path: Path, target: str) -> None:
    root = _repository(tmp_path)
    companion = root / packaging.COMPANION_ROOT
    output = tmp_path / "output"
    if target == "file":
        (companion / "README.md").unlink()
        (companion / "README.md").symlink_to(root / "LICENSE")
    elif target == "ancestor":
        (root / "mods").rename(root / "real-mods")
        (root / "mods").symlink_to(root / "real-mods", target_is_directory=True)
    else:
        actual = tmp_path / "actual-output"
        actual.mkdir()
        output.symlink_to(actual, target_is_directory=True)
    with pytest.raises(packaging.PackageError, match="symlink"):
        packaging.build_companion(root, output)


@pytest.mark.parametrize("kind", ["directory", "oversized", "fifo"])
def test_only_bounded_regular_files_are_read(tmp_path: Path, kind: str) -> None:
    root = _repository(tmp_path)
    path = root / packaging.COMPANION_ROOT / "README.md"
    path.unlink()
    if kind == "directory":
        path.mkdir()
    elif kind == "oversized":
        path.write_bytes(b"x" * (packaging.MAX_FILE_BYTES + 1))
    else:
        if not hasattr(os, "mkfifo"):
            pytest.skip("FIFO is a POSIX filesystem type")
        os.mkfifo(path)
    with pytest.raises(packaging.PackageError, match="regular|size limit"):
        packaging.build_companion(root, tmp_path / "output")


@pytest.mark.parametrize("mutation", ["identity", "license", "private", "missing"])
def test_invalid_or_restricted_sources_fail_before_output(tmp_path: Path, mutation: str) -> None:
    root = _repository(tmp_path)
    companion = root / packaging.COMPANION_ROOT
    if mutation == "identity":
        (companion / ".claude-plugin/plugin.json").write_text('{"name": "other"}')
    elif mutation == "license":
        (companion / "LICENSE").write_text("Unreviewed license")
    elif mutation == "private":
        (companion / "README.md").write_text("/var/ho" + "me/private-owner/client/data.json")
    else:
        (companion / "hooks/register.mjs").unlink()
    with pytest.raises(packaging.PackageError):
        packaging.build_companion(root, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_source_date_epoch_is_explicit_and_validated(tmp_path: Path, monkeypatch) -> None:
    root = _repository(tmp_path)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1791417601")
    outputs = packaging.build_companion(root, tmp_path / "output")
    manifest = json.loads(outputs[f"{packaging.NAME}-{packaging.VERSION}.manifest.json"].read_bytes())
    assert manifest["source_date_epoch"] == 1791417600
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "invalid")
    with pytest.raises(packaging.PackageError, match="integer"):
        packaging.build_companion(root, tmp_path / "bad-output")
    with pytest.raises(packaging.PackageError, match="1980-2107"):
        packaging.build_companion(root, tmp_path / "old-output", source_date_epoch=0)


def test_refuses_to_overwrite_and_verifies_exact_source_bytes(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    outputs = packaging.build_companion(root, tmp_path / "output")
    original = {name: path.read_bytes() for name, path in outputs.items()}
    with pytest.raises(packaging.PackageError, match="already exists"):
        packaging.build_companion(root, tmp_path / "output")
    assert {name: path.read_bytes() for name, path in outputs.items()} == original
    (root / packaging.COMPANION_ROOT / "README.md").write_text("Changed public documentation")
    with pytest.raises(packaging.PackageError, match="differs"):
        packaging.verify_companion(root, tmp_path / "output")


def test_archive_tampering_fails_verification(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    outputs = packaging.build_companion(root, tmp_path / "output")
    archive = outputs[f"{packaging.NAME}-{packaging.VERSION}.zip"]
    with zipfile.ZipFile(archive, "a") as zipped:
        zipped.writestr("../escape", b"unregistered")
    with pytest.raises(packaging.PackageError, match="differs"):
        packaging.verify_companion(root, tmp_path / "output")


def test_real_companion_allowlist_and_manifest_are_packageable(tmp_path: Path) -> None:
    outputs = packaging.build_companion(ROOT, tmp_path / "output")
    packaging.verify_companion(ROOT, tmp_path / "output")
    assert len(outputs) == 3
    assert "types/index.d.ts" in packaging.RUNTIME_FILES
    assert all(not item.startswith(".claude-plugin/types/") for item in packaging.RUNTIME_FILES)


@pytest.mark.skipif(os.name == "nt" or shutil.which("bash") is None, reason="Bash lifecycle requires POSIX host")
def test_main_install_uninstall_does_not_enable_or_remove_optional_companion(tmp_path: Path) -> None:
    # Use only a synthetic profile. The companion lives beside, not within,
    # installer-owned skill and agent directories.
    profile = tmp_path / "profile"
    optional = profile / "mods" / packaging.NAME
    optional.mkdir(parents=True)
    marker = optional / "user-owned.txt"
    marker.write_text("Preserve optional companion and runs.")
    run = profile / "runs" / "keep" / "manifest.json"
    run.parent.mkdir(parents=True)
    run.write_text("Retain run")
    args = ["--target=claude", f"--skill-dir={profile / 'skills'}", f"--agent-dir={profile / 'agents'}"]
    environment = {**os.environ, "HOME": str(profile)}
    installed = subprocess.run(["bash", str(ROOT / "install.sh"), "--source=local", "--no-deps", *args], cwd=ROOT, env=environment, capture_output=True, text=True)
    assert installed.returncode == 0, installed.stdout + installed.stderr
    skill = profile / "skills" / "ads"
    assert not (skill / "mods").exists()
    assert not any(packaging.NAME in path.name for path in (profile / "skills").rglob("*"))
    ownership = (profile / "skills" / ".claude-ads-claude.manifest").read_text()
    assert str(optional) not in ownership
    uninstalled = subprocess.run(["bash", str(ROOT / "uninstall.sh"), *args], cwd=ROOT, env=environment, capture_output=True, text=True)
    assert uninstalled.returncode == 0, uninstalled.stdout + uninstalled.stderr
    assert marker.read_text() == "Preserve optional companion and runs."
    assert run.read_text() == "Retain run"
    assert not skill.exists()


@pytest.mark.parametrize("target", ["types", "hooks"])
def test_manifest_runtime_references_cannot_escape_allowlist(tmp_path: Path, target: str) -> None:
    root = _repository(tmp_path)
    companion = root / packaging.COMPANION_ROOT
    if target == "types":
        path = companion / ".claude-plugin/plugin.json"
        value = json.loads(path.read_text())
        value["types"] = "../private/host.d.ts"
    else:
        path = companion / "hooks/hooks.json"
        value = {"modules": ["../../private/session.mjs"]}
    path.write_text(json.dumps(value))
    with pytest.raises(packaging.PackageError, match="outside the curated surface"):
        packaging.build_companion(root, tmp_path / "output")


def test_detects_input_change_during_capture(tmp_path: Path, monkeypatch) -> None:
    root = _repository(tmp_path)
    path = root / packaging.COMPANION_ROOT / "README.md"
    original = packaging.os.fstat
    changed = False
    def mutate_after_open(descriptor):
        nonlocal changed
        info = original(descriptor)
        if not changed:
            path.write_text("Concurrent replacement changes captured bytes.")
            changed = True
        return info
    monkeypatch.setattr(packaging.os, "fstat", mutate_after_open)
    with pytest.raises(packaging.PackageError, match="changed"):
        packaging._read(path)


def test_cli_package_and_verify_print_only_relative_artifact_names(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    output = tmp_path / "output"
    command = [sys.executable, str(ROOT / "scripts/package_cockpit.py"), "--root", str(root), "--output-dir", str(output)]
    packaged = subprocess.run([*command, "package"], capture_output=True, text=True)
    assert packaged.returncode == 0, packaged.stderr
    assert packaged.stdout.splitlines() == [f"{packaging.NAME}-{packaging.VERSION}{suffix}" for suffix in (".zip", ".manifest.json", ".sha256")]
    verified = subprocess.run([*command, "verify"], capture_output=True, text=True)
    assert verified.returncode == 0, verified.stderr
    assert verified.stdout.strip() == "companion package verified against curated source"
    assert str(root) not in packaged.stdout + packaged.stderr + verified.stdout + verified.stderr


def test_verifier_bounds_whole_archive_separately_from_each_input(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    companion = root / packaging.COMPANION_ROOT
    for relative in ("README.md", "hooks/wire.mjs"):
        (companion / relative).write_bytes(b"x" * (packaging.MAX_FILE_BYTES // 2 + 1))
    outputs = packaging.build_companion(root, tmp_path / "output")
    assert outputs[f"{packaging.NAME}-{packaging.VERSION}.zip"].stat().st_size > packaging.MAX_FILE_BYTES
    packaging.verify_companion(root, tmp_path / "output")


IMPORT_SPECIFIER = re.compile(r"""(?:^|;)[ \t]*(?:import|export)\s*(?:[^'";]*?\sfrom\s*)?['"]([^'"]+)['"]""", re.M)
DYNAMIC_IMPORT = re.compile(r"\bimport\s*\(")


def _specifiers(source: str) -> list[str]:
    # Comments can mention imports; drop them before matching.
    code = re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", source, flags=re.S)
    return IMPORT_SPECIFIER.findall(code)


def test_import_closure_stays_inside_the_runtime_allowlist() -> None:
    """A hook that imports a file the archive omits would load in a checkout and fail once packaged."""
    allowed = set(packaging.RUNTIME_FILES)
    companion = ROOT / packaging.COMPANION_ROOT
    checked = 0
    for relative in sorted(item for item in allowed if item.endswith(".mjs")):
        source = (companion / relative).read_text(encoding="utf-8")
        assert not DYNAMIC_IMPORT.search(re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", source, flags=re.S)), \
            f"{relative} uses a dynamic import; the static closure cannot cover it"
        for specifier in _specifiers(source):
            if specifier == "claude-code":
                continue
            assert specifier.startswith("./") or specifier.startswith("../"), f"{relative} imports {specifier}"
            target = PurePosixPath(os.path.normpath((PurePosixPath(relative).parent / specifier).as_posix()))
            assert not str(target).startswith(".."), f"{relative} imports outside the companion: {specifier}"
            assert target.as_posix() in allowed, f"{relative} imports {specifier}, which the archive omits"
            assert (companion / target).is_file()
            checked += 1
    assert checked >= 20  # the hooks do import each other; a parser that finds nothing must not pass


def test_import_closure_parser_sees_every_import_form() -> None:
    source = """
    import { a } from './a.mjs';
    import b from "../b.mjs"
    import './c.mjs';
    export { d } from './d.mjs';
    export * from './e.mjs';
    // import { z } from './comment.mjs';
    /* import { y } from './block.mjs'; */
    const text = 'not an import';
    import { atom,
      read } from 'claude-code';
    """
    assert _specifiers(source) == ["./a.mjs", "../b.mjs", "./c.mjs", "./d.mjs", "./e.mjs", "claude-code"]


def test_manifest_entry_points_are_in_the_allowlist() -> None:
    companion = ROOT / packaging.COMPANION_ROOT
    hooks = json.loads((companion / "hooks/hooks.json").read_text(encoding="utf-8"))
    plugin = json.loads((companion / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    for module in hooks["modules"]:
        assert (PurePosixPath("hooks") / module).as_posix().replace("/./", "/") in packaging.RUNTIME_FILES
    assert plugin["types"].removeprefix("./") in packaging.RUNTIME_FILES
