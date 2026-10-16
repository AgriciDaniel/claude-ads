# Amazon Ads control reference

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
- Verify marketplace, region, seller/vendor relationship, ad product, API access,
  attribution, reporting grain, and retail ownership before evaluation.
- The registered source below grounds API availability only. Current product,
  policy, metric, attribution, catalog, and format claims require additional dated
  official source IDs or account evidence.
- This reference is advisory and export-read only. It does not provide a live
  Amazon API reader or mutation adapter.

## Controls

| ID | Category | Evidence question |
| --- | --- | --- |
| AMZ-M01 | Measurement | Profile, marketplace, region, currency, timezone, and attribution window are explicit. |
| AMZ-M02 | Measurement | Orders, sales, ACOS, ROAS, TACOS, new-to-brand, and retail metrics are not conflated. |
| AMZ-M03 | Measurement | Async report lifecycle, status, download, pagination, and missing rows are validated. |
| AMZ-M04 | Measurement | Amazon Ads attribution is reconciled with Seller/Vendor and business-level outcomes. |
| AMZ-S01 | Structure | Portfolios, campaign types, targeting, and naming reflect product and objective ownership. |
| AMZ-S02 | Structure | Sponsored Products, Brands, Display, DSP, and video roles are separately evaluated. |
| AMZ-T01 | Targeting | Automatic, keyword, product, audience, and defensive targeting have explicit purposes. |
| AMZ-T02 | Targeting | Search-term harvesting and negatives are based on sufficient query and conversion evidence. |
| AMZ-R01 | Retail | Buy Box, inventory, price, reviews, detail-page quality, and suppression risks are checked. |
| AMZ-R02 | Retail | Catalog and variation relationships support the advertised ASINs and landing experience. |
| AMZ-C01 | Creative | Sponsored Brands, video, display, and Store assets match format and product promise. |
| AMZ-C02 | Creative | Materially different value propositions and formats are available for testing. |
| AMZ-B01 | Budget | Budget, bid, placement adjustments, and pacing reflect margin, stock, objective, and evidence. |
| AMZ-B02 | Budget | Automation changes respect profile/region scope, learning impact, and account ceilings. |
| AMZ-P01 | Policy | Product eligibility, claims, creative, audience, and marketplace policy constraints are checked. |
| AMZ-E01 | Experiment | Tests isolate one lever and account for retail, organic, price, and inventory changes. |

Use `pass`, `fail`, `unknown`, or `not_applicable`. Unknown controls reduce
coverage. Optional, beta, premium, unavailable, immutable, or ineligible features
are unscored opportunities.

## Registered official evidence

The October 7, 2026 review verified the API overview and MCP open-beta
announcement. The exact creative-acceptance page exposed no reviewable policy
text, so its prior verification date was retained. Obtain directly readable,
placement-specific official policy before enforcing a creative limit. Amazon
native report normalization remains disabled pending an exact report contract.

- `amazon-ads-api-official`: [Amazon Ads API overview](https://advertising.amazon.com/about-api/)

Official sources override this summary when they change. Unsupported controls stay
`unknown`; vendor case studies remain labeled and contextual.
