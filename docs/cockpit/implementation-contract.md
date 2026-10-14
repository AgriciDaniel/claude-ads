# Cockpit implementation contract v1

This document freezes the integration boundary for the optional companion.
All implementation is original. API research is external; no private vault code,
transcripts, generated session material, or local paths belong in this repository.

## Ownership

The conductor owns cli.py, contracts.py registration, shared manifests, CI,
root documentation integration and final verification. The core worker owns
new cockpit Python modules, cockpit schemas, core tests, and sanitized fixtures.
The interface worker owns the companion except its README. The packaging worker
owns the companion README, user guide, packaging helper and packaging tests.
Workers must preserve others' changes. No commits or installs.

## Core call boundary

Functions in claude_ads_core.cockpit:

- doctor(policy_root, runs_root=None) -> dict, including interface_version="1.0.0",
  status, core_version, profile summary, and runs (safe id/status rows). A directory
  holding a manifest that cannot be read safely or fails validation is listed with
  status blocked and counted in diagnostics, never omitted. Without POSIX O_NOFOLLOW,
  doctor returns status blocked with an unsupported-platform diagnostic.
- snapshot(runs_root, run_id, policy_root, *, as_of=None) -> Snapshot.
- compare(runs_root, run_id, baseline_id, policy_root, *, as_of=None) -> Snapshot
  with comparison populated. Reject different account/platform identities.
- action(runs_root, run_id, policy_root, operation, *, expected_fingerprint,
  input_id=None, format="markdown") -> Receipt. Only validate-input,
  validate-run and render-report. Fingerprint is mandatory for every action.
- create_demo(runs_root, policy_root) -> {interface_version, runs_root,
  policy_root, steps:[{run_id,title,baseline_id,tab}]}. Caller supplies a fresh
  isolated demo destination. Refuse an existing destination. Fixture-only,
  explicit-user setup, no client inputs; no enabled profiles. This setup helper
  is a `cockpit demo` subcommand, not an extra client action operation.
- CockpitError(ValueError): bounded public diagnostics, no raw data or absolute
  paths. Functions accept Path or str; CLI emits JSON. Exit 2 means the request was
  rejected before any receipt existed (unsafe or invalid input, unavailable lifecycle,
  busy run). Exit 0 means the command produced its JSON reply; for `action` that reply
  is a receipt whose outcome field (succeeded, failed or blocked) carries the result,
  so a blocked or failed action still exits 0.

CLI subcommands: cockpit doctor/snapshot/compare/action/demo. --policy-root is
explicit or uses existing resolver; every data command takes --runs-root.
--run-id selects the current run; --baseline-id selects comparison; action uses
--operation, --expected-fingerprint, optional --input-id and --format.
--as-of YYYY-MM-DD is an explicitly labeled evaluation-date override for
snapshot/compare only. Default uses current UTC. Demo prepares fixtures only on
an explicit command. Doctor is read-only; it never installs or probes PATH code.

## Run layout

Each selected root contains <run-id>/manifest.json (canonical RunManifest v1),
plus cockpit.json, a strict versioned index: schema_version, run_id, phase
(string or null), inputs and artifacts. Input rows: id,path,kind(json/csv),
contract(string or null),platform(string or null),sha256. Artifact rows:
id,path,contract,sha256. Paths are run-relative; nested paths are permitted.
Contract rows identify report-bundle, audit-worker-result, or existing
orchestration contracts. Artifact references and SHA-256 must agree before use.
No glob-based parsing of unregistered client files. Missing index produces a
clear incompatible-run diagnostic. Never infer an input contract from contents.
An atomic publisher helper validates the index and manifest, and exposes actual
worker/phase updates for workflow producers. UI cannot manufacture progress.
Orchestration result chains must use canonical supersedes/subject validation.

Generated reports and receipts go under cockpit/reports/<unique-id>/ and
cockpit/receipts/<unique-id>.json within the run. Receipt and report directories
are not inputs to the authorization fingerprint. Do not overwrite existing
artifacts. All reads/writes reject symlink, traversal, nonregular-file and root
escape cases. A symlink in any ancestor of a root is refused too (for example
/home -> var/home or macOS /tmp); callers pass the fully resolved path. Readers use bounded input sizes and verify changes between read
and use. Serialize per-run actions with an exclusive, recoverable local lock.
Honor data-lifecycle deletion/retention restrictions without deleting client data.
A lifecycle-refused run (expired, verified deletion, restricted, open incident) is
never written to: action raises the lifecycle diagnostic before taking the lock, so
no lock file, receipts directory or receipt is created. A stale fingerprint on an
allowed run still yields a blocked receipt.

## Snapshot wire shape

All listed keys are required; unknown versions/fields fail closed. Arrays can be
empty. Strings displayed in the terminal are redacted and control-character safe.

schema_version="1.0.0", artifact_type="cockpit-snapshot", run_id, evaluated_at
(UTC timestamp), fingerprint (sha256), policy_fingerprint (sha256), privacy_class,
phase (string|null), completeness (complete|partial|failed), workflow_status
(pending|running|completed|blocked|failed|unknown), workers, accounts, findings,
claims, sources, inputs, artifacts, receipts, scoring, permitted_actions, limitations,
comparison (object|null).

