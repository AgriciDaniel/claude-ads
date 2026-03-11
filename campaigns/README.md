# Campaigns

All active and past Meta ad campaigns are stored here. Each campaign gets its
own directory following the naming convention:

```
{client}_{objective}_{audience}_{YYYY-MM-DD}/
```

**Example:** `acme_leads_smb-owners_2026-03-15/`

## Campaign Directory Structure

```
{campaign-name}/
  brief.md          ← Offer, audience, budget, KPI targets
  structure.md      ← Campaign/ad set/ad spec for Ads Manager
  copy.md           ← All ad copy across 3 angles
  images/           ← Static ad creative (PNG files from /html-ad)
  tracking.md       ← UTM parameters, conversion events, GA4 config
  ab-test.md        ← A/B test plan with hypothesis and success metrics
  report.md         ← Performance report (post-launch)
  log.md            ← Running action log for every account change
```

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Campaign | `{client}_{objective}_{audience}_{date}` | `acme_leads_smb_2026-03` |
| Ad Set | `{audience-segment}_{placement}` | `smb-owners_feed` |
| Ad | `{angle}_{format}_{variant}` | `pain_image_v1` |
| UTM Source | `meta` | `meta` |
| UTM Medium | `paid` | `paid` |
| UTM Campaign | Match campaign name | `acme_leads_smb_2026-03` |
| UTM Content | Match ad name | `pain_image_v1` |

## Logging Rules

Every action taken on a Meta ad account must be logged in `log.md`:

```
## {YYYY-MM-DD}
- **{HH:MM}** — {action taken} ({reason})
```

Do not skip this step. The log is institutional memory.
