# Meta Ads audit control catalog

<!-- Catalog IDs preserved from the legacy runtime; current platform facts require dated source or account evidence. -->

## Runtime evaluation contract

- Start with objective, geography, account type, campaign type, data window, conversion lag, sample size, and feature access.
- Return `not_applicable` when the surface or requirement does not apply and `unknown` when the required evidence is absent.
- A conditional control can affect health only when current account evidence, owner-defined economics, and an applicable official source establish the expectation.
- Product adoption, availability, beta access, announcement awareness, and vendor-reported performance are not health controls. Record them only as unscored discovery.
- Do not use fixed platform-wide thresholds, broad benchmarks, launch dates, sunset dates, or universal network, bidding, budget, audience, creative, or attribution rules from this catalog.
- Validate mutable facts at run time. A confirmed policy, support-state, or migration requirement needs its own current claim coverage before it can create a finding.

## Source coverage boundary

The October 7, 2026 refresh verified the exact public Conversions API,
Insights, and campaign Insights reference pages. CLM-0008 and CLM-0202 cover
only those documented foundations. Daily Insights rows require
`time_increment=1`; the native scalar projection excludes action arrays.
Documentation and fixtures do not establish an authenticated account request,
consent state, matching quality, deduplication health, or account health.

The general Marketing API overview and Reels source remain unverified
for current claims. Meta engineering architecture sources were checked
separately and do not prove measurement or creative requirements.

The registered sources below cover only the measurement, API, and import foundations stated in the claim ledger. They do not support every named product or control in this catalog. Until a narrower current claim exists, treat those names as routing labels and gather fresh official or in-account evidence.

## Official evidence

- `meta-marketing-api-official`: [Meta Marketing APIs documentation](https://developers.facebook.com/docs/marketing-apis/)
- `meta-conversions-api-official`: [Meta Conversions API overview](https://developers.facebook.com/documentation/ads-commerce/conversions-api)
- `meta-capi-deduplication-official`: [Handling duplicate Pixel and Conversions API events](https://developers.facebook.com/docs/marketing-api/conversions-api/deduplicate-pixel-and-server-events)
- `meta-graph-api-versions-official`: [Graph API and Marketing API versions](https://developers.facebook.com/docs/graph-api/changelog/versions)
- `meta-graph-api-v26-changelog-official`: [v26.0 changelog](https://developers.facebook.com/docs/graph-api/changelog/version26.0)
- `meta-v26-launch-blog-official`: [Introducing Graph API v26.0 and Marketing API v26.0](https://developers.facebook.com/blog/post/2026/07/29/introducing-graph-api-v26-and-marketing-api-v26/)

- `meta-insights-reporting-official`: [Meta Insights reporting](https://developers.facebook.com/documentation/ads-commerce/marketing-api/insights)
- `meta-campaign-insights-reference-official`: [Meta campaign Insights reference](https://developers.facebook.com/documentation/ads-commerce/marketing-api/reference/ad-campaign-group/insights)

## API version status verified 2026-10-12

Meta released Graph API and Marketing API `v26.0` on 2026-07-29 (`CLM-0221`).
The `v24.0` expiry that Meta lists, 2026-10-06, has passed, so do not treat a
pinned `v24.0` integration as supported. Meta lists changes that extend to all
remaining Marketing API versions on 2026-10-27, including the Messenger Stories
placement value, web-only destinations on Website and App campaigns, and poll-ad
creation. Verify the version an integration pins before reporting an error or a
removal.

From `v26.0`, creating Housing, Employment, or Financial Products and Services
(special category) ad sets with relaxable targeting in a non-broad setup requires
`targeting_automation.advantage_audience` to be set explicitly to `1` or `0`;
omission is rejected. Meta's launch post limits this to ad set creation, not to
updates of existing ad sets, and earlier versions follow only after `v25.0` is
deprecated, so do not report a missing flag on an existing ad set as a failure.
The Pixel redundancy and deduplication wording (matching `event_id` and
`event_name`) is on the deduplication page, not the Conversions API overview
(`CLM-0008`).

## Control registry

| ID | Audit intent | Runtime disposition |
|---|---|---|
| M01 | Meta Pixel installed | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M02 | Conversions API applicability and status | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M03 | Event deduplication | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M04 | Event Match Quality diagnostics | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M05 | Domain verification | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M06 | Aggregated measurement applicability | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M07 | Standard events vs custom | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M08 | CAPI Gateway | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M09 | iOS attribution window | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M10 | Data freshness | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M25 | Creative format diversity | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M26 | Creative concept coverage | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M27 | Video aspect ratios | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M28 | Creative fatigue detection | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M29 | Hook rate | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M30 | Social proof utilization | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M31 | UGC / social-native content | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M32 | Advantage+ Creative | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M-CR1 | Creative freshness | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M-CR2 | Frequency: Prospecting | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M-CR3 | Frequency: Retargeting | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M-CR4 | CTR benchmark | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M11 | Campaign fragmentation | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M12 | Campaign- versus ad-set-budget control | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M13 | Learning phase status | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M14 | Learning phase resets | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M15 | Advantage+ Sales campaign | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M16 | Ad set consolidation | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M17 | Budget distribution | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M18 | Campaign objective alignment | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M33 | Advantage+ Placements | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M34 | Placement performance review | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M35 | Attribution setting | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M36 | Bid strategy appropriateness | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M37 | Frequency cap monitoring | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M38 | Breakdown reporting | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M39 | UTM parameters | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M40 | A/B testing active | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M-ST1 | Budget adequacy | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M-ST2 | Budget utilization | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M19 | Audience overlap | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M20 | Custom Audience freshness | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M21 | Lookalike source quality | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M22 | Advantage+ Audience testing | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M23 | Exclusion audiences | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M24 | First-party data utilization | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M-AN1 | Andromeda creative diversity | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M-AT1 | Attribution window post | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| M-IA1 | Incremental Attribution testing | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M-TH1 | Threads placement evaluation | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M51 | Meta Ads MCP server inventory | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M52 | MCP paused-by-default enforcement | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M53 | MCP write-action governance | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M54 | Click-through metric-definition evidence | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M55 | Engage-through attribution column | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M56 | Engaged-view threshold | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M57 | Default attribution windows | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M58 | Historical baseline comparability | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M59 | View-through integration | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M60 | GEM claim provenance | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M61 | Lattice claim provenance | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M62 | Andromeda claim provenance | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M63 | ARM readiness | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M64 | Incremental Attribution as reporting view | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M65 | Ad-level placement control | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M66 | AI-generated Instant Forms | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M67 | Purchase audience retention governance | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M68 | Pixel auto-include detailed info governance | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M69 | Advantage+ Creative Image Generation Categories | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M70 | Automotive market-code migration evidence | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M71 | Digital Services Tax pass-through | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| M72 | CAPI one-click setup + EMQ | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |

## Recommendation boundary

A recommendation must identify the observed evidence, account-specific baseline or owner threshold, expected mechanism, confidence, reversible next step, measurement window, and rollback condition. Do not infer a recommendation from the control name alone.
