# Claude Ads Cockpit local verification

Evaluation date: October 8, 2026. This is an uncommitted development candidate
on `codex/ads-cockpit-v1`. Local implementation and verification are distinct
from native host qualification, publication and product release acceptance.

## Subject and scope

The managed feature worktree starts from maintenance candidate
`558c977ffc0c709992fdcf192e62b37599d170be`. Public `main` remains
`ac21644933910419529bcf81efb95a9ca71edf81`. GitHub PR #89 was rechecked during
handoff: open, draft, unmerged, with the same maintenance head. The primary and
maintenance checkouts are preserved. No feature commit or remote update was made.

The companion display title is **Claude Ads Cockpit**, version **0.1.0**. Its
runtime ID and marketplace entry are **ads-cockpit**. The installed Claude Code
2.1.294 strict validator rejects new third-party plugin names prefixed
`claude-`, so the runtime ID differs from the planning name. The source
directory remains `mods/claude-ads-cockpit/`.

Delivered behavior includes the status band; Run, Evidence, Inputs, Compare and
Reports views; explicit local actions and saved receipts; safe core binding;
and the isolated walkthrough. The eight-step demo opens with a full synthetic four-platform audit (28 checks, unscored), then starts with missing keyword
evidence and a corrected input, then shows stale support, a partial worker,
comparison and report generation. Its G14 finding is explicitly precomputed
synthetic content. Input validation is structural, not a live keyword diagnosis.

The Python core remains authoritative. Snapshot, action-receipt and run-index v1
contracts reject unknown versions and inconsistent subjects. The index is an
additional producer contract: legacy folders without one require explicit
adoption. No automatic scan or conversion is performed. The companion requires
the matching core and public policy resources; it does not install either.

Production scoring profiles, control registry and capability manifest are byte
identical to the maintenance baseline. Every scoring profile in the manifest remains disabled.
Health remains null and approved coverage zero. Completion counts, structural
validity, evidence confidence and advertising health are separate concepts.

## Verification results

The baseline Python 3.11 suite passed with **829 passed, 33 skipped**. The final
candidate uses Python 3.11.15 and 3.12.13. The 3.12 test environment was created
locally and installed from the runtime, development and schema-test locks with
`--require-hashes --only-binary=:all:`. No production dependency changed.

| Check | Command or method | Result |
| --- | --- | --- |
| Full Python 3.11 suite | `python -m pytest tests -q -ra --junitxml=...` | 1,017 passed, 33 skipped, 0 failures/errors, 239.23s |
| Full Python 3.12 suite | `python -m pytest tests -q -ra --junitxml=...` | 1,017 passed, 33 skipped, 0 failures/errors, 236.08s |
| Independent core/story regression | `python -m pytest tests/core/test_cockpit_demo_story.py tests/core/test_cockpit.py tests/core/test_cockpit_contracts.py tests/core/test_companion_cli.py -q` | 146 passed; final G14 binding and unchanged source-policy bytes independently checked |
| Strict companion validation | `claude plugin validate mods/claude-ads-cockpit --strict` | Passed on installed CLI 2.1.294 |
| Host test kit | `claude plugin test mods/claude-ads-cockpit` | 169 passed, 0 failed, across three files (after the fourth pass below) |
| Isolated launcher integration | `python -m pytest mods/claude-ads-cockpit/tests/test_launcher_integration.py -q` | 8 passed |
| Companion packaging regression | `python -m pytest tests/release/test_cockpit_packaging.py tests/release/test_optional_marketplace.py -q` | 42 passed (32 packaging, 10 marketplace), also included in the full suites |
| Repository and sensitive-content audit | `python scripts/release.py audit --include-untracked` | Passed, including task-created files and JavaScript/TypeScript text |
| Dependency audit | Hash-pinned audit environment running `python scripts/audit_dependencies.py` | Passed; 0 unhandled advisories, 3 existing machine-checked `not_affected` advisory exceptions for 1 package |
| Environment integrity | `python -m pip check` | No broken requirements |
| Syntax | `bash -n install.sh uninstall.sh`; `python -m compileall -q claude_ads_core evals scripts tests mods/claude-ads-cockpit/tests` | Passed |
| Whitespace and final diff | `git diff --check` plus explicit review of new files | Passed |
| Standalone layout | Actual matching core and curated public resources copied into a temporary standalone layout, trusted isolated launcher invoked from an unrelated directory | Doctor passed, all 12 profiles disabled; no real profile installation |
| Optional archive | Two independent package builds and `package_cockpit.py verify` on each | Byte-identical; the curated runtime files only (22 at this check) |

