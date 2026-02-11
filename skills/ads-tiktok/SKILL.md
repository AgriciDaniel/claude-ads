---
name: ads-tiktok
user-invocable: false
description: >
  TikTok Ads deep analysis covering creative quality, tracking, bidding,
  campaign structure, and TikTok Shop. Evaluates 25 checks with emphasis on
  creative-first strategy, safe zone compliance, and Smart+ campaigns. Use
  when user says "TikTok Ads", "TikTok marketing", "TikTok Shop", "Spark Ads",
  "Smart+", or "TikTok campaign".
---

# TikTok Ads Deep Analysis

## Process

1. Collect TikTok Ads data (Ads Manager export, Pixel/Events API status)
2. Read `ads/references/tiktok-audit.md` for full 25-check audit
3. Read `ads/references/benchmarks.md` for TikTok-specific benchmarks
4. Read `ads/references/platform-specs.md` for creative specifications
5. Read `ads/references/scoring-system.md` for weighted scoring algorithm
6. Evaluate all applicable checks as PASS, WARNING, or FAIL
7. Calculate TikTok Ads Health Score (0-100)
8. Generate findings report with action plan

## What to Analyze

### Creative Quality (30% weight)
- ≥6 creatives per ad group (T05) — Critical
- All video 9:16 vertical 1080x1920 (T06) — Critical
- Native-looking content, not corporate/polished (T07)
- Hook in first 1-2 seconds (T08)
- No creative active >7 days with declining CTR (T09)
- Spark Ads tested: ~3% CTR vs ~2% standard (T10)
- TikTok Shop integration for e-commerce (T20)
- Video Shopping Ads tested (T21)
- Caption SEO with high-intent keywords (T22)
- Trending audio used (sound-on platform) (T23)
- Custom CTA button, not default (T24)
- Safe zone compliance: X:40-940, Y:150-1470 (T25)

### Technical Setup (25% weight)
- TikTok Pixel installed and firing on all pages (T01)
- Events API + ttclid passback active (T02)
- Standard events configured (ViewContent, AddToCart, Purchase, CompleteRegistration)
- Advanced matching parameters configured

### Bidding & Budget (20% weight)
- Bid strategy matches goal: Lowest Cost for volume, Cost Cap for efficiency (T11)
- Daily budget ≥50x target CPA per ad group (T12)
- Learning phase: ≥50 conversions per 7 days per ad group (T13)
- No edits during learning phase (resets learning)

### Structure & Settings (15% weight)
- Separate campaigns for prospecting vs retargeting (T03)
- Smart+ campaigns tested: 42% adoption, 1.41-1.67 ROAS (T04)
- Search Ads Toggle enabled (T14)
- Placement selection reviewed: TikTok, Pangle, etc. (T15)
- Dayparting aligned with audience activity (T16)

### Performance (10% weight)
- CTR ≥1.0% for in-feed ads (T17)
- CPA within target, 3x Kill Rule applies (T18)
- Average video watch time ≥6 seconds (T19)

## Creative-First Strategy

TikTok is a creative-first platform. Unlike Google/Meta where targeting and bidding
drive most performance, TikTok success depends primarily on creative quality.

### What Makes a TikTok Ad Work
- **Native feel**: looks like organic content, not a polished ad
- **Sound-on**: 93% of TikTok is consumed with sound (never run silent)
- **Fast hooks**: capture attention in 1-2 seconds or lose the viewer
- **Trend alignment**: use trending sounds, formats, and editing styles
- **UGC style**: user-generated content outperforms studio content
- **Vertical only**: 9:16 is non-negotiable (no letterboxed horizontal)

### Creative Testing Framework
1. Test 3-5 hooks per winning concept
2. Rotate creatives every 5-7 days (fatigue sets in fast)
3. Kill underperformers after 3 days if CTR <0.5%
4. Scale winners by duplicating (not increasing budget on same ad)
5. Repurpose winning concepts, not assets (fresh footage, same angle)

## Safe Zone

All critical text, logos, and CTAs must be within the safe zone:

```
┌──────────────────────┐
│   UNSAFE (status)    │  Y: 0-150px
├──────────────────────┤
│                 │UNSA│
│                 │FE  │
│   SAFE ZONE     │icon│  X: 40-940px
│   900×1320px    │    │  Y: 150-1470px
│                 │    │
│                 │    │  Right 140px: like/comment/share
├──────────────────────┤
│   UNSAFE (caption)   │  Y: 1470-1920px
└──────────────────────┘
```

## TikTok Shop Assessment

If e-commerce, evaluate TikTok Shop setup:
- Product catalog connected and synced
- Product detail pages complete (images, descriptions, reviews)
- Video Shopping Ads linking to in-app checkout
- Shop tab on TikTok profile configured
- Affiliate program active (if applicable)
- Shop CVR benchmark: >10% (significantly higher than standard landing page)

## Smart+ Campaigns

- 42% of advertisers have adopted Smart+ (TikTok's automated campaign type)
- Average ROAS: 1.41-1.67
- Best for: e-commerce with product feed, app installs
- Evaluate: is the advertiser testing Smart+ alongside manual campaigns?
- Compare Smart+ performance vs manual for same objectives

## TikTok Context

| Setting | Value |
|---------|-------|
| CPM | 40-60% cheaper than Meta |
| Spark Ads CTR | ~3% (vs ~2% standard) |
| Smart+ adoption | 42% of advertisers |
| Smart+ ROAS | 1.41-1.67 |
| Shop CVR | >10% |
| Available markets | 11 countries (US, UK, ID, MY, PH, SG, TH, VN, JP, KR, BR) |

## Key Thresholds

| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| CTR (in-feed) | ≥1.0% | 0.5-1.0% | <0.5% |
| Creatives per ad group | ≥6 | 3-5 | <3 |
| Video watch time | ≥6s | 3-6s | <3s |
| Learning conversions | ≥50/week | 30-50/week | <30/week |
| Daily budget | ≥50x CPA | 20-49x CPA | <20x CPA |
| Creative age (declining) | <7 days | 7-14 days | >14 days |

## Output

### TikTok Ads Health Score

```
TikTok Ads Health Score: XX/100 (Grade: X)

Creative Quality:  XX/100  ████████░░  (30%)
Technical Setup:   XX/100  ██████████  (25%)
Bidding & Budget:  XX/100  ███████░░░  (20%)
Structure:         XX/100  █████░░░░░  (15%)
Performance:       XX/100  ████████░░  (10%)
```

### Deliverables
- `TIKTOK-ADS-REPORT.md` — Full 25-check findings with pass/warning/fail
- Creative scorecard per ad (hook quality, safe zone, native feel)
- Smart+ vs manual performance comparison
- TikTok Shop readiness assessment (if e-commerce)
- Quick Wins sorted by impact
