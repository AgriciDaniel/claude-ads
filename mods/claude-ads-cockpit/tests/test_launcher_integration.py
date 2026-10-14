"""Local subprocess isolation tests, separate from host mod-kit tree tests."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import sysconfig
import venv

import pytest

SOURCE = Path(__file__).parents[1] / 'hooks' / 'launcher.mjs'
LOADER = re.search(r'PYTHON_LOADER = `(.*?)`;', SOURCE.read_text(), re.S).group(1)


def core(root, *, standalone=False):
    package = root / ('scripts/claude_ads_core' if standalone else 'claude_ads_core')
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('')
    (package / 'cli.py').write_text('''import json, importlib.util

def main(args):
    available = importlib.util.find_spec("cockpit_pdf_dependency") is not None
    print(json.dumps({"args": args, "optional_pdf_dependency_visible": available}))
    return 0
''')


def run(python, root, cwd, env=None):
    return subprocess.run([str(python), '-I', '-S', '-c', LOADER, str(root),
                           'cockpit', 'doctor', '--policy-root', str(root)],
                          cwd=cwd, env=env, text=True, capture_output=True, timeout=20)


@pytest.mark.parametrize('standalone', [False, True])
def test_source_and_verified_standalone_layout(tmp_path, standalone):
    root = tmp_path / 'core'
    core(root, standalone=standalone)
    result = run(sys.executable, root, tmp_path)
    assert result.returncode == 0
    assert json.loads(result.stdout)['args'][:2] == ['cockpit', 'doctor']


def test_environment_and_working_directory_import_poisoning(tmp_path):
    root = tmp_path / 'core'
    core(root)
    poison = tmp_path / 'poison'
    poison.mkdir()
    for module in ['json', 'pathlib', 'tempfile', 'sysconfig', 'sitecustomize', 'usercustomize']:
        (poison / f'{module}.py').write_text('raise RuntimeError("poison imported")')
    (poison / 'claude_ads_core').mkdir()
    (poison / 'claude_ads_core' / '__init__.py').write_text('raise RuntimeError("poison core imported")')
    env = {**os.environ, 'PYTHONPATH':str(poison), 'PYTHONHOME':str(poison),
           'PYTHONUSERBASE':str(poison), 'PYTHONSTARTUP':str(poison / 'sitecustomize.py')}
    result = run(sys.executable, root, poison, env)
    assert result.returncode == 0
    assert 'poison imported' not in result.stdout + result.stderr


def test_bound_venv_dependencies_visible_without_pth_execution(tmp_path):
    root = tmp_path / 'core'
    core(root)
    environment = tmp_path / 'trusted-python'
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    paths = sysconfig.get_paths(vars={'base':str(environment),'platbase':str(environment)})
    site = Path(paths['purelib'])
    site.mkdir(parents=True, exist_ok=True)
    (site / 'cockpit_pdf_dependency.py').write_text('AVAILABLE = True')
    marker = tmp_path / 'pth-executed'
    (site / 'untrusted.pth').write_text(f'import pathlib; pathlib.Path({str(marker)!r}).touch()\n')
    result = run(python, root, tmp_path)
    assert result.returncode == 0
    assert json.loads(result.stdout)['optional_pdf_dependency_visible'] is True
    assert not marker.exists()


def test_symlinked_core_and_dependency_escape_fail_closed(tmp_path):
    root = tmp_path / 'core'
    core(root)
    link = tmp_path / 'linked-core'
    try:
        link.symlink_to(root, target_is_directory=True)
    except OSError:
        pytest.skip('symlink creation unavailable on this host')
    result = run(sys.executable, link, tmp_path)
    assert result.returncode == 2
    assert json.loads(result.stdout) == {'error':'Trusted core unavailable or configuration unsafe'}
    assert str(tmp_path) not in result.stdout
    environment = tmp_path / 'trusted-python'
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    site = Path(sysconfig.get_paths(vars={'base':str(environment),'platbase':str(environment)})['purelib'])
    for path in site.iterdir():
        assert path.name in {'README.txt'}
        path.unlink()
    site.rmdir()
    external = tmp_path / 'external-site'
    external.mkdir()
    site.symlink_to(external, target_is_directory=True)
    result = run(python, root, tmp_path)
    assert result.returncode == 2
    assert json.loads(result.stdout)['error'] == 'Trusted core unavailable or configuration unsafe'


def demo_call(python, root, *args, env=None):
    return subprocess.run([str(python), '-I', '-S', '-c', LOADER, str(root), *args],
                          cwd=root, env=env, text=True, capture_output=True, timeout=20)


def test_demo_preparation_ignores_tmpdir_and_uses_bound_fresh_destination(tmp_path):
    root = tmp_path / 'core'
    core(root)
    env = {**os.environ, 'TMPDIR':str(root), 'TEMP':str(root), 'TMP':str(root)}
    result = demo_call(sys.executable, root, 'demo-prepare', str(root), env=env)
    if os.name == 'nt' and result.returncode != 0:
        pytest.skip('conventional isolated Windows temp directory unavailable')
    assert result.returncode == 0
    prepared = json.loads(result.stdout)
    destination = Path(prepared['runs_root'])
    assert destination.name == 'runs'
    assert destination.parent.name.startswith('claude-ads-demo-')
    assert not destination.exists()
    assert not destination.is_relative_to(root)
    assert prepared['policy_root'] == str(destination / '_policy')
    (root / 'claude_ads_core' / 'cockpit.py').write_text('''def create_demo(destination, policy_root):
    return {"interface_version":"1.0.0", "runs_root":str(destination), "policy_root":str(destination / "_policy"), "steps":[]}
''')
    setup = demo_call(sys.executable, root, 'demo-setup', str(destination))
    assert setup.returncode == 0
    assert json.loads(setup.stdout)['runs_root'] == prepared['runs_root']


def test_demo_loader_refuses_helper_root_substitution(tmp_path):
    root = tmp_path / 'core'
    core(root)
    (root / 'claude_ads_core' / 'cockpit.py').write_text('''def create_demo(destination, policy_root):
    return {"interface_version":"1.0.0", "runs_root":str(policy_root), "policy_root":str(policy_root / "_policy"), "steps":[]}
''')
    allocation = demo_call(sys.executable, root, 'demo-prepare')
    if os.name == 'nt' and allocation.returncode != 0:
        pytest.skip('conventional isolated Windows temp directory unavailable')
    prepared = json.loads(allocation.stdout)
    result = demo_call(sys.executable, root, 'demo-setup', prepared['runs_root'])
    assert result.returncode == 2
    assert json.loads(result.stdout) == {'error':'Trusted core unavailable or configuration unsafe'}
    assert str(root) not in result.stdout


def test_demo_loader_refuses_arbitrary_or_existing_destination(tmp_path):
    root = tmp_path / 'core'
    core(root)
    (root / 'claude_ads_core' / 'cockpit.py').write_text('def create_demo(*args):\n    raise AssertionError("must not enter core helper")\n')
    result = demo_call(sys.executable, root, 'demo-setup', str(root / 'runs'))
    assert result.returncode == 2
    allocation = demo_call(sys.executable, root, 'demo-prepare')
    if os.name == 'nt' and allocation.returncode != 0:
        pytest.skip('conventional isolated Windows temp directory unavailable')
    prepared = json.loads(allocation.stdout)
    Path(prepared['runs_root']).mkdir()
    result = demo_call(sys.executable, root, 'demo-setup', prepared['runs_root'])
    assert result.returncode == 2
