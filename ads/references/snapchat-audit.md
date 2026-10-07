# Snapchat Ads control reference

Catalog reviewed: 2026-10-07. Use the per-source and per-claim verification
dates in the control-plane ledgers. This date does not verify every control.

## Category model

This reference does not define an executable scoring profile. Bind a versioned
profile whose categories cover the applicable controls and whose weights total 100;
otherwise produce findings without a health score.

## Runtime evaluation contract

- Treat each row as an applicability-first evidence question. Missing evidence is
  `unknown`; unavailable or ineligible surfaces are `not_applicable`.
- Verify objective, placement, geography, measurement path, reporting lifecycle,
  catalog use, policy, and account eligibility before evaluation.
- The registered source below grounds the Marketing API surface only. Current
  Pixel, CAPI, measurement, report-field, format, policy, and availability claims
  require additional dated official source IDs or account evidence.
- This reference is advisory and export-read only. It does not provide a live Snap
  API reader or mutation adapter.

## Controls

| ID | Category | Evidence question |
| --- | --- | --- |
| SC-M01 | Measurement | Snap Pixel, Conversions API, MMP, or offline source is declared and verified. |
| SC-M02 | Measurement | Events and values match the objective and use documented deduplication when needed. |
| SC-M03 | Measurement | App campaigns include the required app measurement configuration. |
| SC-M04 | Measurement | Attribution windows and report fields are explicit and comparable. |
| SC-R01 | Reporting | Date boundaries use the ad-account timezone and the data-finalization window is disclosed. |
| SC-R02 | Reporting | Large or product-level reports use the supported asynchronous lifecycle. |
| SC-S01 | Structure | Campaign, ad-squad, ad, creative, and objective relationships are valid. |
| SC-S02 | Structure | Optimization, placements, and delivery choices match the declared outcome. |
| SC-A01 | Audience | Audience, geography, device, and first-party targeting are intentional and eligible. |
| SC-C01 | Creative | Creative is mobile-first and native to the selected Snap placement. |
| SC-C02 | Creative | Materially different hooks, formats, and concepts are available for testing. |
| SC-C03 | Creative | AR, Lens, Story, collection, or lead formats use their required assets and destinations. |
| SC-D01 | Retail | Catalog mappings, product availability, and product-level reporting validate when DPA is used. |
| SC-B01 | Budget | Budget, bid, pacing, and campaign caps are viable and use correct currency units. |
| SC-P01 | Policy | Brand-safety, age, privacy, regulated-category, and review-status constraints are checked. |
| SC-E01 | Experiment | Tests isolate one decision and account for reporting latency. |

Results use `pass`, `fail`, `unknown`, or `not_applicable`. Unknown controls
reduce evidence coverage; unavailable, beta, premium, or ineligible features are
unscored opportunities.

## Registered official evidence

- `snap-ads-changelog-official`: [Marketing API changelog](https://developers.snap.com/marketing-api/Ads-API/changelog)
- `snap-capi-deduplication-official`: [Conversions API deduplication](https://developers.snap.com/marketing-api/Conversions-API/Deduplication)
- `snap-advertising-policies-official`: [Advertising policies](https://values.snap.com/policy/advertising-policies?lang=en-US)

Checked October 7, 2026 (CLM-0219): the October 6 changelog documents Unified
Attribution, App ID and TARGET_COST eligibility endpoints and an AI
self-declaration field. Obtain account-specific eligibility rather than
assuming access. September changes include asynchronous HOUR reporting and
age-bucket changes. Retain timezone and finalization timestamps when comparing
reports. Old wording that CAPI v2 would deprecate in early 2025 does not prove
its current removal; verify the selected version separately.

- `snap-marketing-api`: [Snap Marketing API](https://developers.snap.com/marketing-api/home)

Official sources override this summary when they change. Unsupported controls stay
`unknown`; practitioner material may supplement but not replace official evidence.
