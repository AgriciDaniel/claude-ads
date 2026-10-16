# Conversion Tracking and Measurement

**Verified:** 2026-10-12 for the Google consent-mode, TikTok deduplication, and LinkedIn Conversions API rows; other rows follow their ledger entries (2026-10-07)
**Refresh due:** 2026-11-06 for platform documentation
**Evidence status:** architecture and audit questions; implementation is account-specific

Tracking is acceptable only when the business event, consent state, browser and
server paths, platform configuration, and downstream business record reconcile.
The presence of a tag or API connection is not proof of accurate measurement.

## Canonical event contract

For every optimization and reporting event, record:

- Stable event name and business definition.
- Event time, timezone, source, and unique event ID.
- Order, lead, or opportunity ID where lawful and appropriate.
- Currency and value definition, including refunds and cancellations.
- Browser/server/offline origin and deduplication key.
- Consent state and allowed processing purpose.
- Platform conversion action, primary/secondary role, counting behavior,
  attribution window, and inclusion in bidding.
- CRM acceptance state and reconciliation result.

Do not send unnecessary personal or sensitive data. Hashing is not consent and
does not make otherwise prohibited collection lawful.

## Platform evidence

| Platform | Current first-party source | What it supports |
| --- | --- | --- |
| Google Ads | `google-consent-modeling-official`: [Consent mode modeling](https://support.google.com/google-ads/answer/10548233), `google-consent-mode-verification-official`: [Verify consent mode implementation](https://support.google.com/google-ads/answer/14218557), `google-consent-mode-improve-modeling-official`: [How to improve your modeling](https://support.google.com/google-ads/answer/12445060), and `google-consent-modeling-improvement-official`: [impact results](https://support.google.com/google-ads/answer/11954524) | Modeling and impact reporting use eligibility thresholds that Google words differently by page; inspect the active setup and diagnostics instead of inventing an unpublished number |
| TikTok Ads | `tiktok-events-api-official`: [About Events API](https://ads.tiktok.com/help/article/events-api) and `tiktok-event-deduplication-official`: [About event deduplication](https://ads.tiktok.com/help/article/event-deduplication) | TikTok recommends Pixel plus Events API with event deduplication for web conversion clients; the deduplication page requires the same `event_id` and event parameters through both paths |
| LinkedIn Ads | `linkedin-conversions-api-official`: [Conversions API use cases](https://learn.microsoft.com/en-us/linkedin/marketing/conversions/conversions-usecase) | Insight Tag, Conversions API, and CSV conversion types; browser and server events sent with the same event ID are counted once, with the Insight Tag event retained |
| Microsoft Advertising | `microsoft-uet-official`: [UET setup](https://help.ads.microsoft.com/apex/index/3/en/56913) | UET setup, page coverage, verification, and troubleshooting |
| Meta | `meta-capi-deduplication-official`: [Handling duplicate Pixel and Conversions API events](https://developers.facebook.com/docs/marketing-api/conversions-api/deduplicate-pixel-and-server-events) | Conversions API is recommended alongside Meta Pixel as a redundant setup; deduplication matches the Pixel `eventID` to `event_id` and the Pixel event to `event_name`, or uses `fbp` and `external_id` consistently |

For Apple, Amazon, Reddit, Pinterest, Snapchat, X, and any platform detail
not represented by a current source-ledger entry, inspect the current official
account documentation and capability manifest during the run. Do not reuse a
different platform's event names or requirements by analogy.

Google's consent-mode pages word the modeling click threshold differently, and
Google does not reconcile them. Treat the figure as 700 ad clicks over seven days
per country/domain grouping: the modeling page calls it a daily threshold over a
seven-day period, while the implementation-verification page states 700 ad clicks
over 7 days for a domain and country grouping without the word daily. A third
page lists 100 clicks per day per country/domain grouping as a requirement for
basic consent mode only, not advanced. These readings are unreconciled, so cite
the page you used. The separate current impact-results page says additional
volume and modeling thresholds apply, but it does not publish another numeric
click threshold. Do not infer one. These are eligibility facts, not a universal
minimum account budget or a guarantee of modeled conversions. Use the active
configuration and current diagnostics.

## Audit sequence

1. Trace one real test event from user action to browser request, server request,
   platform receipt, deduplication, report, and CRM record.
2. Compare totals by event date and processing date over a lag-mature window.
3. Inspect duplicates, missing IDs, invalid values/currencies, clock skew, and
   events arriving before valid consent.
4. Confirm only intended business outcomes influence bidding.
5. Test refunds, cancellations, offline status changes, cross-domain flows, and
   payment-provider redirects where applicable.
6. Record platform diagnostics as vendor observations, then verify with raw
   payload logs and business records where access permits.

## Deduplication

Browser and server copies of the same business action must share the platform's
documented deduplication fields. Do not invent a universal field mapping. Check:

- Same action produces one accepted platform conversion.
- Distinct actions do not collide on an ID.
- Retries are idempotent.
- Late offline updates do not create a second sale or lead.
- Deduplication survives cross-domain and payment flows.

## Attribution and reconciliation

Keep these views separate:

- Platform-attributed conversions for delivery diagnostics.
- Analytics attribution for journey analysis.
- CRM/accounting outcomes for accepted business value.
- Experiment or model estimates for incrementality.

Never sum platform-attributed conversions across platforms as though they were
unique people or incremental outcomes. Disclose attribution windows, view-through
treatment, identity resolution, consent exclusions, and conversion lag.

## Severity guidance

Critical findings require observed impact, such as no primary event, confirmed
double counting, unauthorized sensitive-data transmission, materially wrong
value/currency, or bidding against a non-business event. A missing server-side
integration alone is an opportunity or coverage gap unless a current platform
requirement or observed measurement loss makes it more severe.

## Completion evidence

A tracking review is complete only when it identifies tested events, environments,
time window, consent states, payload evidence, platform diagnostics, CRM
reconciliation, gaps, confidence, and an owner for remediation. Never infer
health from configuration screenshots alone.
