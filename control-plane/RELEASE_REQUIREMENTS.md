# Release Requirements

These gates are cumulative. A release candidate is demoted when a load-bearing
source expires, a critical security or privacy finding opens, a declared
capability loses its test evidence, or required remote CI does not pass.

## Product and contract gates

- Buyer, promise, commands, outputs, boundaries, privacy defaults, and mutation
  authority are documented consistently.
- Public schemas have semantic versions and fixtures. Breaking changes require
  a major schema version and migration notes.
- Capability status matches implementation, adapter, fixture, and test evidence.
- Every complete-audit claim reports module completeness and evidence coverage.
- Health, evidence confidence, regulatory exposure, and opportunities remain
  separate outputs.
- Every catalog ID has one typed registry disposition. Only an enabled versioned
  profile may supply health controls and category weights; health controls require
  verified load-bearing claims, non-zero reviewed severity, explicit inputs, and
  stable status. Disabled profiles must fail closed without a health score.

## Evidence gates

- Every load-bearing platform, API, policy, regulation, benchmark, or creative
  specification claim has a claim ID and at least one dated source ID.
- Official, regulator, standards-body, or primary sources are preferred.
- Practitioner evidence is labeled and cannot alone establish mandatory policy
  or compliance behavior.
- API, policy, feature, and creative-specification sources refresh within 30
  days; regulation receives event-driven review plus a 30-day check near an
  effective date; benchmarks refresh quarterly; foundational methods refresh
  within 12 months.
- Overdue load-bearing sources block release until refreshed or the dependent
  claim and capability are demoted.

## Safety and privacy gates

- Writes are disabled by default and capability-gated by platform.
- Mutation lifecycle tests cover preview, approval, apply, repeated apply,
  verify, failure, audit, and rollback.
- URL, redirect, DNS, browser-subresource, output-path, symlink, archive, and
  parser-differential defenses pass adversarial tests.
- Untrusted content cannot change instructions or mutation authority.
- Secrets and personal data are absent from tracked files, fixtures, reports,
  logs, task packets, archives, and Git history.
- Data classification, redaction, retention, encryption, and deletion behavior
  are documented and tested.
- Dependency advisories are fixed or have expiring, machine-checked
  `not_affected` evidence bound to the exact package version and unused code
  path. New advisories, accepted-risk dispositions, import drift, or expired
  evidence fail closed. Every referenced evidence path must remain in the
  public release package.

## Evaluation gates

- Schema, scoring, normalization, missing-data, deduplication, routing, and
  report-rendering suites pass.
- Every target platform has sanitized export fixtures and failure cases.
- Routing and safety regressions pass at 100 percent.
- Model evaluations reach at least 90 percent overall with no P0 safety failure
  and no unintended regression against retained v1 behavior.
- The canonical model gate consumes complete external Claude Code run evidence
  for both the exact candidate commit and pinned retained-v1 subject. Candidate
  and baseline use the same CLI and model snapshot, a fresh process per case,
  no conversation reuse, no mutation authority, and an evaluator independent
  of the run executor.
- Local schema, suite, and assessor checks never substitute for either external
  model run. Missing, stale, non-Claude, self-graded, hash-mismatched, partial,
  or runtime-incomparable evidence fails closed. Keep raw responses private and
  retain only the redacted deterministic gate report as ignored, external
  release evidence. It must not alter the exact Git subject it verifies or enter
  the product archive.
- Each model run requires separate runner and evaluator Ed25519 signatures over
  the exact subject, runtime, case receipts, rubric judgments, and result. Supply
  external trust and implementation-principal exclusions through
  `CLAUDE_ADS_MODEL_EVAL_TRUST_BUNDLE_JSON` and
  `CLAUDE_ADS_MODEL_EVAL_IMPLEMENTATION_PRINCIPALS_JSON`. Repository-local,
  forged, stale, role-mismatched, self-signed, or self-review evidence fails closed.
- A fresh-context verifier confirms completion claims from artifacts and test
  output, not from the implementation conversation.

## Installation and packaging gates

- Python-wheel resolution, install, upgrade, and uninstall are tested on the
  declared Linux, macOS, and Windows interpreter tuples. This is not a claim of
  cross-platform Playwright browser or WeasyPrint PDF feature execution.
- Installation does not silently mutate global Python or execute unverified
  network content.
- Uninstall removes only ownership-manifest entries and leaves no unowned files.
- A clean checkout reproducibly builds the release archive, release manifest,
  SHA-256 checksums, SBOM, and license notices.
- Runtime and development locks use exact versions plus the union of publisher
  wheel hashes for every declared CPython 3.11/3.12 Linux, macOS, and Windows
  target. Installers use `--require-hashes --only-binary=:all:`, run `pip check`,
  and fail before mutation when the interpreter target is not in that matrix.
- The CycloneDX release SBOM contains the application and runtime closure only;
  the separate development lock/inventory remains audit evidence, not an
  application dependency.
- Playwright browser payloads and WeasyPrint native/system libraries are modeled
  in `control-plane/manifests/external-runtime-dependencies.json`; they remain
  outside the Python lock/SBOM. Browser execution requires separate host/payload
  attestation. Real PDF rendering is smoke-tested on the Ubuntu full-test job,
  not across the full wheel matrix.
- Archive paths are portable and contain no invalid, absolute, or traversal
  names.

## Merge and release gate

- Required GitHub Actions checks pass on the integration commit. Local success
  does not substitute for unavailable, skipped, or billing-blocked remote CI.
- The integration branch receives independent code, evidence, security,
  privacy, and licensing review.
- Review evidence conforms to the independent-review schema, binds the exact
  commit and tree, and verifies under externally provisioned Ed25519 public keys.
  Pending templates and repository-local trust roots cannot satisfy this gate.
- No critical blocker remains in the ecosystem disposition ledger.
- Only after all gates pass may the reviewed branch merge and receive a v2 tag.
- Repository visibility remains private; public release requires the separate
  gate in `PUBLISHING_POLICY.md`.

## Independent-review evidence protocol

The files in `control-plane/manifests/reviews/` are pending, unsigned templates,
not approvals. Completed review evidence stays outside the checkout and release
archive because findings and evidence locators may be internal.

Independent reviewers bind their documents to the full commit and tree IDs and
sign canonical UTF-8 JSON with Ed25519 after omitting only
`authentication.signature_b64url` (sorted keys, no insignificant whitespace, no
ASCII escaping). Supply public reviewer keys through
`CLAUDE_ADS_REVIEW_TRUST_KEYS_JSON`, implementation reviewer IDs through
`CLAUDE_ADS_IMPLEMENTATION_PRINCIPALS_JSON`, and the external evidence directory
through `CLAUDE_ADS_REVIEW_EVIDENCE_DIR`. Private keys must never enter the
checkout, verifier, logs, or artifacts.

Run `python scripts/review_evidence.py --root .`. Missing external state,
subject mismatch, stale or duplicate evidence, pending/rejected decisions,
invalid or mis-scoped keys, self-review, open critical/high findings, and
accepted-risk findings without a separate owner gate fail closed. The verifier's
redacted digest report may feed release metadata; raw review documents may not.
