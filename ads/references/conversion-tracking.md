# Conversion Tracking and Measurement

**Verified:** 2026-08-26
**Refresh due:** 2026-09-25 for platform documentation
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
| Google Ads | `google-consent-modeling-official`: [Consent mode modeling](https://support.google.com/google-ads/answer/10548233) and `google-consent-modeling-improvement-official`: [impact results](https://support.google.com/google-ads/answer/11954524) | Modeling and impact reporting use eligibility thresholds; inspect the active setup and diagnostics instead of inventing an unpublished number |
| TikTok Ads | `tiktok-events-api-official` — [About Events API](https://ads.tiktok.com/help/article/events-api) | TikTok recommends Pixel plus Events API with event deduplication for web conversion clients |
| LinkedIn Ads | `linkedin-conversions-api-official` — [Conversions API Playbook](https://business.linkedin.com/content/dam/me/business/en-us/marketing-solutions/resources/pdfs/Conversions-API-Playbook.pdf) | Browser and server conversion sources require deliberate reporting setup |
| Microsoft Advertising | `microsoft-uet-official` — [UET setup](https://help.ads.microsoft.com/apex/index/3/en/56913) | UET setup, page coverage, verification, and troubleshooting |

For Meta, Apple, Amazon, Reddit, Pinterest, Snapchat, X, and any platform detail
not represented by a current source-ledger entry, inspect the current official
account documentation and capability manifest during the run. Do not reuse a
different platform's event names or requirements by analogy.

Google's current consent-mode modeling page lists correct consent mode or IAB
TCF implementation and a daily threshold of 700 ad clicks over seven days per
country/domain grouping among its quality checks. The separate current
impact-results page says additional volume and modeling thresholds apply, but it
does not publish another numeric click threshold. Do not infer one. These are
eligibility facts, not a universal minimum account budget or a guarantee of
modeled conversions. Use the active configuration and current diagnostics.

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
