---
name: ads-microsoft
description: "Microsoft/Bing Ads deep analysis covering search, Performance Max, Audience Network, and Copilot integration. Evaluates 20 checks with focus on Google import validation, unique Microsoft features, and cost advantage assessment. Use when user says 'Microsoft Ads', 'Bing Ads', 'Bing PPC', 'Copilot ads', or 'Microsoft campaign'."
---

# Microsoft Ads Deep Analysis

## Process

1. Collect Microsoft Ads data (account export, UET tag status, import results)
2. Read `ads/references/microsoft-audit.md` for full 20-check audit
3. Read `ads/references/benchmarks.md` for Microsoft-specific benchmarks
4. Read `ads/references/scoring-system.md` for weighted scoring
5. Evaluate all applicable checks as PASS, WARNING, or FAIL
6. Calculate Microsoft Ads Health Score (0-100)
7. Generate findings report with action plan

## What to Analyze

### Technical Setup (25% weight)
- UET tag installed and firing on all pages (MS01)
- Enhanced conversions enabled (MS02)
- Google Ads import validated: URLs, extensions, bids, goals (MS03)

### Syndication & Bidding (20% weight)
- Search partner network reviewed, low-performers excluded (MS04)
- Audience Network enabled only if testing intentionally (MS05)
- Bid targets 20-35% lower than Google (CPC advantage) (MS06)
- Target New Customers enabled for PMax — Beta 2026 (MS07)

### Campaign Structure (20% weight)
- Campaign structure mirrors Google or follows best practices (MS08)
- Budget proportional to Bing volume: typically 20-30% of Google (MS09)
- LinkedIn profile targeting for B2B — unique advantage (MS10)

### Creative & Extensions (20% weight)
- RSA: ≥8 headlines, ≥3 descriptions (MS11)
- Multimedia Ads tested — unique rich format (MS12)
- Ad copy optimized for Bing demographics (MS13)
- Action Extension utilized — unique to Microsoft (MS19)
- Filter Link Extension tested (MS20)

### Settings & Performance (15% weight)
- Copilot chat placement enabled for PMax: 73% CTR lift (MS14)
- Conversion goals configured natively, not relying on imported (MS15)
- CPC 20-40% lower than Google for same keywords (MS16)
- CVR comparable to Google, not >50% lower (MS17)
- Impression share tracked for brand and top terms (MS18)

## Google Import Validation

Most Microsoft Ads accounts start as Google Ads imports. Critical validation:

### What Transfers Correctly
- Campaign structure and ad groups
- Keywords and match types
- RSA headlines and descriptions
- Basic bid strategies

### What Needs Manual Review
- **URLs**: verify all landing page URLs are correct post-import
- **Extensions**: not all Google extensions have Microsoft equivalents
- **Bid amounts**: should be 20-35% lower (don't import Google bids as-is)
- **Conversion goals**: re-create natively for better tracking
- **Audiences**: import may miss segments, verify all are present
- **Negative keywords**: verify shared negative lists transferred

### Import Schedule
- Auto-import: useful but review changes monthly
- Manual import: more control, recommended for large accounts
- Never import without post-import audit

## Copilot Integration

Microsoft's AI assistant creates unique ad opportunities:

### Copilot Chat Ads
- Available in Performance Max campaigns
- 73% CTR lift reported in chat placement
- Copilot Checkout launched Jan 2026 (in-chat purchase)
- Natural language ad delivery (conversational context)

### How to Evaluate
- Is Copilot placement enabled? (If not, HIGH priority for PMax)
- What % of impressions/clicks come from Copilot?
- CTR/CVR comparison: Copilot vs traditional placements
- Ad copy quality: does it read well in conversational context?

## Microsoft-Unique Features

These features are exclusive to Microsoft Ads — evaluate adoption:

| Feature | Description | Priority |
|---------|-------------|----------|
| Multimedia Ads | Image-rich search ads with visual elements | Medium |
| Action Extension | CTA button directly in search ad | Medium |
| Filter Link Extension | Filterable category links in ad | Low |
| LinkedIn Profile Targeting | Target by company, industry, job function | High (B2B) |
| Copilot Chat Placement | Ads within Copilot conversations | High |

## Bing Demographic Context

Microsoft Ads reach a distinct audience:
- Older demographic (35-65+ over-indexed)
- Higher household income (top 25% income brackets)
- Desktop-heavy (Windows default browser = Edge = Bing)
- Enterprise/corporate users (Office 365 integration)

Ad copy optimization for this audience:
- Professional tone, less casual than Google/Meta
- Emphasize quality, reliability, premium positioning
- Desktop-optimized landing pages matter more
- B2B messaging resonates strongly

## Key Thresholds

| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| CTR (Search) | ≥2.83% | 1.5-2.83% | <1.5% |
| CPC (Search) | ≤$1.55 | $1.55-2.50 | >$2.50 |
| CPC vs Google | 20-40% lower | 10-20% lower | Same or higher |
| CVR vs Google | Within 20% | 20-50% lower | >50% lower |
| Impression share (brand) | ≥80% | 60-80% | <60% |

## Output

### Microsoft Ads Health Score

```
Microsoft Ads Health Score: XX/100 (Grade: X)

Technical Setup:   XX/100  ████████░░  (25%)
Syndication:       XX/100  ██████████  (20%)
Structure:         XX/100  ███████░░░  (20%)
Creative:          XX/100  █████░░░░░  (20%)
Settings:          XX/100  ████████░░  (15%)
```

### Deliverables
- `MICROSOFT-ADS-REPORT.md` — Full 20-check findings with pass/warning/fail
- Google import validation results
- Copilot integration readiness assessment
- Cost advantage analysis (CPC savings vs Google)
- Microsoft-unique feature adoption checklist
- Quick Wins sorted by impact
