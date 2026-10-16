# Claude Ads Cockpit user guide

Cockpit is an optional local daily workbench for inspecting a Claude Ads run,
reviewing its evidence and inputs, comparing a prior run, and recording local
validation/report actions. It reads the versioned core contracts. The skill and
core remain usable without the companion.

## Bind a trusted core

Review the source or verify a separately obtained package before selecting the
companion through the host's local plugin flow. Its runtime plugin ID is
`ads-cockpit`, display title Claude Ads Cockpit, and marketplace install selector
`ads-cockpit@ai-marketing-hub-claude-ads`. The main skill does not select it.
Exact host API compatibility and live native acceptance remain pending.

Configure `coreRoot` and `pythonExecutable` as explicit trusted absolute paths.
Use this source checkout or a verified standalone skill root with the matching
Cockpit-enabled core and public policy resources. A standalone skill stores the
core under `scripts/claude_ads_core`; a source checkout stores it directly under
`claude_ads_core`. A version string alone does not establish compatibility.
`runsRoot` is optional until opening client runs. The companion searches neither
PATH for Python nor arbitrary directories for code, and it installs nothing.

Until both fields are set the pane, the demo, the band and Doctor say "Not set
up yet" and name `coreRoot` and `pythonExecutable`. Set them with
`claude plugin configure ads-cockpit`. The practice demo needs both fields;
`runsRoot` is needed only for real runs.

Run `/ads-cockpit doctor` first. Doctor checks compatibility and available local
run summaries without exposing client bodies or installing dependencies. A run
folder that has a manifest but cannot be read safely appears as Blocked instead
of being omitted. On non-POSIX hosts Doctor reports an unsupported platform. Repair
missing prerequisites separately through the existing reviewed skill setup
workflow. Never paste credentials into these configuration fields. Pass fully resolved
paths (for example from `realpath`): a symlink in any part of a root path is
refused.

For direct CLI use from a trusted source checkout, the commands below use a
Python executable already selected by you. Set `CORE_ROOT`, `TRUSTED_PYTHON`,
`RUNS_ROOT`, and `RUN_ID` to your approved local paths and run ID. For a standalone
layout, run Python from the skill's `scripts` directory instead of its root.
These are local CLI examples, not installation instructions:

```sh
cd "$CORE_ROOT"
"$TRUSTED_PYTHON" -m claude_ads_core cockpit doctor \
  --policy-root "$CORE_ROOT" --runs-root "$RUNS_ROOT"
"$TRUSTED_PYTHON" -m claude_ads_core cockpit snapshot \
  --policy-root "$CORE_ROOT" --runs-root "$RUNS_ROOT" --run-id "$RUN_ID"
"$TRUSTED_PYTHON" -m claude_ads_core cockpit compare \
  --policy-root "$CORE_ROOT" --runs-root "$RUNS_ROOT" \
  --run-id "$RUN_ID" --baseline-id "$BASELINE_ID"
```

CLI replies are JSON. Exit code 0 means the command produced its JSON reply. For
an action, that reply is a receipt, and its `outcome` field (succeeded, failed or
blocked) carries the result, so a stale or blocked action still exits 0. Exit
code 2 means the request was rejected before any receipt existed, for example an
unsafe path, an invalid ID, a busy run or an unavailable lifecycle, and the
reply is a bounded public diagnostic. `snapshot` and `compare` accept `--as-of YYYY-MM-DD` as an
explicitly labeled evaluation-date override. The default is current UTC.
Changing an evaluation date does not refresh a source or create new evidence.

## Prepare a compatible run

The configured runs root contains one directory per safe run ID:

```text
runs-root/
  review-001/
    manifest.json
    cockpit.json
    inputs/export.csv
    artifacts/report-bundle.json
```

`manifest.json` must satisfy canonical RunManifest v1. `cockpit.json` is a strict
`cockpit-index` v1 object with required `schema_version`, `run_id`, `phase`,
`inputs` and `artifacts`. Unknown fields or versions fail closed. The run ID
must match the selected run. Phase is a string or null.

Each input row contains `id`, run-relative `path`, `kind` (`json` or `csv`),
`contract` (a registered contract name or null), `platform` (canonical ID or
null), and `sha256`. Each artifact row contains `id`, `path`, `contract` and
`sha256`. Nested paths are allowed. Contract-backed artifacts use registered
contracts such as `report-bundle`, `audit-worker-result` and orchestration
contracts. An input with no declared contract does not acquire one by inference.

Publish canonical manifest/index updates through the core's validated atomic
publisher. Hashes, artifact references and contracts must agree before the
companion trusts them. The UI shows actual worker/phase updates produced by
that workflow; it cannot manufacture progress. Orchestration supersession
chains remain canonical. A missing index yields an incompatible-run diagnostic.
There is no glob scan of unregistered client files and no automatic legacy-run
conversion.

