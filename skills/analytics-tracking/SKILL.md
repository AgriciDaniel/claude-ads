---
name: analytics-tracking
description: >
  GA4 setup, conversion event plan, UTM parameter scheme, and Google Tag
  Manager implementation for Meta ad campaigns. Covers Meta Pixel, CAPI,
  and cross-platform attribution. Triggers on: "analytics", "tracking",
  "GA4", "UTM", "conversion tracking", "Pixel", "CAPI", "tag manager",
  "attribution", "events".
argument-hint: "<campaign-name> | <website URL>"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - WebFetch
---

# Analytics & Tracking — Meta Campaign Measurement Setup

Produces a complete tracking specification covering Meta Pixel, Conversions
API (CAPI), GA4 events, UTM parameters, and Google Tag Manager configuration.

## Process

1. Read campaign brief from `campaigns/{name}/brief.md` if available
2. Identify conversion objective and destination URL(s)
3. Generate tracking spec covering all four layers
4. Write to `campaigns/{name}/tracking.md`
5. Log in `campaigns/{name}/log.md`

---

## Layer 1 — Meta Pixel & Conversions API

### Pixel Health Check
Before campaign launch, verify:
- Pixel fires on all key pages (homepage, landing page, thank-you page)
- Pixel fires the correct standard event on each page:

| Page | Standard Event | Required Parameters |
|------|---------------|-------------------|
| All pages | PageView | — |
| Landing page | ViewContent | content_name, content_type |
| Lead form / contact | Lead | value, currency (if applicable) |
| Purchase / checkout | Purchase | value, currency, content_ids |
| Sign-up / registration | CompleteRegistration | value, currency |

### Conversions API (CAPI) — Required for iOS 14.5+
CAPI sends server-side events to Meta, recovering signal lost from browser
tracking restrictions. Without CAPI, expect 30–40% data loss.

Required CAPI setup:
1. Generate system user access token in Meta Business Manager
2. Connect CAPI to your CRM or backend (or use Meta's partner integrations)
3. Implement `event_id` deduplication to prevent double-counting:
   - Browser event: `event_id = {timestamp}_{random_string}`
   - Server event: same `event_id` as browser event
4. Include customer information parameters for EMQ:
   - `em` (email, hashed SHA-256) — highest priority
   - `ph` (phone, hashed SHA-256)
   - `fn`, `ln` (first/last name, hashed)
   - `ct`, `st`, `zp` (city, state, zip)
   - `external_id` (CRM ID)

### Aggregated Event Measurement (AEM)
For iOS users (significant share of Meta audience):
1. Verify domain in Business Manager → Brand Safety → Domains
2. Configure up to 8 conversion events in Events Manager → Aggregated Event
   Measurement
3. Prioritize events by value (Purchase highest, ViewContent lowest)

---

## Layer 2 — UTM Parameter Scheme

Standard UTM structure for all Meta ads:

| Parameter | Value | Notes |
|-----------|-------|-------|
| `utm_source` | `meta` | Always lowercase |
| `utm_medium` | `paid` | — |
| `utm_campaign` | `{campaign-name}` | Match Ads Manager name |
| `utm_content` | `{ad-name}` | Match ad name exactly |
| `utm_term` | `{ad-set-name}` | Optional but useful |

### URL Template
```
{landing-page-url}?utm_source=meta&utm_medium=paid&utm_campaign={campaign}&utm_content={ad-name}
```

### Campaign UTM Map
Generate a UTM URL for every ad in the campaign:

| Ad Name | Destination URL | Full UTM URL |
|---------|----------------|-------------|
| `pain_image_v1` | {url} | {url}?utm_source=meta&utm_medium=paid&utm_campaign={campaign}&utm_content=pain_image_v1 |
| `outcome_image_v1` | {url} | {url}?utm_source=meta&utm_medium=paid&utm_campaign={campaign}&utm_content=outcome_image_v1 |
| `proof_image_v1` | {url} | {url}?utm_source=meta&utm_medium=paid&utm_campaign={campaign}&utm_content=proof_image_v1 |

---

## Layer 3 — GA4 Event Plan

### Key Conversion Events to Configure

| Event Name | Trigger | Parameters |
|-----------|---------|-----------|
| `generate_lead` | Form submission / Lead form complete | `campaign_name`, `ad_content` |
| `purchase` | Order confirmation page | `value`, `currency`, `transaction_id` |
| `begin_checkout` | Checkout page load | `value`, `currency` |
| `sign_up` | Registration complete | `method` |
| `page_view` | All pages (auto) | `page_title`, `page_location` |

### GA4 Source/Medium Attribution
GA4 should automatically attribute sessions with UTM params. Verify:
- `Session source / medium` report shows `meta / paid`
- Conversion events fire within the attributed session
- Cross-channel attribution model set to: Data-Driven (preferred) or Last Click

### Custom GA4 Dimensions
Add these custom dimensions for campaign analysis:
- `ad_content` (maps to `utm_content`) — identifies which creative converted
- `campaign_name` (maps to `utm_campaign`) — identifies which campaign

---

## Layer 4 — Google Tag Manager Implementation

If GTM is in use, provide tag configuration:

### Tags Required
1. **GA4 Configuration Tag** — fires on all pages
2. **GA4 Event Tag: generate_lead** — fires on thank-you page or form submit
3. **Meta Pixel Base Code** — fires on all pages (if not hardcoded)
4. **Meta Pixel Event: Lead** — fires on thank-you page

### Triggers
- All Pages: `Page View` trigger
- Thank-You Page: URL contains `/thank-you` (or specify exact path)
- Form Submit: Form ID or class selector

### Testing
- Use GTM Preview mode to verify tags fire correctly
- Use Meta's Pixel Helper Chrome extension to verify Pixel events
- Use GA4 DebugView to verify GA4 events

---

## Output

Write to `campaigns/{campaign-name}/tracking.md`:

```markdown
# Tracking Specification — {Campaign Name}

## Meta Pixel
- Pixel ID: {ID}
- Events configured: {list}
- CAPI status: {Active | Not configured}
- EMQ target: ≥8.0 for primary conversion event

## UTM Parameters
{table of all UTM URLs per ad}

## GA4 Events
{list of events with triggers}

## Verification Checklist
- [ ] Pixel fires on landing page
- [ ] Lead event fires on thank-you page
- [ ] CAPI active and deduplicating
- [ ] UTM URLs added to all ads in Ads Manager
- [ ] GA4 shows meta/paid as traffic source in real-time
- [ ] AEM configured for iOS (if running iOS-heavy audience)
```

After writing, confirm: "Tracking spec saved to `campaigns/{name}/tracking.md`. Add UTM URLs to ads in Ads Manager before launch."
