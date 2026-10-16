# Claude Ads Cockpit 0.1.0

An optional local workbench for Claude Ads runs. The five screens are Overview,
Checks, Inputs, Compare and Reports. They use plain language and theme colors,
and show recorded step state, the checks a run made, dated source support,
indexed inputs, run differences and local report receipts. On screen, a "check"
is one canonical finding, a "step" is one worker of the run and the "engine" is
the local Claude Ads core. The guided demo uses synthetic fixtures in an isolated
run root and policy copy.

The Claude Ads skill and matching Python core are prerequisites. This companion
does not bundle Python or the core, install dependencies, grant advertising
account permissions, call models, retrieve sources, or change campaigns. The
ordinary skill installer does not install or enable it.

## Explicit setup

The runtime plugin ID is `ads-cockpit`; the display title is Claude Ads Cockpit.
Select it separately after reviewing the package and verifying its checksum
against a trusted channel. For the Claude Ads marketplace, its explicit install
selector is `ads-cockpit@ai-marketing-hub-claude-ads`. Selecting or installing the
main skill does not select this companion. Exact host API and native rendering
acceptance are still pending.
No real profile needs to be changed to inspect the source or run kit tests.

Set the host's companion configuration fields:

| Field | Value |
| --- | --- |
| `coreRoot` | Explicit trusted absolute source checkout or verified standalone skill root containing the matching core and public policy resources. |
| `pythonExecutable` | Explicit trusted absolute Python executable. Never a command found through PATH. |
| `runsRoot` | Optional explicit absolute root containing compatible local runs. Required for client data commands; isolated demo supplies its own root. |

Both required fields default to blank. Set them with
`claude plugin configure ads-cockpit` (or the plugin's options in `/plugin`).
Until `coreRoot` and `pythonExecutable` are valid absolute paths for the host
platform, every entry point (chooser, demo, band and `doctor`) says "Not set up
yet" and names the two options; it never prints a configured path. A drive letter
or UNC path is not accepted on macOS or Linux. The manifest declares all three
fields as plain strings. `claude plugin validate --strict` also accepts the
`directory` and `file` types on 2.1.296, but how the options dialog treats a
blank default or an optional path was not exercised here, so they stay strings
and the launcher is the check on every path.

Run `/ads-cockpit doctor` and inspect its compatibility status before opening
client runs. It does not install or
repair anything. A compatible run needs canonical `manifest.json` and strict
`cockpit-index` v1 `cockpit.json`; missing indexes are reported as incompatible.

## Commands and local actions

| Command | Result |
| --- | --- |
| `/ads-cockpit` | Open the local run chooser. |
| `/ads-cockpit open <id>` | Select a registered run by its safe run ID. |
| `/ads-cockpit demo` | Explicitly create and enter the isolated synthetic demo. |
| `/ads-cockpit hide` | Hide the pane, cancel refresh and clear displayed client state. |
| `/ads-cockpit doctor` | Check the explicit binding and compatibility. |

The only run actions are `validate-input`, `validate-run` and `render-report`.
They require the selected run's current authorization fingerprint and operate
on local files. Report formats are Markdown, HTML and conditional PDF. PDF needs the optional
renderer and system libraries in the configured trusted environment; an absent
dependency or render failure must produce a clear unavailable/error receipt. A receipt records success, failure or blocking without proving
advertising truth.

Keys: the tabs answer to 1 to 5, and the footer keys are r refresh, c runs,
d details, h hide (demo: b back, n next, z reset, q exit). Screens fit the
rows the pane has and never scroll: j shows the next page of a long list, u the
previous one, and f filters Checks by result. A framed button names
its key in its label, for example `Next (n)`, `Markdown (m)`, `HTML (l)`,
`PDF (p)` and `Check whole run (k)`, because the terminal draws a key only on a
plain button. Keys act while the pane or band holds focus (ctrl+x tab).

Views use cached state. A visible pending/running run refreshes at five-second
intervals without overlapping requests, and only while the pane is placed and
shown; a closed, undrawn or background pane starts no process. When a turn ends,
a pending run is refreshed in the background without delaying the turn, and a
finished run spawns nothing. Hiding or reloading cancels refresh.
No pane opens automatically. Demo entry/exit clears client state, and leaving
the demo returns to the chooser. The demo is an example, not client evidence.

## Optional package and rollback

From a reviewed source checkout, build a separate development archive:

```sh
python scripts/package_cockpit.py --root . --output-dir dist/cockpit-review package
python scripts/package_cockpit.py --root . --output-dir dist/cockpit-review verify
```

Choose a fresh output directory; existing output files are never overwritten.
The ZIP has one `ads-cockpit/` root and contains a fixed allowlist of companion
runtime files, this README,
its original state declaration and MIT license. It excludes Python/core files,
generated host typings, tests, transcripts, raw captured evidence, client runs,
private vault material and repository-only release evidence. A packaging test
checks that every relative import in those files resolves inside the allowlist.

The two install routes differ. The ZIP above is the reviewed, allowlisted
package. The marketplace entry `ads-cockpit` has the source
`./mods/claude-ads-cockpit`, which installs the whole directory as committed,
including `tests/`, `tsconfig.json` and `types/` beside the runtime files; only
the generated host typings under `.claude-plugin/types/` are git-ignored. The
extra files are never loaded as hooks, but they are on disk. The accompanying
manifest and SHA-256 file contain relative paths and hashes. Building does not
install, load, enable or publish the companion. Reproducible bytes do not make a
development archive an approved release.

The demo writes synthetic runs to a new `claude-ads-demo-<random>` folder under
the system temp directory (`/tmp` on macOS and Linux). The cockpit never deletes
these folders, because cleanup would need host reach it does not have. Hide the
cockpit first, then remove only folders with that prefix when you no longer need
them. They hold made-up data only.

Rollback starts with `/ads-cockpit hide`, then disable the companion through the
host's plugin controls. To uninstall, remove only this companion's separately
selected package using that host's ownership-aware removal flow. If the host
cannot show exact owned files, stop for manual review. Retain the core, skill,
client run directories and generated reports/receipts. No broad skill-name glob
or profile cleanup is needed.

For source-checkout documentation, see the [user guide](../../docs/cockpit/user-guide.md),
[compatibility limits](../../docs/cockpit/compatibility.md) and
[proposed roadmap](../../docs/cockpit/roadmap.md). These guides are repository
resources and are not copied into the small optional archive. Local kit checks
cannot establish terminal/Desktop painting, Windows/macOS native behavior,
market readiness or product release readiness.

## What is and is not verified

Verified here by `claude plugin validate --strict` and `claude plugin test`
(Claude Code 2.1.296): the manifest, the static hook inventory, drawing-tree
validity on terminal and Desktop surfaces, hook behavior with stubbed host
calls, and launcher isolation tests on Linux. Not verified: real terminal or
Desktop painting, Windows and macOS behavior, the options dialog, and how a live
`--plugin-dir` session behaves. Test stubs stand in for the host, so none of
these checks loaded the mod in a real session.
