import { MESSAGES } from './lexicon.mjs';
// Deliberately fixed code and argv: no shell and no PATH lookup, because argv[0] is the configured
// absolute interpreter. The child still inherits the host environment and the session working
// directory; `-I -S` (below) is what isolates Python from PYTHON* variables, the current directory,
// user site packages and executable .pth files.
export const PYTHON_LOADER = `import sys, pathlib, json, tempfile, sysconfig, os
root = pathlib.Path(sys.argv[1])
def safe_root(p):
    if not p.is_absolute() or any(q.is_symlink() for q in (p, *p.parents)):
        raise ValueError("unsafe configured root")
    return p.resolve(strict=True)
try:
    root = safe_root(root)
    candidates = [root, root / "scripts"]
    base = next((p for p in candidates if (p / "claude_ads_core" / "__init__.py").is_file()), None)
    if base is None:
        raise ValueError("core package unavailable")
    package = base / "claude_ads_core"
    for item in package.rglob("*"):
        if item.is_symlink():
            raise ValueError("unsafe core package")
    # -I -S excludes environment, cwd, user sites and executable .pth files.
    # Expose dependency directories only from the explicitly trusted interpreter.
    executable = pathlib.Path(sys.executable)
    venv = executable.parent.parent
    config = venv / "pyvenv.cfg"
    if config.exists():
        if config.is_symlink() or not config.is_file():
            raise ValueError("unsafe interpreter configuration")
        dependency_base = safe_root(venv)
        paths = sysconfig.get_paths(vars={"base": str(dependency_base), "platbase": str(dependency_base)})
    else:
        dependency_base = pathlib.Path(sys.prefix).resolve(strict=True)
        paths = sysconfig.get_paths()
    for name in ("purelib", "platlib"):
        candidate = pathlib.Path(paths[name])
        if not candidate.exists():
            continue
        candidate = candidate.resolve(strict=True)
        if not candidate.is_dir() or not candidate.is_relative_to(dependency_base):
            raise ValueError("unsafe interpreter dependencies")
        if str(candidate) not in sys.path:
            sys.path.append(str(candidate))
    sys.path.insert(0, str(base))
    from claude_ads_core.cli import main
    argv = sys.argv[2:]
    if len(argv) in (1, 2) and argv[0] == "demo-prepare":
        # Do not let ambient TMPDIR place synthetic fixtures inside client runs.
        temp_base = pathlib.Path("/tmp") if os.name != "nt" else pathlib.Path(pathlib.Path(sys.base_prefix).anchor) / "Windows" / "Temp"
        temp_base = pathlib.Path(temp_base).resolve(strict=True)
        protected = [root] + ([pathlib.Path(argv[1]).resolve()] if len(argv) == 2 else [])
        if not temp_base.is_dir() or any(temp_base == p or temp_base.is_relative_to(p) for p in protected):
            raise ValueError("isolated temporary directory unavailable")
        parent = pathlib.Path(tempfile.mkdtemp(prefix="claude-ads-demo-", dir=temp_base))
        destination = parent / "runs"
        print(json.dumps({"interface_version": "1.0.0", "runs_root": str(destination), "policy_root": str(destination / "_policy")}))
        raise SystemExit(0)
    if len(argv) == 2 and argv[0] == "demo-setup":
        from claude_ads_core.cockpit import create_demo
        destination = pathlib.Path(argv[1])
        parent = safe_root(destination.parent)
        if destination.name != "runs" or not parent.name.startswith("claude-ads-demo-") or destination.exists():
            raise ValueError("unsafe demo destination")
        value = create_demo(destination, root)
        if value.get("runs_root") != str(destination) or value.get("policy_root") != str(destination / "_policy"):
            raise ValueError("mismatched demo destination")
        print(json.dumps(value, ensure_ascii=True))
        raise SystemExit(0)
    raise SystemExit(main(argv))
except (ValueError, OSError, ImportError):
    print(json.dumps({"error":"Trusted core unavailable or configuration unsafe"}))
    raise SystemExit(2)
`;
const ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const SHA = /^[a-f0-9]{64}$/;
const OPERATIONS = new Set(['validate-input', 'validate-run', 'render-report']);
// The platform decides what "absolute" means. POSIX accepts only a rooted path, so a drive letter or a
// UNC path can never become a relative argv[0]. Windows keeps its rooted and drive-letter forms.
const hostPlatform = () => (typeof globalThis.process?.platform === 'string' ? globalThis.process.platform : 'linux');
export function absolutePath(value, platform = hostPlatform()) {
  const common = typeof value === 'string' && value.length > 1 && value.length <= 4096
    && !/[\x00-\x1f\x7f]/.test(value)
    && !value.split(/[\\/]/).some(x => x === '..' || x === '.');
  if (!common) return false;
  return platform === 'win32' ? /^\//.test(value) || /^[A-Za-z]:[\\/]/.test(value) : /^\/(?!\/)/.test(value) && !value.includes('\\');
}
export function binding(options) {
  const config = { coreRoot: options?.coreRoot, pythonExecutable: options?.pythonExecutable, runsRoot: options?.runsRoot || null };
  if (!absolutePath(config.coreRoot) || !absolutePath(config.pythonExecutable)
      || (config.runsRoot !== null && !absolutePath(config.runsRoot))) {
    throw new Error(MESSAGES.setup);
  }
  return config;
}
function id(value) {
  if (!ID.test(value || '')) throw new Error(MESSAGES.badId);
  return value;
}
export function buildArgv(config, command, request = {}) {
  const prefix = [config.pythonExecutable, '-I', '-S', '-c', PYTHON_LOADER, config.coreRoot];
  if (command === 'prepare-demo') return [...prefix, 'demo-prepare', ...(config.runsRoot ? [config.runsRoot] : [])];
  if (command === 'demo') {
    if (!absolutePath(request.runsRoot) || request.policyRoot?.replaceAll('\\','/') !== request.runsRoot.replaceAll('\\','/').replace(/\/$/, '') + '/_policy') throw new Error('Invalid isolated demo destination.');
    return [...prefix, 'demo-setup', request.runsRoot];
  }
  if (!['doctor', 'snapshot', 'compare', 'action'].includes(command)) throw new Error('Unsupported local operation.');
  const policyRoot = request.policyRoot || config.coreRoot;
  const runsRoot = request.runsRoot || config.runsRoot;
  if (!absolutePath(policyRoot) || (runsRoot && !absolutePath(runsRoot))) throw new Error('Invalid local root.');
  const args = ['cockpit', command, '--policy-root', policyRoot];
  if (runsRoot) args.push('--runs-root', runsRoot);
  if (command !== 'doctor') {
    if (!runsRoot) throw new Error(MESSAGES.runs);
    args.push('--run-id', id(request.runId));
  }
  if (command === 'compare') args.push('--baseline-id', id(request.baselineId));
  if (command === 'action') {
    if (!OPERATIONS.has(request.operation) || !SHA.test(request.fingerprint || '')) throw new Error('Action unavailable without a current fingerprint.');
    args.push('--operation', request.operation, '--expected-fingerprint', request.fingerprint);
    if (request.operation === 'validate-input') args.push('--input-id', id(request.inputId));
    if (request.operation === 'render-report') { const format = request.format || 'markdown'; if (!['markdown','html','pdf'].includes(format)) throw new Error('Unsupported report format.'); args.push('--format', format); };
  }
  return [...prefix, ...args];
}