- workers: id, platform (canonical id|null), status (canonical worker status),
  result_status (ok|needs_input|blocked|failed|null), missing_inputs,
  contradictions, stale_sources, recovery_hints (string arrays).
- accounts: platform, account_key (hash of actual identity, no raw account id),
  window {start,end}, currency. account_key is an unsalted SHA-256 of
  {platform, account_id}. It stays stable so compare can match runs, which also
  means it is linkable across runs and brute-forceable for short or numeric
  account IDs. It is a comparison key, not anonymization. Snapshots are not
  persisted by the core or the companion.
- findings: platform, account_key, finding (canonical Finding v1, redacted for
  display), severity (registry-owned), claim_ids, source_ids, evidence_status
  (current|stale|demoted|missing|contested|provisional).
- claims: id, statement, verdict, classification, last_verified, refresh_due,
  effective_status, source_ids, control_ids.
- sources: id,title,locator (eligible public URL|null),retrieved_at,refresh_due,
  confidence,status,claim_ids,control_ids. No retrieving sources from the mod.
- inputs: indexed input fields plus validation (unchecked|valid|invalid|missing)
  and details (safe string array). Missing/tampered references cannot be treated
  as validated. Fatal integrity errors return an error, not a trusted snapshot.
- artifacts: path,kind,sha256,size. Paths relative to run; no raw contents.
- receipts: path,sha256,size,receipt (canonical Cockpit action receipt v1).
  Discover only bounded designated run-local receipt files, validate their run,
  operations and output hashes, and expose generated outputs in artifacts.
  Historical input/policy fingerprints may differ from current. Generated
  history never enters the input authorization fingerprint. Report outputs are
  hash-bound: a receipt-listed report whose bytes or size differ is fatal.
  Receipts are local records, checked for schema, subject, name and time but not
  hash-bound, so a receipt edited into another valid receipt is not detected.
  Receipts are not a tamper-proof audit trail. History is bounded: at most 1000
  listed artifacts (registered files plus receipts plus reports) and 64 MiB; past
  that, snapshot, compare and action refuse and ask the user to archive older
  receipts from cockpit/receipts and reports from cockpit/reports out of the run.
- scoring: platform,health_score,evidence_coverage,status,profile_status.
  Recompute using canonical registry. All current profiles remain disabled.
- permitted_actions: subset of three operation names. Empty for unavailable work.
- comparison: baseline_run_id,comparable (bool),differences (string array),
  findings [{platform,control_id,change,baseline_status,current_status}].
  change: new_failure|new_finding|newly_unknown|not_retested|status_changed|unchanged.
  Status fields are Finding statuses or null. Scope/window/policy/input/evaluation
  differences are disclosed. Absence never means resolved. No uplift claims.

Evidence status reflects dated ledger support, not a new live verification.
Future/inverted dates, missing dependencies, demotions and expired supporting
sources cannot yield current evidence. Refresh_due equality follows existing
repository semantics. Do not parse free-text evidence as a file path or command.

## Action receipt wire shape

schema_version="1.0.0", artifact_type="cockpit-action-receipt", action_id,
run_id, operation, started_at, finished_at, outcome (succeeded|failed|blocked),
input_fingerprint, policy_fingerprint, outputs [{path,sha256,size}], diagnostics
(string array). Strict validation, no client bodies or absolute paths. A failed
render/check records the failure; receipts never imply advertising truth.

## Companion binding and behavior

Plugin id ads-cockpit (host rejects new third-party claude- prefixes), display title Claude Ads Cockpit, version 0.1.0. /ads-cockpit has open <id>, demo,
hide, doctor. No arguments opens chooser. Config binds an explicit trusted core
root and Python executable (no PATH search), and optional runs root. Use the
source checkout or verified standalone layout; a compatibility probe must pass
before client reads. Core invocation uses fixed argument arrays and a fixed
isolated Python launcher. UI views use cached state only. Five tabs: Run,
Evidence, Inputs, Compare, Reports. Nonvisual replies contain safe status only.

Five-second refresh only while a selected pending/running run is visible;
nonoverlapping; cancel on hide/reload; refresh after relevant turns. No auto pane
opens, model calls, tool interception, prompt submits, or network calls.
Compose other bands, yield to surveys, keyboard navigation, narrow layouts,
explicit error states. Clear client state on demo entry/exit; demo return goes
to chooser. Demo actions call only the isolated fixture root and policy copy.
Use session state, never persist client payloads. UI action double-clicks and
stale asynchronous refreshes must not act on a different selected run.

## Verification

Core schema/validator parity, dates/expiry, canonical scores for all twelve
platforms, identity/comparison changes, stale fingerprints, lifecycle, receipts,
concurrent actions, unsafe paths, redaction, demo isolation and malformed input.
Mod kit: terminal/Desktop tree and controls, narrow/fallback, surveys/other bands,
hide/reset/clear, stale selections, timeout/errors and local process allowlist.
Packaging: optional plugin isolation, manifest/allowlist consistency, fixtures,
no generated typings/transcripts/private data, and ownership-safe uninstall.
Real native painting is a separate approved-session check, never inferred from
kit tests. Windows/macOS native behavior remains unchecked on Linux.
