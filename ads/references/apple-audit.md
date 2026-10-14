# Apple Ads control reference

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
- Verify app, market, placement, campaign type, reporting access, attribution path,
  and account eligibility before evaluation.
- The registered source below grounds the developer API surface only. Current
  product, policy, attribution, privacy-threshold, report-field, bidding, and
  creative claims require additional dated official source IDs or account evidence.
- This reference is advisory and export-read only. It does not provide a live Apple
  Ads API reader or mutation adapter.

## Controls

| ID | Category | Evidence question |
| --- | --- | --- |
| AP-M01 | Measurement | AdServices, AdAttributionKit, MMP, or internal attribution sources and limitations are declared. |
| AP-M02 | Measurement | Installs and post-install events reconcile across Apple Ads and the app analytics source. |
| AP-M03 | Measurement | Attribution privacy thresholds and missing detail are treated as uncertainty, not zero performance. |
| AP-M04 | Measurement | Campaign, placement, ad-group, keyword, search-term, and ad reports use comparable windows. |
| AP-S01 | Structure | Campaigns separate brand, category, competitor, discovery, and placement intent where material. |
| AP-S02 | Structure | Search Match discovery and manually targeted keywords do not create uncontrolled overlap. |
| AP-K01 | Keywords | Match type, negatives, search terms, and keyword movement follow observed query evidence. |
| AP-K02 | Keywords | Bid and CPT decisions consider tap-through, conversion, CPA, value, and volume together. |
| AP-A01 | Audience | Country, device, customer type, demographics, and audience choices are eligible and intentional. |
| AP-C01 | Creative | Default and custom product pages match keyword, placement, audience, and app-store promise. |
| AP-C02 | Creative | Product-page tests isolate creative or message changes and have sufficient observation time. |
| AP-B01 | Budget | Budget allocation and pacing preserve discovery while funding proven intent. |
| AP-B02 | Budget | Goal-based bidding or automation is recommended only when eligible and supported by evidence. |
| AP-R01 | Reporting | Currency, timezone, delayed attribution, and API pagination/report completeness are disclosed. |
| AP-P01 | Policy | App, market, age, privacy, and product eligibility requirements are checked. |
| AP-E01 | Experiment | Tests define hypothesis, placement, primary metric, guardrails, and readout window. |

Use `pass`, `fail`, `unknown`, or `not_applicable`. Unknown controls reduce
coverage. Optional, beta, premium, unavailable, immutable, or ineligible features
are unscored opportunities.

## Registered official evidence

- `apple-ads-api-official`: [Using Apple Ads API functionality](https://developer.apple.com/documentation/apple_ads/using-apple-search-ads-api-functionality)
- `apple-ads-platform-api-official`: [Apple Ads Platform API](https://developer.apple.com/documentation/apple-ads-platform-api)

## API lifecycle status verified 2026-10-12

Apple's deprecation banner states that the Apple Ads Campaign Management API is
deprecated and will be sunset on 2027-01-26, and it names the Apple Ads Platform
API as the replacement. The `v5` endpoints, including the campaign reporting
endpoint behind the `apple-ads-api-v5-campaign-daily-v1` profile (`CLM-0206`),
belong to the deprecated API. Treat that profile and any `v5` reader as ending on
2027-01-26 and plan a migration. Only the existence of the replacement page was
confirmed (`CLM-0220`); its endpoints, authentication, capabilities, and field
mappings were not read, so do not assume the `v5` field names or semantics carry
over.

Official sources override this summary when they change. Unsupported controls stay
`unknown`; vendor case studies remain labeled and contextual.
