# Pinterest Ads control reference

Catalog reviewed: 2026-10-07. Use the per-source and per-claim verification
dates in the control-plane ledgers. This date does not verify every control.

## Category model

This reference does not define an executable scoring profile. Bind a versioned
profile whose categories cover the applicable controls and whose weights total 100;
otherwise produce findings without a health score.

## Runtime evaluation contract

- Treat each row as an applicability-first evidence question. Missing evidence is
  `unknown`; unavailable or ineligible surfaces are `not_applicable`.
- Verify objective, placement, geography, measurement path, domain/catalog state,
  privacy choices, policy, and account eligibility before evaluation.
- The registered source below grounds the Conversions API only. Current catalog,
  Performance+, collections, targeting, format, policy, and availability claims
  require additional dated official source IDs or account evidence.
- This reference is advisory and export-read only. It does not provide a live
  Pinterest API reader or mutation adapter.

## Controls

| ID | Category | Evidence question |
| --- | --- | --- |
| PN-M01 | Measurement | Pinterest Tag, Conversions API, MMP, or offline source is declared and verified. |
| PN-M02 | Measurement | Browser and server events use event IDs or the documented deduplication mechanism. |
| PN-M03 | Measurement | Event quality, latency, diagnostics, and representative test events have been reviewed. |
| PN-M04 | Measurement | Privacy flags and data-use choices match applicable geography and consent. |
| PN-R01 | Retail | Catalog required fields, variants, prices, availability, links, and images validate. |
| PN-R02 | Retail | Catalog refreshes prevent stale or unavailable products from serving. |
| PN-R03 | Retail | Claimed-domain, destination, and tracking behavior are consistent. |
| PN-S01 | Structure | Objective, optimization event, and campaign type match the business outcome. |
| PN-S02 | Structure | Automation such as Performance+ is intentionally configured and eligible. |
| PN-A01 | Audience | First-party, interest, keyword, and expansion choices reflect search and discovery intent. |
| PN-C01 | Creative | Pins meet format requirements and communicate value without relying on unsupported assumptions. |
| PN-C02 | Creative | Creative diversity covers materially different concepts, formats, and funnel stages. |
| PN-C03 | Creative | Landing pages preserve the Pin promise, product, and tracking parameters. |
| PN-B01 | Budget | Budget and bidding are viable for the optimization event and evidence volume. |
| PN-P01 | Policy | Merchant, creative, privacy, AI-disclosure, and regulated-category obligations are reviewed. |
| PN-E01 | Experiment | Tests isolate one decision with a declared audience, window, and success measure. |

Results use `pass`, `fail`, `unknown`, or `not_applicable`. Unknown controls
reduce evidence coverage; unavailable, beta, premium, or ineligible features are
unscored opportunities.

## Registered official evidence

- `pinterest-objective-simplification-official`: [Campaign objective migration](https://developers.pinterest.com/docs/work-with-ads/try-out-campaign-objective-type-simplification/)
- `pinterest-api-changelog-official`: [API changelog](https://developers.pinterest.com/docs/changelog/changelog/)
- `pinterest-advertising-guidelines-official`: [Advertising guidelines](https://policy.pinterest.com/en/advertising-guidelines)

Checked October 7, 2026 (CLM-0218): SALES and LEADS are in production. The
listed legacy-objective creation restrictions are scheduled for February 1,
2027, with listed legacy campaign archival scheduled for April 30, 2027. Vendor
dates may change. During migration, reporting filters need both current and
applicable legacy objective values. Recheck the active API and account context
before recommending changes. The announced November 12, 2026 policy preview is
not the active policy on the verification date.

- `pinterest-conversions-api`: [Pinterest API for Conversions](https://help.pinterest.com/en/business/article/the-pinterest-api-for-conversions)

Official sources override this summary when they change. Unsupported controls stay
`unknown`; practitioner material may supplement but not replace official evidence.