The producer API is `publish(runs_root, run_id, policy_root, manifest, index,
expected_fingerprint=None)` in `claude_ads_core.cockpit`. Create immutable,
hash-bound artifact files first, then call it at the recorded workflow boundary.
For an existing initialized run, pass the current snapshot fingerprint. The
publisher validates the pair under the same per-run lock used by readers and
preserves prior metadata in `cockpit/recovery/`. A crash between metadata
renames leaves a marker that blocks further reads until the producer reviews
and restores a consistent pair. It does not infer or advance a worker's state.
No automatic polling of arbitrary audit folders substitutes for producer setup.

A run whose retention has expired, whose deletion is verified, that is
restricted, or that has an open incident is never written to, so no receipt is
created for it.

Keep client runs outside the repository. Respect their existing classification,
retention, encryption and access rules. Cockpit does not delete client data to
satisfy a retention deadline; a lifecycle restriction may block an action.
Reads and writes reject symlink, traversal, root escape and nonregular-file
cases. Integrity failures are errors, not partially trusted snapshots.

## Open and navigate

Use `/ads-cockpit` for the chooser or `/ads-cockpit open <id>` for a registered
run. `/ads-cockpit hide` hides the pane and clears displayed state. No pane
opens automatically. Nonvisual replies contain safe status only.

| Screen | What it shows |
| --- | --- |
| Overview | One plain-language verdict with a button to the next step, a coverage bar (how many applicable checks had enough data, and how they came out), a meter per platform when the run has several, a meter per topic (quality score, tracking, keywords and so on, worst first), the first checks to fix with the step that fixes each, what needs your input, and the scoring state. Desktop and VS Code add a coverage donut. |
| Checks | Every check with its plain-language name. A large audit shows one line per check, grouped by platform and worst first; open one for its card: what was seen, the diagnosis, what to do next, the evidence count and how current its claims and sources are. |
| Inputs | What the workers are waiting for and a checklist of registered input files, each with a Check button. Missing or tampered input cannot appear validated. |
| Compare | A selected compatible baseline, the disclosed differences and a before and after table per control. |
| Reports | Buttons to make Markdown, HTML or conditional PDF reports, the saved files, and the history of local action receipts. |

Every screen uses the same words for the same states ("Waiting for your input",
"Out of date", "Not scored"). Raw status values from the core never reach the
screen. Keys: 1 to 5 switch screens, r refreshes, c lists runs, d shows or hides
details (short fingerprints, ledger entries, notes on limits), h hides the pane,
g follows the verdict card's suggested next step. Every screen is drawn to fit
the rows the pane has, so it never scrolls: lists show what fits, j and u move
to the next and previous page, and f narrows Checks to fails, unknowns or
passes. A taller pane shows more of the same screen: a short pane keeps the verdict, coverage, topics and first fixes, and a taller one adds platforms, inputs and notes. An opened check is a three-sentence card (what we saw, what it means, what to do); d adds severity, evidence and sources. For the most room, use a fullscreen terminal at least 110 columns wide, where the pane docks at full height. Colors come from your theme, so
the pane follows light and dark. Buttons that have a key show it in their label,
for example `Next (n)`. Desktop and VS Code add small SVG graphics; the
terminal uses text bars.

The pane uses cached state. Only a shown, selected pending/running run polls
at five-second intervals, and a turn end refreshes only a run with pending work. Requests do not overlap, hide/reload cancels polling,
and stale refresh results must not replace a newly selected run. Relevant turns
may request a fresh snapshot. Navigate through host keyboard controls; surveys
and other bands retain their host precedence. Narrow/fallback views and native
painting still require an approved host acceptance session.

A claim labeled current reflects dated ledger support, not live reverification.
Missing, expired, demoted or contested dependencies remain visible. Every
production scoring profile in the scoring manifest is disabled, so no platform
health score should be invented. Completeness, coverage and evidence confidence answer
different questions.

## Compare cautiously

Comparisons require the same account/platform identities. Raw account IDs are
not exposed; account keys are derived from actual identity. A mismatch is
rejected. The comparison discloses scope, date-window, policy, input and
evaluation-date differences that affect interpretation.

Changes can be new failure, new finding, newly unknown, not retested, status
changed or unchanged. A control absent from the new run is not retested; absence
never proves resolution. A comparison is not causal evidence, an experiment
readout, a comparable-conversion total or an uplift claim.

## Run the three local actions

Only these operations are permitted:

| Operation | Required context | Local effect |
| --- | --- | --- |
| `validate-input` | Selected indexed input ID and current snapshot fingerprint | Checks that input against its declared structure/contract and records a receipt. |
| `validate-run` | Selected run and current snapshot fingerprint | Checks indexed run integrity/contracts and records a receipt. |
| `render-report` | Canonical report bundle and current snapshot fingerprint | Renders from that bundle and records output hashes plus a receipt. |

