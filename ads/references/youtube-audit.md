# YouTube Ads control reference

Catalog reviewed: 2026-10-07. Use the per-source and per-claim verification
dates in the control-plane ledgers. This date does not verify every control.

## Category model

This reference does not define an executable scoring profile. Bind a versioned
profile whose categories cover the applicable controls and whose weights total 100;
otherwise produce findings without a health score. The deterministic engine applies
weights only after scoring applicable controls within each category.

## Runtime evaluation contract

- Treat each row as an applicability-first evidence question. Missing evidence is
  `unknown`; unavailable or ineligible surfaces are `not_applicable`.
- Verify campaign subtype, inventory, objective, geography, format, reporting
  fields, measurement path, and account eligibility before evaluation.
- The registered source below grounds Google Ads API video campaign support only.
  Current Demand Gen, migration, engagement-goal, creative, policy, and availability
  claims require additional dated official source IDs or account evidence.
- This reference is advisory and export-read only. It does not provide a live
  Google/YouTube API reader or mutation adapter.

## Controls

| ID | Category | Evidence question |
| --- | --- | --- |
| YT-M01 | Measurement | Primary conversion or engagement goal and its counting role are explicit. |
| YT-M02 | Measurement | Google Ads, GA4, channel-link, view-through, and assisted measurement choices are reconciled. |
| YT-M03 | Measurement | YouTube and non-YouTube Demand Gen inventory are separated in reporting where needed. |
| YT-M04 | Measurement | Brand-lift or incrementality methods are used when direct response cannot answer the objective. |
| YT-S01 | Structure | Campaign subtype, channel controls, objective, bidding, and inventory match the intended outcome. |
| YT-S02 | Structure | Historical reporting continuity for upgraded Video Action Campaigns, including original campaigns kept as removed or paused, and incompatible settings are reviewed. |
| YT-A01 | Audience | Audience signals or segments match intent and first-party exclusions avoid overlap. |
| YT-A02 | Audience | Content suitability, placements, topics, and inventory controls are intentionally governed. |
| YT-C01 | Creative | The opening earns attention before skip behavior and communicates the offer clearly. |
| YT-C02 | Creative | Horizontal, vertical, square, short, and long formats cover intended inventory. |
| YT-C03 | Creative | Materially different concepts and hooks are available, not cosmetic variants. |
| YT-C04 | Creative | Demand Gen asset and product-feed choices are deliberate and eligible. |
| YT-B01 | Budget | Bid and budget strategy fit the objective, evidence volume, and campaign maturity. |
| YT-R01 | Reporting | View, engagement, click, conversion, and cost metrics use a consistent window and definition. |
| YT-P01 | Policy | Content suitability, brand safety, disclosures, and regulated-category obligations are checked. |
| YT-E01 | Experiment | Creative or audience experiments isolate one decision and account for conversion lag. |

Use `pass`, `fail`, `unknown`, or `not_applicable`. Unknown controls reduce
coverage. Optional, beta, premium, unavailable, immutable, or ineligible features
are unscored opportunities.

## Registered official evidence

- `youtube-google-ads-video-official`: [Google Ads API video campaigns](https://developers.google.com/google-ads/api/docs/video/overview)
- `google-ads-vac-demand-gen-upgrade-official`: [Video Action Campaigns are being upgraded to Demand Gen](https://support.google.com/google-ads/answer/15110871)

## Video Action Campaign status verified 2026-10-12

Google states that Video Action Campaigns were automatically upgraded to Demand
Gen, with the final campaigns upgraded by April 2026 (`CLM-0224`). Do not look
for a surviving legacy campaign state. Original campaigns remain in the account
as removed or paused and keep their historical reporting, and the upgraded Demand
Gen campaign does not count spend made in the original. YT-S02 therefore checks
that reporting joins the original and upgraded campaigns across the change,
using status filters that include removed and paused campaigns, and that
settings that do not carry over are reviewed. Google's page contains some
conflicting timing text and no update date, so label any account-level mismatch
as `unknown` rather than a failure.

Official sources override this summary when they change. Unsupported controls stay
`unknown`; vendor case studies remain labeled and contextual.
