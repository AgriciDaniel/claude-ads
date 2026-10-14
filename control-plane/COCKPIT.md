# Optional Cockpit producer interface

Claude Ads Cockpit 0.1.0 has the separately enabled plugin ID `ads-cockpit`.
The main skill installers carry this public producer contract and the matching
Python core, but do not install or load the companion.

Bind an explicit trusted Python executable, core root and client runs root.
The source checkout stores `claude_ads_core` at its root. A standalone skill
stores it under `scripts/claude_ads_core`, with policy resources at the skill
root. `cockpit doctor` checks compatibility before client processing. There is
no ambient working-directory or PATH discovery.

Each selected run requires canonical `manifest.json` and a `cockpit-index` v1
`cockpit.json`. Its exact fields are `schema_version`, `run_id`, `phase`, `inputs`
and `artifacts`. Input rows declare `id`, `path`, `kind`, `contract`, `platform`
and `sha256`; artifact rows declare `id`, `path`, `contract` and `sha256`. Paths
are relative to the selected run. Declare immutable, hashed canonical artifacts
before publishing metadata. Do not register generated Cockpit history as inputs.

At an actual producer boundary call
`claude_ads_core.cockpit.publish(runs_root, run_id, policy_root, manifest, index,
expected_fingerprint=current_fingerprint)`. An uninitialized run omits the
fingerprint; updating an existing run requires its current snapshot fingerprint.
Readers and the publisher share a per-run lock. Metadata publication preserves
recovery bytes. An interrupted publication marker blocks further processing
until an operator restores a verified, consistent manifest/index pair.

The CLI provides `cockpit doctor`, `snapshot`, `compare`, `action` and `demo`.
Data operations require an explicit `--runs-root`, selected `--run-id` where
applicable, and a verified policy binding (`--policy-root`). The three client
actions are `validate-input`, `validate-run` and `render-report`; rendering
supports Markdown, HTML and conditional PDF. Actions require the current
`--expected-fingerprint` and write unique reports and receipts under the run's
`cockpit/` directory. Reopened snapshots validate and expose saved history.

The companion cannot approve controls, assign severity, enable scoring, infer
missing accounts, refresh source evidence, or confer account authority. Every
scoring profile in the scoring manifest remains disabled. A receipt records the local
operation and its outcome, not advertising truth or account permission.

Legacy runs without an index need explicit producer adoption. There is no
automatic scan or conversion. Demo setup creates a fresh synthetic destination
and separate policy copy, never client inputs. Current secure client IO requires
POSIX descriptor APIs; non-POSIX client processing fails closed. Native terminal
and Desktop rendering acceptance is separate from automated kit checks.
