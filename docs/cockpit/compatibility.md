# Cockpit compatibility and verification

Claude Ads Cockpit 0.1.0 is an optional companion with runtime plugin ID
`ads-cockpit` and marketplace selector `ads-cockpit@ai-marketing-hub-claude-ads`. The Claude Ads skill and
Python core remain the prerequisite. A skill install does not install or enable
this companion, and the companion archive does not carry Python, the core,
automatic installers, or client runs.

## Binding

Configure an explicit trusted Python executable and a trusted core root. The
root can be this source checkout or a verified standalone skill layout whose
`scripts/claude_ads_core` contains the matching Cockpit implementation and whose
public policy resources are present. An older core with the same product label
may still lack the Cockpit interface. Run Doctor before reading client runs.
There is no PATH search or automatic dependency installation.

The compatibility boundary is the versioned JSON CLI interface
`cockpit doctor`, `snapshot`, `compare`, `action`, and `demo`, with interface
version `1.0.0`. Unknown versions, fields or malformed replies fail closed.
Host views consume cached validated state, not arbitrary run files or shell
commands. A Python wheel alone does not establish that the matching policy
resources or optional report prerequisites exist.

## Evidence levels

| Surface | Acceptance evidence | Current boundary |
| --- | --- | --- |
| Core contracts and local CLI | Focused Python tests and validated JSON replies | Test results must refer to the exact candidate. Structural validation does not prove source truth or advertising performance. |
| Companion control flow | Host-kit tests for trees, actions, selection, refresh and failure handling | Kit success is not proof of terminal pixels or Desktop painting. |
| Optional archive | Allowlist, checksum, deterministic bytes and hostile-path tests | Packaging is separate from installing or loading a mod. A development archive is not an approved release. |
| Public host APIs | Official overview, API and test documentation checked on October 8, 2026; installed CLI reports 2.1.294 | Strict validation and the installed test kit pass. A controlled load to capture exact generated 2.1.294 typings remains pending approval, so native compatibility is provisional. |
| Native terminal/Desktop | Approved live session with visible rendering, keyboard, narrow layout, survey coexistence and cleanup checks | Actual native painting and local preview acceptance are pending. |
| Windows/macOS native host behavior | Native session checks on those operating systems | Unchecked on Linux. The current core client-file defense requires POSIX `O_NOFOLLOW` and descriptor-relative operations; Windows client processing fails closed. Packaging portability does not establish native behavior. |
| PDF | Successful synthetic Markdown, HTML and PDF actions on Linux, with HTML and all three PDF pages visually inspected | Conditional on the trusted environment. Missing dependencies or a failed render produce an unavailable/error receipt; other operating systems and client bundles are not established by this fixture. |

No entry above confers account access. The companion neither calls advertising
APIs nor invokes models, submits prompts, retrieves sources, or installs tools.
It displays dated ledger support. It does not perform new live verification.
All twelve current platform scoring profiles remain disabled, so a successful
view must not invent account-health scores.

The display title remains Claude Ads Cockpit. The runtime ID is `ads-cockpit`
because the installed CLI's strict validator rejects new third-party plugin
names beginning with `claude-`. The existing main plugin retains its identity.
The public package contains original narrow declarations, not private vault
captures or host-generated types. In a source checkout, see the
[verification report](verification.md) for exact commands, findings and remaining
gates. That candidate-specific report is repository-only material.

## Reports and old runs

Markdown, HTML and conditional PDF reports use the canonical report bundle. PDF
depends on the optional renderer in the matching trusted Python environment and
native libraries. Neither the companion package nor Doctor installs them. Only a
successful action receipt and its existing output files establish that a report
was generated. A kit node, report button, or saved filename does not establish a
successful PDF render.

A compatible run needs both canonical `manifest.json` and the strict
`cockpit-index` v1 `cockpit.json`. Legacy runs with no index are incompatible;
the companion does not guess contracts from content or scan unregistered client
files. Comparisons require matching account/platform identity and disclose
window, scope, input, policy and evaluation-date differences. An absent finding
means not retested, never automatically resolved.

## Release boundary

Local checks, a synthetic demo, ordinary CI and API documentation are distinct
from fresh native acceptance and the full release gate. This workbench is not
market-ready or release-ready until the applicable product, privacy, security,
external model evaluation, independent review and exact-subject remote CI gates
pass. See [release requirements](../../control-plane/RELEASE_REQUIREMENTS.md).