Each full suite's 33 skips are environmental: 25 require PowerShell, 4 require
Windows PowerShell 5.1, 1 requires a managed Windows install target, and 3 require
Windows ACL, sharing or file-identity semantics. They are not treated as passes.
Native Windows/macOS behavior was not executed. Current secure client-file
processing requires POSIX descriptor operations and fails closed on unsupported
hosts.

The final test-only POSIX marker was also checked by rerunning the story test
(1 passed). It preserves the documented fail-closed boundary on unsupported hosts.

The full suites cover contracts and schema parity, identity and policy drift,
tampered files, scoring spoof attempts, comparison scope/window differences,
omitted controls, local action outcomes, lock contention, timeouts,
interruption, atomic publication recovery, freshness dates and demoted support,
hostile paths, escaping, report semantics, installation and packaging.

The kit exercises all five views at widths 34 and 72 on terminal and Desktop
test surfaces. It covers controls, cached render purity, subject binding,
keyboard assignments, hiding, clear/reload cancellation, surveys, other bands,
nonvisual responses, polling recovery and demo isolation. These are element
tree and interaction checks. They do not establish how the native application
paints, scrolls, focuses or composes these elements.

## Independent findings and dispositions

Fresh read-only reviews reproduced consequential defects, returned them to
their owners, and rechecked the repairs. The final review found no remaining
blocker within the authorized local and kit scope.

| Finding | Disposition and evidence |
| --- | --- |
| Comparison could infer identity for a platform without an actual bound account | Rejected. Adversarial same/different account and missing-account cases reproduced and regression-tested. |
| Duplicate account identity could disagree on window or currency | Rejected before projection/comparison. Both conflict cases are covered. |
| Failed/blocked/needs-input orchestration could retain complete status | Completeness now downgrades to partial; recorded worker results remain visible. |
| Oversized numeric input could escape bounded validation | Finite-number validation rejects overflow; CLI and failed-receipt paths are covered. |
| Saved report/receipt history disappeared on reopening | Bounded, hash-verified history is projected into snapshots and Reports, with run, timestamp, filename, output and subject validation. |
| Renderer subprocesses inherited client/lock descriptors or exceeded an aggregate host deadline | Children close inherited client/policy/lock descriptors; every report shares one 20-second render deadline. Normal interruption/timeout writes a receipt and reaps the child. |
| Date redaction could obscure ISO dates | Canonical dates remain readable while sufficiently long phone-like numbers are redacted. |
| Stale command continuations could reopen hidden UI or overwrite a new selection | Generation/selection checks apply after awaits; hide, clear, reload and demo changes invalidate prior work. |
| Comparison or action replies could carry the wrong subject | Baseline, run, input and policy subjects are checked before accepting data. |
| Disabled numeric health or fabricated coverage could be rendered | Core recomputes canonical policy, wire rejects inconsistent disabled scores, and views defensively withhold health. |
| Polling could stop permanently after a transient refresh failure | A pending run retains retry scheduling; actions stay disabled until a fresh snapshot is accepted. |
| Demo helpers could substitute roots or inherit client-selected temporary paths | Two-stage allocation uses a fixed conventional temporary base, verifies returned roots and clears client state. |
| Status band, contextual routes, input hashes and actual evidence were incomplete | All four surfaces completed and independently probed, with zero effects during rendering. |
| P2: a retained action callback could target a newly selected run | Every action captures its rendered run/input/policy subject. Independent probes rejected all 18 stale combinations with zero core calls and accepted all 6 current controls. |
| P3: an input ID could match letters inside an ordinary word | Complete case-sensitive token matching; free-text matches are labeled as text, not structured links. Short-ID negative cases independently reproduced. |
| Demo did not tell the agreed missing-keyword/corrected-input story | Separate missing and corrected runs now exercise real failed/succeeded input checks, comparison, report creation and rediscovered receipts. |
| P2: keyword fixture finding used campaign-naming control G01 | Both story runs now bind canonical keyword-governance control G14, with a third isolated synthetic claim/source and matching manifest references. |

