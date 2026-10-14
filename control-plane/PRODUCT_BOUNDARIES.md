# Product Boundaries

## Buyer and promise

Claude Ads serves agencies, consultants, and in-house paid-media teams that
need repeatable, evidence-backed audits, plans, creative workflows, monitoring,
experiments, and reports across major advertising platforms.

It turns authorized exports or account reads into normalized observations,
findings, recommendations, and client-ready deliverables. It is advisory and
read-only by default.

## Supported product surface

- Primary runtime: Claude Code through `/ads` for a standalone skill install or
  `/claude-ads:ads` for the necessarily namespaced plugin install.
- Portable surface: Agent Skills-compatible runtimes and a matching CLI where
  executable support exists.
- Target platforms: Google, Meta, YouTube, LinkedIn, TikTok, Microsoft, Apple,
  Amazon, Reddit, Pinterest, Snapchat, and X Ads.
- Cross-platform workflows: attribution, tracking, creative, landing pages,
  budgeting, forecasting, experiments, competitor research, policy, privacy,
  and regulatory review.
- Canonical machine output: versioned JSON. Human formats are renderings of the
  same run bundle.
- Optional companion: Claude Ads Cockpit (`ads-cockpit`) projects validated
  local runs, evidence and comparisons. Its explicit local actions validate
  registered inputs or runs and render reports with receipts. It is separately
  enabled, does not confer account authority, and retains disabled scoring.
  Native terminal and Desktop acceptance must be recorded separately from
  automated element-tree tests.

## Non-promises

- A skill file is not proof of a working integration.
- A benchmark is not a guarantee of future performance or platform approval.
- A recommendation is not legal, tax, accounting, or investment advice.
- Claude Ads does not bypass platform policy, consent requirements, access
  controls, or geographic restrictions.
- Claude Ads does not infer missing account facts and present them as observed.
- Claude Ads does not guarantee live read or write support for every platform.
  Availability is declared per capability and adapter.
- Claude Ads does not produce platform health from an audit checklist alone.
  Disabled scoring profiles yield no health score; watchlist findings remain
  unscored until their evidence and severity contract is approved.
- Claude Ads does not permanently delete campaigns or account objects in v2.
- Claude Ads does not publish client data, raw private research, captured
  prompts, or credentials.

## Mutation boundary

Account writes are disabled unless the platform capability is independently
enabled and a mutation plan contains an exact before/after diff, object IDs,
owner, approval record, idempotency key, blast-radius limit, verification
window, audit destination, and rollback procedure. Missing budget or policy
ceilings block the write. Pause or archive is preferred to deletion.

## Evidence boundary

Current platform, API, policy, specification, regulation, and benchmark claims
must point to dated entries in the source and claim ledgers. Stale, contested,
practitioner, and single-source evidence must be labeled. Unknown and
not-applicable are valid outputs and must not be converted into passes.
