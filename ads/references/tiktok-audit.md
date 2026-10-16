# TikTok Ads audit control catalog

<!-- Catalog IDs preserved from the legacy runtime; current platform facts require dated source or account evidence. -->

## Runtime evaluation contract

- Start with objective, geography, account type, campaign type, data window, conversion lag, sample size, and feature access.
- Return `not_applicable` when the surface or requirement does not apply and `unknown` when the required evidence is absent.
- A conditional control can affect health only when current account evidence, owner-defined economics, and an applicable official source establish the expectation.
- Product adoption, availability, beta access, announcement awareness, and vendor-reported performance are not health controls. Record them only as unscored discovery.
- Do not use fixed platform-wide thresholds, broad benchmarks, launch dates, sunset dates, or universal network, bidding, budget, audience, creative, or attribution rules from this catalog.
- Validate mutable facts at run time. A confirmed policy, support-state, or migration requirement needs its own current claim coverage before it can create a finding.

## Source coverage boundary

On October 7, 2026, the exact public v1.3 BASIC reporting, dimension, and
metric pages were verified for the selected `AUCTION` / `AUCTION_AD` native
projection. CLM-0204 covers its listed daily identifiers, names, spend, and
`conversion` fields. The conversion metric counts the selected optimization
event; it is not interchangeable with other conversion definitions.
Documentation and fixtures do not establish an authenticated report request.
No v1.3 removal date was verified. Pixel and Events API measurement guidance
was reverified separately; use identical event and event_id values when
deduplicating copies of the same event.

The registered sources below cover only the measurement, API, and import foundations stated in the claim ledger. They do not support every named product or control in this catalog. Until a narrower current claim exists, treat those names as routing labels and gather fresh official or in-account evidence.

## Official evidence

- `tiktok-business-api-official`: [TikTok API for Business](https://business-api.tiktok.com/portal)
- `tiktok-events-api-official`: [TikTok Events API](https://ads.tiktok.com/help/article/events-api)
- `tiktok-pixel-official`: [TikTok Pixel](https://ads.tiktok.com/help/article/tiktok-pixel)

- `tiktok-integrated-reporting-official`: [TikTok API for Business v1.3 basic reporting documentation](https://business-api.tiktok.com/portal/docs/basic-reports/v1.3)
- `tiktok-basic-report-dimensions-v13-official`: [TikTok v1.3 basic-report supported dimensions](https://business-api.tiktok.com/portal/docs/basic-reports-supported-dimensions/v1.3)
- `tiktok-basic-report-metrics-v13-official`: [TikTok v1.3 basic-report supported metrics](https://business-api.tiktok.com/portal/docs/basic-reports-supported-metrics/v1.3)

## Control registry

| ID | Audit intent | Runtime disposition |
|---|---|---|
| T05 | Creative test capacity | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T06 | Vertical video format | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T07 | Native-looking content | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T08 | Hook strategy | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T09 | Creative fatigue | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T10 | Spark Ads applicability | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T20 | TikTok Shop integration | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T21 | Video Shopping Ads | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T22 | Caption SEO | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T23 | Sound/music usage | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T24 | CTA button | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T25 | Safe zone compliance | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T01 | TikTok Pixel installed | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T02 | Events API + ttclid | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T11 | Bid strategy | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T12 | Budget sufficiency | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T13 | Learning evidence | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T03 | Campaign structure | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T04 | Smart+ applicability | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T14 | Search Ads applicability | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T15 | Placement selection | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T16 | Dayparting | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T17 | CTR benchmark | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T18 | CPA target | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T19 | Video completion rate | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T-SR1 | Search Ads alongside In-Feed | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T-GM1 | GMV Max for Shop campaigns | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T-EA1 | Events API Gateway setup | Conditional evidence control: establish applicability and evaluate from current account evidence; otherwise return `unknown` or `not_applicable`. |
| T29 | TikTok Ads MCP Server | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T30 | TikTok Ads Skills | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T31 | Smart+ One Buying Experience module control | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T32 | Smart+ Music Autofix | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T33 | Smart+ creative reporting + multi-URL | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T34 | Smart+ for app objectives | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T35 | TopReach + Creative Sequencing | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T36 | Branded Buzz | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T37 | Search Hubs | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T38 | Symphony AI creative stack | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T39 | TikTok GO booking integration | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T40 | Mini Series & Mini Games | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T41 | Collage Carousel availability | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T42 | One Asset Manager | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T43 | View+ for Pulse Core Max | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T44 | TikTok Market Scope | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T45 | TikTok Real + UK Ad-Free Subscription | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |
| T46 | GMV Max market expansion | Unscored source-refresh discovery: verify current official availability, account eligibility, and governance need; non-adoption is never a failure. |

## Recommendation boundary

A recommendation must identify the observed evidence, account-specific baseline or owner threshold, expected mechanism, confidence, reversible next step, measurement window, and rollback condition. Do not infer a recommendation from the control name alone.
