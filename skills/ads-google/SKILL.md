---
name: ads-google
description: "Google Ads deep analysis covering Search, Performance Max, Display, YouTube, and Demand Gen campaigns. Evaluates 74 checks across conversion tracking, wasted spend, account structure, keywords, ads, and settings. Use when user says 'Google Ads', 'Google PPC', 'search ads', 'PMax', 'Performance Max', or 'Google campaign'."
---

# Google Ads Deep Analysis

## Process

1. Collect Google Ads account data (export, Change History, Search Terms Report)
2. **Validate**: confirm data covers ≥30 days and includes Search Terms Report before proceeding
3. Read `ads/references/google-audit.md` for full 74-check audit
4. Read `ads/references/benchmarks.md` for Google-specific benchmarks
5. Read `ads/references/scoring-system.md` for weighted scoring
6. Evaluate all applicable checks as PASS, WARNING, or FAIL
7. **Validate**: confirm all 74 checks evaluated before calculating score
8. Calculate Google Ads Health Score (0-100)
9. Generate findings report with action plan

## What to Analyze

### Conversion Tracking (25% weight)
- Google tag (gtag.js) installed and firing on all pages
- Enhanced Conversions active (hashed first-party data)
- Consent Mode v2 implemented (required for EU/EEA)
- Conversion actions mapped correctly (primary vs secondary)
- Offline conversion import configured (for lead gen)
- Server-side tagging via GTM (recommended for accuracy)
- Attribution model: data-driven preferred (last-click as fallback only)
- Conversion lag analysis (are conversions still trickling in?)

### Wasted Spend (20% weight)
- Search Terms Report reviewed (last 30 days minimum)
- Negative keyword coverage adequate (shared lists + campaign-level)
- Display placement audit (exclude low-quality sites)
- Invalid click rate within norms (<10%)
- Broad Match only used with Smart Bidding (NEVER without it)
- Brand/non-brand campaigns separated
- Geographic targeting precise (no wasted international spend)

**Negative Keyword Rules (critical — bad negatives kill campaigns):**
- NEVER suggest Broad Match negatives unless explicitly justified — they block too broadly
- Default to **Exact Match** `[keyword]` for specific irrelevant queries
- Use **Phrase Match** `"keyword"` for irrelevant intent patterns
- Source negatives from actual Search Terms Report irrelevant queries, NOT guesses
- Group into themed lists: Informational (how-to, DIY, what is), Job-seeker (jobs, careers, salary), Competitor (only if intentionally excluded), Free-intent (free, crack, torrent)
- Recommend **Shared Negative Lists** at the account level — not just campaign-level
- Review existing negatives for over-blocking (are any negatives accidentally blocking converting queries?)

### Account Structure (15% weight)
- Campaign-level organization follows business logic
- Ad groups themed tightly (15-20 keywords max per group)
- RSA ad groups have ≥3 active ads
- PMax campaigns structured correctly (asset groups, signals)
- SKAGs evaluated (migrate to themed groups if present)
- Campaign labels/naming conventions consistent

### Keywords (15% weight)
- Match type strategy appropriate (Exact → Phrase → Broad progression)
- Quality Score distribution (aim ≥7 average)
- Low QS keywords flagged (<5 = FAIL, 5-6 = WARNING)
- Keyword cannibalization check (same keywords in multiple campaigns)
- Impression share tracked for top keywords
- Keyword bid adjustments set for devices/locations/audiences

### Ads (15% weight)
- RSA: ≥8 unique headlines, ≥3 descriptions per ad group
- RSA: ad strength "Good" or "Excellent" (not "Poor" or "Average")
- Pin usage minimal and strategic (over-pinning reduces RSA flexibility)
- Ad extensions: sitelinks (≥4), callouts (≥4), structured snippets, image
- Dynamic keyword insertion used appropriately
- Ad copy includes CTA, value proposition, differentiators

### Settings (10% weight)
- Bid strategy appropriate for campaign maturity and goals
- Budget pacing: no campaigns limited by budget (unless intentional)
- Ad schedule aligned with business hours/conversion patterns
- Device bid adjustments set based on performance data
- Location targeting: "Presence" not "Presence or Interest"
- Network settings: Search Partners reviewed, Display opt-out for Search

## PMax Deep Dive

If Performance Max campaigns exist, additionally evaluate:
- Asset group diversity (text, images, video, feeds)
- Audience signals configured (custom segments, lists, demographics)
- URL expansion settings reviewed (opt-out of irrelevant pages)
- Brand exclusions applied (prevent cannibalizing brand search)
- Search themes utilized (2024 feature)
- Final URL expansion: enabled or disabled with justification
- Insights tab reviewed (search categories, audience segments)

## AI Max for Search (2026)

If AI Max for Search is available/active:
- Broad Match + AI Max integration evaluated
- Auto-generated headline performance monitored
- Search term categories reviewed for relevance
- Budget impact assessed (AI Max can shift spend)

## Key Thresholds

| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| Quality Score (avg) | ≥7 | 5-6 | <5 |
| CTR (Search) | ≥6.66% | 3-6.66% | <3% |
| CVR (Search) | ≥7.52% | 3-7.52% | <3% |
| CPC (Search) | ≤$5.26 | $5.26-8.00 | >$8.00 |
| Wasted Spend | <10% | 10-20% | >20% |
| Ad Strength | Good+ | Average | Poor |
| Invalid Clicks | <5% | 5-10% | >10% |

## Output

### Google Ads Health Score

```
Google Ads Health Score: XX/100 (Grade: X)

Conversion Tracking: XX/100  ████████░░  (25%)
Wasted Spend:        XX/100  ██████████  (20%)
Account Structure:   XX/100  ███████░░░  (15%)
Keywords:            XX/100  █████░░░░░  (15%)
Ads:                 XX/100  ████████░░  (15%)
Settings:            XX/100  ██████████  (10%)
```

### Deliverables
- `GOOGLE-ADS-REPORT.md` — Full 74-check findings with pass/warning/fail
- Wasted spend estimate (monthly $ value)
- Quick Wins sorted by impact
- PMax-specific recommendations (if applicable)
- Keyword health matrix with QS, CTR, CVR per keyword group
