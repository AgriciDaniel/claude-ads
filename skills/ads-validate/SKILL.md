---
name: ads-validate
description: "Validate Claude Ads contracts, scoring inputs, run bundles, capabilities, source freshness, safety, installation, uninstall, or release readiness. Use for ads validate, ads status, ads next, maturity checks, ownership-manifest uninstall, preserving unrelated ads-* skills, checksum verification, preflight, QA, or release audits."
---

# Validate Claude Ads

Choose the narrowest validation target:

- Contract or bundle: use the deterministic core validator.
- Scores: validate controls, findings, category weights, and coverage.
- Run: verify manifest completeness, source lineage, privacy, worker status, and
  render artifacts.
- Capability: require implementation, fixtures, tests, sources, and truthful mode.
- Repository: run deterministic, routing, security, installer, rendering, evidence,
  packaging, and freshness gates.
- Release: dispatch a fresh-context release verifier.

Return machine-readable pass/fail results, the highest-priority blocker, exact
evidence, and recovery steps. Never promote maturity because documentation is
polished or a prior release passed. Stale evidence and skipped remote CI demote
readiness.

Reverify-or-demote decisions belong to `ads-research`. If an expired claim cannot be reverified because source or filesystem access is
unavailable, return a failed current-evidence check, demote that claim for the
current run, and block dependent release-current assertions before asking for the
missing access.

## Install and uninstall validation

An uninstall may remove only exact paths in the matching Claude Ads ownership
manifest. Validate the entire manifest and configured root boundaries before any
deletion. If the manifest is absent, invalid, mismatched, or unsafe, stop before
deleting anything and require manual review. Never discover targets with an
`ads-*` glob; unrelated skills such as `ads-weather` must remain untouched.

Reject pipe-to-shell install instructions. A safe install uses the host's native
installer or a locally inspected checkout/archive; archives require a SHA-256
checksum verified against a trusted release channel before execution.
