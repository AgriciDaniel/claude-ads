# Claude Ads Control Plane

This directory is the public-safe contract layer for Claude Ads v2. It records
what the product is allowed to claim, what it can actually do, which evidence
supports it, how work is coordinated, and what must pass before release.

The design is a clean-room synthesis of source-first research discipline,
capability honesty, progressive disclosure, reversible operations, and
fresh-context verification. It contains no copied private prompts, captured
system text, account exports, credentials, or raw private corpus.

## Contracts

- `PRODUCT_BOUNDARIES.md`: buyer, promise, supported workflows, and explicit
  non-promises.
- `PUBLISHING_POLICY.md`: private/public classification and publication gate.
- `RELEASE_REQUIREMENTS.md`: maturity, testing, security, packaging, and remote
  CI requirements.
- `schemas/`: JSON Schema Draft 2020-12 contracts.
- `schemas/independent-review-evidence.schema.json` and
  `schemas/review-trust-bundle.schema.json`: externally signed release-review
  contracts; repository templates cannot satisfy the gate.
- `manifests/`: current product, evidence, capability, safety, orchestration,
  maturity, and ecosystem-review state.
- `manifests/data-lifecycle-policy.json`: versioned classification, minimum
  retention, encryption, access, deletion-verification, and incident rules. The
  matching schema is `schemas/data-lifecycle-policy.schema.json`; per-run values
  use `claude_ads_core/schemas/v1/data-lifecycle.schema.json`.
- `manifests/control-registry.json` and `manifests/scoring-profiles.json`: the
  exhaustive typed audit catalog and fail-closed platform health state. A named
  check is not scoreable unless its versioned profile is enabled.

Schema `$id` values use stable `urn:ai-marketing-hub:claude-ads:schema:*`
identifiers. They are identifiers, not network locations. The tracked files in
`claude_ads_core/schemas/v1/`, `control-plane/schemas/`, and `evals/schemas/`
are the canonical validation resources.

## Doctrine

1. No source, no current claim.
2. No implementation, fixture, and test, no capability claim.
3. No approval and rollback, no account mutation.
4. No independent verification path, no release.
5. Staleness, security failures, or broken evaluations demote maturity.

Manifests are release inputs, not marketing copy. A planned capability must be
marked `declared` or `disabled`; only verified behavior may be marked
`fixture-verified` or `live-verified`.

The dependency-free core also validates strict v1 workflow artifacts for setup,
brand, planning, creative/copy, generation, monitoring, experiments, and mutation
plans. These contracts establish structure only; they do not prove source truth,
platform eligibility, provider availability, account authority, or approval.
File-backed orchestration uses immutable run, task, result, and artifact-only gate
packets. Reruns require an explicit `supersedes` chain.

Ecosystem dispositions may use `metadata-only` for issue or pull-request
metadata and independently reimplemented concepts. This does not approve
copying a patch or establish contributor rights. `same-project-mit` records a
separate review of MIT-covered patch use. Tracker titles and links provide
attribution; raw issue text, private discussion, and patches do not belong in
the disposition ledger.

The current catalog is operational for discovery findings, not account-health
grading. All twelve scoring profiles are disabled until per-control source
support, severity decisions, typed inputs, weights, and regression evidence are
approved together.

Run `python scripts/release.py gate` with the exact canonical-model report,
external signed review directory, reviewer public-key trust bundle, implementation
principal list, and GitHub Actions run ID. The emitted assessment conforms to
`schemas/release-gate-report.schema.json` and fails closed when any input is
missing, stale, unsigned, mismatched, incomplete, or unsuccessful.

Canonical model evidence uses separate externally trusted runner and evaluator
keys. Supply the model trust bundle and implementation-principal exclusions via
the `CLAUDE_ADS_MODEL_EVAL_*_JSON` environment variables documented in
`RELEASE_REQUIREMENTS.md`; no repository file is a trust root.

Run `python -m claude_ads_core status --root . --as-of YYYY-MM-DD` for the
repository-artifact status, or replace `status` with `next` for exactly one
deterministically selected blocker. Both commands are offline and fail closed.