An interim demo edit added a second account input to an existing test scenario
and caused 12 regressions in window/platform mutation fixtures. The corrected
story was moved to its own run, preserving the existing scenario and its
security checks. Focused and full-suite reruns passed after that correction.
The original generic demo and control-binding gaps were acceptance findings,
not production platform diagnoses.

## Real reports and package evidence

The final isolated G14 story exercised a missing-input failure receipt, a
corrected-input success receipt and successful Markdown, HTML and PDF renders.
Reopening recovered all four corrected-run receipts and preserved the
authorization fingerprint. All scores remained null with zero coverage.

The HTML was rendered in headless Chromium at 1280 pixels wide, with all
subresource requests blocked: zero requests occurred and there was no horizontal
overflow. Its full screenshot and all three A4 PDF pages were inspected.
Dates, the synthetic diagnosis, G14, "Not scored" and zero coverage were
readable without clipping. PDF was produced with WeasyPrint 70.0 and local
native prerequisites. This proves that fixture in that environment. PDF remains
conditional elsewhere; unavailable-dependency and failed-render paths are tested.

The curated companion archive excludes Python/core files, tests, client runs,
private source material, transcripts, reviews and generated host typings. It
contains the manifest, original license/readme, six hook/runtime files and
original narrow state declarations. The archive is a development artifact:

```text
ads-cockpit-0.1.0.zip
SHA256 e04040a279d3f2bebd493b1e3be68987ab046d3a27bb23e20876d70366949438
```

The main skill installers do not load this companion. They carry the public
producer guide, matching core and policy resources through the existing curated
ownership mechanism. The companion has a separate marketplace entry and its
own runtime allowlist. Existing upgrade/uninstall tests remain in the full suite.

Official host overview, API and testing documentation was checked on the
evaluation date and recorded as metadata-only sources and scoped claims.
Documentation and kit results do not establish exact generated host typings or
native compatibility. No private captured implementation or prompt material
was copied into this candidate.

## Remaining acceptance and release gates

Native terminal and Desktop qualification is pending explicit owner approval
for a controlled live load. An original display-only fixture was prepared and
statically validated. The installed CLI reports 2.1.294; exact generated current
typings have not been captured. No `claude --plugin-dir` session, real-profile
installation or live native companion load was performed. Actual painting, keyboard/scroll
usability, live narrow layout, native survey coexistence and reload cleanup
remain unchecked. Host-kit coverage does not substitute for that session.

Main release packaging correctly refused the uncommitted worktree. The release
gate reported failure for clean subject, canonical external model evaluation,
trusted signed independent reviews and exact-subject remote CI. Its tracked-only
repository audit also fails while new companion files are untracked; the
explicit tracked-plus-new audit passes. Source/capability, vulnerability-exception
and ecosystem integrity checks passed. The gate assessment refers to HEAD, not
to a committed version of this uncommitted feature.

No model evaluations, external signed reviews, remote CI runs, commits, pushes,
merges, publication, real account operations or spending were performed. The
read-only local reviewers do not satisfy the external signed-review gate.
Uncatchable process termination cannot guarantee a final receipt or child
reaping; ordinary handled timeouts and interrupts are covered. Exhaustive
filesystem race behavior across every filesystem remains unchecked.

## Evidence and rollback

Raw local test logs, JUnit results, synthetic report bytes, screenshots, package
manifests and hash records are retained under the ignored build evidence root,
`.claude-ads/runs/cockpit-build-20261008/`. Final orchestration packets use
canonical task/result/gate contracts and public source/test metadata. Their
artifact-only local acceptance gate is separate from the unmet native and
product release gates. Synthetic lifecycle seeds do not establish infrastructure
encryption or real-client privacy acceptance.

No real profile was changed, so there is no installed companion to remove for
this handoff. Preserve the managed feature worktree for review; archive it through
the managed-worktree flow only when the owner no longer needs the candidate.
For a separately approved future install, hide and disable the exact
`ads-cockpit` plugin, then remove only its owned package. Keep the Claude Ads
skill/core and every client run, report and receipt. Do not use broad directory
deletion as an uninstall substitute.

## Interface redesign (October 8, 2026)

After a first look at the native terminal, the plain-text interface was judged too
hard to read. The views were rebuilt without changing the core, wire contracts,
launcher, action binding or controller data flow. New modules: `theme.mjs`
(semantic tones mapped to theme keys), `lexicon.mjs` (one plain-language source),
`model.mjs` (shared derived facts and the verdict), `kit.mjs` (cards, chips, bars,
tables), `screens/*.mjs` (one per screen), `band.mjs` and `svg.mjs` (desktop and
VS Code graphics). The only controller change is a view-only `details` toggle that
hide resets.

