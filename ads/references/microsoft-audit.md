# Microsoft Advertising audit control catalog

<!-- Catalog IDs preserved from the legacy runtime; current platform facts require dated source or account evidence. -->

## Runtime evaluation contract

- Start with objective, geography, account type, campaign type, data window, conversion lag, sample size, and feature access.
- Return `not_applicable` when the surface or requirement does not apply and `unknown` when the required evidence is absent.
- A conditional control can affect health only when current account evidence, owner-defined economics, and an applicable official source establish the expectation.
- Product adoption, availability, beta access, announcement awareness, and vendor-reported performance are not health controls. Record them only as unscored discovery.
- Do not use fixed platform-wide thresholds, broad benchmarks, launch dates, sunset dates, or universal network, bidding, budget, audience, creative, or attribution rules from this catalog.
- Validate mutable facts at run time. A confirmed policy, support-state, or migration requirement needs its own current claim coverage before it can create a finding.

## Source coverage boundary

The registered sources below cover only the measurement, API, and import foundations stated in the claim ledger. They do not support every named product or control in this catalog. Until a narrower current claim exists, treat those names as routing labels and gather fresh official or in-account evidence.

## Official evidence

- `microsoft-advertising-api-official`: [Microsoft Advertising API overview](https://learn.microsoft.com/en-us/advertising/guides/?view=bingads-13)
- `microsoft-uet-official`: [Microsoft UET setup](https://learn.microsoft.com/en-us/advertising/msa-help/hlp_ba_conc_uet_setup_master)
- `microsoft-conversions-api-official`: [Microsoft Conversions API guide](https://learn.microsoft.com/en-us/advertising/guides/uet-conversion-api-integration?view=bingads-13)
- `microsoft-google-import-official`: [Microsoft Google Ads import mapping](https://learn.microsoft.com/en-us/advertising/msa-help/hlp_ba_conc_importwhatinfo)
- `microsoft-ads-soap-rest-migration-official`: [Microsoft Advertising SOAP-to-REST migration](https://learn.microsoft.com/en-us/advertising/guides/migrate-to-rest?view=bingads-13)

## API transport status verified 2026-10-07

Microsoft states that existing SOAP integrations remain supported, including
feature and enhancement access, through 2027-01-31. SOAP is scheduled for full
deprecation on that date. Recommend migration planning and current SDK checks,
but do not report SOAP as unsupported or REST-only before the deadline.

## Control registry

| ID | Audit intent | Runtime disposition |
|---|---|---|
| MS01 | UET tag installed | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS02 | Enhanced conversions | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS03 | Google Ads import validation | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS04 | Brand syndication control | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS05 | Audience Network settings | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS06 | Bid strategy alignment | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS07 | New-customer optimization applicability | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS08 | Campaign structure | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS09 | Budget allocation | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS10 | LinkedIn profile targeting applicability | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS11 | RSA asset count | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS12 | Multimedia Ads | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS13 | Ad copy uniqueness | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS19 | Action Extension | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS20 | Filter Link Extension | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS14 | Copilot and new-placement applicability | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS15 | Conversion goals | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS16 | Cross-platform CPC context | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS17 | Conversion rate comparison | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS18 | Impression share | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS-SI1 | Scheduled import status | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS-CM1 | Consent Mode compliance | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS-CT1 | CTV ad inventory coverage | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS-VD1 | Video ad inventory utilization | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| MS25 | AI Max for Search applicability | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS26 | Offer Highlights in Copilot | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS27 | Audience Generation | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS28 | PMax Final URL reporting | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS29 | Clarity AI Visibility | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS30 | Brand Agents on commerce platforms | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS31 | UCP in Merchant Center | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS32 | Copilot Checkout | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS33 | Rewarded Portals | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS34 | Import Center | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS35 | Automated bidding + custom columns | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS36 | Performance Shift Root Cause Analysis | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS37 | Conversion Tracking Diagnostics | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS38 | Data-Driven Attribution adoption | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS39 | Conversion API | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS40 | Ad Studio Brand Kit | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| MS41 | API transport migration evidence | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |

## Recommendation boundary

A recommendation must identify the observed evidence, account-specific baseline or owner threshold, expected mechanism, confidence, reversible next step, measurement window, and rollback condition. Do not infer a recommendation from the control name alone.
