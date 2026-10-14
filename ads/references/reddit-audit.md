# Reddit Ads control reference

Catalog reviewed: 2026-10-07. Use the per-source and per-claim verification
dates in the control-plane ledgers. This date does not verify every control.

## Current API changes verified 2026-10-12

The official `reddit-ads-api-history-official` changelog records these contract
changes (`CLM-0216`):

- Since 2026-09-30, creating an onsite Lead Generation Form returns `410 Gone`;
  retrieval remains available and existing ads using onsite forms are paused.
- Since 2026-09-23, creative writes must use
  `enhancements.user_generated_content.enroll_status`; the removed
  `enhancements.allow_user_generated_content` field returns `HTTP 400`.
- Since 2026-09-21, new campaign objective enums roll out and legacy enums remain
  supported. Campaigns created with the new objectives return the new enum
  values, which Reddit marks as a breaking change for integrations that store,
  display, map, or report on objective values. `use_catalog` is added to the
  Campaigns API and applies only to `SALES` objectives that need a product
  catalog. Review Reddit's mapping table before comparing objectives across
  accounts or dates.
- Since 2026-10-01, `SALES` and `LEAD_GENERATION` objectives are supported in
  Create Campaign for Max campaigns.
- From 2026-12-08, report requests using the `HOUR` breakdown for more than seven
  days, or using unsupported breakdown combinations, return `400 Bad Request`.
  Until then, treat this as a migration deadline, not an already-active response
  contract.

## Category model

This reference does not define an executable scoring profile. Bind a versioned
profile whose categories cover the applicable controls and whose weights total 100;
otherwise produce findings without a health score.

## Runtime evaluation contract

- Treat each row as an applicability-first evidence question. Missing evidence is
  `unknown`; unavailable or ineligible surfaces are `not_applicable`.
- Verify objective, placement, geography, identity, measurement path, catalog use,
  reporting definitions, policy, and account eligibility before evaluation.
- The registered source below grounds supported conversion events only. Current
  catalog, DPA, targeting, format, policy, and API claims require additional dated
  official source IDs or account evidence.
- This reference is advisory and export-read only. It does not provide a live
  Reddit API reader or mutation adapter.

## Controls

| ID | Category | Evidence question |
| --- | --- | --- |
| RD-M01 | Measurement | Primary conversion source and ownership are identified. |
| RD-M02 | Measurement | Reddit Pixel or Conversions API events match the business conversion taxonomy. |
| RD-M03 | Measurement | Pixel and server events use deduplication when both paths send the same event. |
| RD-M04 | Measurement | Events Manager diagnostics and representative test events have been reviewed. |
| RD-S01 | Structure | Campaign objective and optimization event match the business outcome. |
| RD-S02 | Structure | Prospecting and retargeting intent are distinguishable and exclusions prevent avoidable overlap. |
| RD-A01 | Audience | Community, interest, keyword, or first-party targeting is supported by the offer and evidence. |
| RD-A02 | Audience | Audience expansion is deliberate and measured rather than assumed beneficial. |
| RD-C01 | Creative | Creative reads naturally in the selected Reddit placement and community context. |
| RD-C02 | Creative | Materially different concepts, hooks, and formats are available for testing. |
| RD-C03 | Creative | Ad promise, comment context, and landing-page experience remain consistent. |
| RD-R01 | Retail | Catalog fields, availability, prices, links, and refresh behavior are healthy when commerce formats are used. |
| RD-R02 | Retail | Dynamic product advertising maps the relevant catalog and measurement source. |
| RD-B01 | Budget | Budget and bid strategy are viable for the objective, data volume, and test design. |
| RD-P01 | Policy | Brand-safety, placement, regulated-category, and privacy controls have been reviewed. |
| RD-E01 | Experiment | Tests isolate a decision, define success criteria, and avoid overlapping changes. |

Results use `pass`, `fail`, `unknown`, or `not_applicable`. Unknown controls
reduce evidence coverage; unavailable, beta, premium, or ineligible features are
unscored opportunities.

## Registered official evidence

- `reddit-business-help`: [Reddit supported conversion events](https://business.reddithelp.com/articles/Knowledge/supported-conversion-events)
- `reddit-ads-api-history-official`: [Reddit Ads API changelog](https://ads-api.reddit.com/docs/v3/history)

Official sources override this summary when they change. Unsupported controls stay
`unknown`; practitioner material may supplement but not replace official evidence.