Checks run on the redesigned views: the host kit (136 passed) validates every
screen on the terminal and desktop surfaces at widths 34, 72 and 160, and
`claude plugin validate --strict` passes. Pure tests cover no overflow at widths 34
to 160 in both modes, that no raw wire word reaches the screen, that every wire status
has a plain-language entry, an element prop allowlist with theme colors only, unique
control keys, the spoofed-health guard, and the existing stale-click and subject
checks. The curated archive list and its packaging tests (50 passed) were updated.

Not established: how the native terminal and Desktop actually paint these elements.
`tests/render-text.mjs` approximates layout as text and cannot show color or the
host's exact button chrome. The redesign still needs a visual check in the real host.

### Second pass: richer demo and plain check names

Feedback on the first redesign was that it looked plain, the demo was too thin and it was
hard to understand. The demo now starts with a full synthetic audit (`demo-showcase`: four
platforms, 28 checks, each with its own synthetic support, some expired, one failed
platform, every scoring profile still disabled). The snapshot gained a required
`control_title` per finding (the registry's public intent text, redacted and capped at 200
characters), added to the core, the schema, the wire check and the fixtures. The views gained
number tiles, a colored results bar, a per-platform strip of squares, a short "Needs
attention" list and a compact grouped Findings list for large audits. Verified: the host kit
(138 passed), strict validation, and the core cockpit, contract and schema tests. Native
painting of the new elements is still unverified.

### Third pass: independent review and fixes (October 11, 2026)

Four independent read-only reviews (core, mod, tracked-file edits, upstream issue and pull
request triage) found real defects, which were then fixed and re-verified. Core: actions no
longer write into lifecycle-refused runs, receipt history is counted once with an actionable
limit message, doctor lists unreadable runs and reports an unsupported platform, display
redaction keeps URLs and colliding keys, the portable validator rejects a trailing newline
and non-RFC 3339 times, and a failed demo cleans up its own destination. Mod: first-run
setup is explained in plain words, a turn end refreshes only pending work without waiting,
polling stops while the pane is not shown, keys are shown on framed buttons, button labels
are sanitized, input check keys are unambiguous, tables fit narrow widths, and packaging has
an import-closure test. Skill text now publishes Cockpit metadata only when the user asks for
Cockpit or a Cockpit index already exists.

Verified on Python 3.12: full test suite 1053 passed and 33 skipped (Windows and PowerShell
cases), host kit 162 passed, strict plugin validation, launcher and packaging tests, two
byte-identical package builds that verify, compile check, and the repository audit with
`--include-untracked` (the plain audit passes only once the companion files are tracked).
Still unverified: native terminal and Desktop painting, Windows and macOS behavior, remote
CI, the model-evaluation gates and an independent signed review.

### Fourth pass: screens that fit, a story Overview and a plainer demo (October 16, 2026)

Feedback from a real terminal was that the panes scrolled, were clipped and were hard to
grasp. Every screen is now drawn to the rows the pane has (`scroll.bodyRows`), so none
scrolls: long lists are paged (j next, u previous), Checks can be filtered (f), an opened
check is a three-sentence card (d adds severity, evidence and sources), and a short pane
keeps only the verdict, coverage, topics and first fixes. The Overview now shows how much of
the audit could be judged, a meter per platform and per topic (topics are a display grouping
derived from each check's id and title, because the registry leaves most controls
unclassified), and the first checks to fix with the step that fixes each. New module:
`pack.mjs` (fits blocks into a line budget). The demo has one plain headline per step.
A real-terminal screenshot exposed a defect that text previews cannot show: an unset style
value erased the tone color on every colored line part. It is fixed and a test now asserts
that tones reach the drawn Text. Bar glyphs were changed to block characters because the
terminal font drew the earlier ones as thin shapes.

Verified: the host kit (169 passed), strict plugin validation, the launcher, packaging and
marketplace tests, and a text-render matrix (3560 renders across six pane sizes, every tab
and mode) with none over its row budget. The demo was walked end to end with the real
engine, including input checks and Markdown, HTML and PDF reports. Not established: how the
Desktop and VS Code surfaces paint the coverage donut, and Windows and macOS behavior.
