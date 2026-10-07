# LinkedIn Ads audit control catalog

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

- `linkedin-marketing-api-official`: [LinkedIn Marketing Developer Platform](https://learn.microsoft.com/en-us/linkedin/marketing/overview)
- `linkedin-conversion-tracking-official`: [LinkedIn conversion tracking](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/conversion-tracking)
- `linkedin-conversions-api-official`: [LinkedIn Conversions API use cases](https://learn.microsoft.com/en-us/linkedin/marketing/conversions/conversions-usecase)
- `linkedin-marketing-api-changes-official`: [Recent LinkedIn Marketing API changes](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/recent-changes?view=li-lms-2026-07)

## API version status verified 2026-10-07

LinkedIn lists Marketing API version `202510` for sunset on 2026-10-15. Treat
that date as an imminent migration deadline and verify the requested replacement
version and endpoint compatibility before changing an integration. Do not report
`202510` as already removed before the effective date.

## Control registry

| ID | Audit intent | Runtime disposition |
|---|---|---|
| L01 | Insight Tag installed | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L02 | Conversions API applicability and status | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L03 | Job title targeting precision | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L04 | Company size filtering | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L05 | Seniority level targeting | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L06 | Matched Audiences | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L07 | ABM company-list applicability | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L08 | Audience expansion setting | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L09 | Predictive audiences | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L10 | Thought Leader Ads applicability | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L11 | Ad format diversity | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L12 | Video ads present | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L13 | Creative refresh cadence | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L14 | Lead Gen Form friction | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L15 | Lead Gen Form CRM integration | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L16 | Bid strategy appropriate | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L17 | Budget sufficiency | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L18 | Ad Set objective alignment | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L19 | A/B testing active | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L20 | Frequency monitoring | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L21 | CTR benchmark | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L22 | CPC benchmark | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L23 | Lead quality tracking | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L24 | Conversion tracking attribution | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L25 | Demographics report review | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L-CRM1 | CRM integration for revenue attribution | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L-EU1 | EU Sponsored Messaging compliance | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| L28 | Off-Platform Event Ads | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L29 | Campaign Manager terminology rename trap | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L30 | Accelerate auto-campaign creation | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L31 | AI Ad Variants | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L32 | Career Journey targeting | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L33 | Reserved Ads | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L34 | First Impression Ads | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L35 | BrandLink expansion | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L36 | Wire | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L37 | Thought Leader Event Ads | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L38 | CTV expansion | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L39 | Company Attribution in Revenue Attribution Report | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L40 | MRC accreditation for video metrics | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L41 | Company Intelligence API | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L42 | Flexible Ad Creation availability | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L43 | SMB Auto-targeting + Draft with AI | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L44 | Real-time CRM data in Campaign Manager | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L45 | Ads Agency Certification | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| L46 | Organic-signal relevance | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |

## Recommendation boundary

A recommendation must identify the observed evidence, account-specific baseline or owner threshold, expected mechanism, confidence, reversible next step, measurement window, and rollback condition. Do not infer a recommendation from the control name alone.