Report formats are Markdown, HTML and conditional PDF. PDF requires the
optional renderer and native libraries in the configured trusted environment.
An absent prerequisite or rendering failure must produce a clear unavailable or
error receipt. The companion does not install those prerequisites or establish
their availability from a version label. A visible button, kit response or
filename does not prove a report rendered successfully.

Copy the fingerprint from the latest snapshot. If inputs or policy changed,
refresh before trying again; an old fingerprint blocks the action. UI selection
and double-click guards do not replace that core check. Example CLI action:

```sh
"$TRUSTED_PYTHON" -m claude_ads_core cockpit action \
  --policy-root "$CORE_ROOT" --runs-root "$RUNS_ROOT" --run-id "$RUN_ID" \
  --operation validate-input --input-id "$INPUT_ID" \
  --expected-fingerprint "$FINGERPRINT"
"$TRUSTED_PYTHON" -m claude_ads_core cockpit action \
  --policy-root "$CORE_ROOT" --runs-root "$RUNS_ROOT" --run-id "$RUN_ID" \
  --operation render-report --format markdown \
  --expected-fingerprint "$FINGERPRINT"
```

The Reports view rediscovers validated saved receipts and their report outputs
when a run is reopened. It displays each operation, outcome, timestamps, input
and policy fingerprints, diagnostics, and output hashes. Historical fingerprints
can differ from the latest snapshot and do not authorize new actions.

Generated outputs are new files under `cockpit/reports/<unique-id>/` and
`cockpit/receipts/<unique-id>.json` within the selected run. Existing artifacts
are never overwritten. A run keeps at most 1000 listed items, counting
registered files, receipts and rendered reports, within 64 MiB. Past that,
snapshot, compare and action refuse. To continue, move older files from
`cockpit/receipts` and their reports from `cockpit/reports` out of the run
folder, then refresh. Receipts are local records, not tamper-proof; report files
are hash-checked. A recoverable per-run lock serializes actions. Reports
and receipts are excluded from the authorization fingerprint. Receipt outcomes
are succeeded, failed or blocked; failures remain visible and do not imply
advertising truth, account permissions or a passed audit.

## Try the isolated demo

Run `/ads-cockpit demo` explicitly. Demo preparation is a setup command, separate
from the three client-run actions. It creates fixture-only runs under a fresh
isolated destination and uses a separate policy copy with disabled profiles.
Client state clears on entry and exit. Demo actions are restricted to that
fixture root and policy; leaving demo returns to the chooser.

The walkthrough has eight steps. Step 1 opens a full synthetic audit of four platforms (28
checks with a mix of pass, fail and unknown results, some out-of-date support, and one
failed platform) so you can see a populated run. The keyword story then starts with
missing keyword evidence, opens its indexed
input, and moves to a separate corrected fixture containing positive and
negative keywords. Use **Check** on the input to record the local result. The remaining
steps show expired support, a partial worker, a comparison against the unknown
result, and report creation with a receipt. Each step shows a short coaching line
below a PRACTICE DATA banner. Next, Back and Reset navigate this
walkthrough; generated demo reports and receipts remain in its isolated root. The
companion does not delete the demo folder (`claude-ads-demo-*` under the system
temp directory); remove it yourself when finished.
The G14 keyword finding is explicitly precomputed synthetic content. The local
check validates its declared input contract; it does not run a live keyword
diagnosis or establish that an advertising account improved.

The direct CLI equivalent creates a fresh destination that must not exist:

```sh
"$TRUSTED_PYTHON" -m claude_ads_core cockpit demo \
  --policy-root "$CORE_ROOT" --runs-root "$FRESH_DEMO_ROOT"
```

Use only the returned demo root, policy root and step IDs for demo follow-up
commands. Reusing an existing destination is refused. Synthetic fixtures are
not proof of client outcomes, enabled scoring, account connectivity or live
source checks. The demo is not started by ordinary install or Doctor.

## Recover or remove the companion

For an incompatible reply, unsafe path, timeout or stale action, run Doctor,
check the trusted binding, and refresh the selected run. Repair input/index
problems at their authorized producer. Preserve failed receipts. A process error
must not display raw stderr, client bodies or configured absolute paths.

To roll back the companion, hide it, disable it through host plugin controls,
and use the host's ownership-aware removal flow for its exact package. Retain
the Claude Ads core, skill and run directories, including generated reports and
receipts. If exact ownership is unavailable, stop for manual review rather than
broad deletion. The existing skill uninstall does not manage this separately
selected companion. See [compatibility](compatibility.md) for verification limits.
In a source checkout, `docs/cockpit/verification.md` records the local
candidate's checks and `docs/cockpit/roadmap.md` contains proposals outside v1.
Those two source-only documents are excluded from distribution archives, so
they are not linked here.
