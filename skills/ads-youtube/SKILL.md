---
name: ads-youtube
description: "YouTube Ads specific analysis covering campaign types, creative quality, audience targeting, and measurement. Evaluates video ad performance across skippable, non-skippable, bumper, Shorts, and Demand Gen formats. Use when user says 'YouTube Ads', 'video ads', 'pre-roll', 'bumper ads', 'YouTube campaign', or 'Shorts ads'."
---

# YouTube Ads Analysis

## Process

1. Collect YouTube Ads data (Google Ads export filtered to Video campaigns)
2. Read `ads/references/google-audit.md` for YouTube-relevant checks
3. Read `ads/references/platform-specs.md` for video specifications
4. Read `ads/references/benchmarks.md` for YouTube benchmarks
5. Read `ads/references/scoring-system.md` for health score algorithm
6. **Validate**: confirm at least one active video campaign exists before proceeding
7. Evaluate campaign setup, creative quality, targeting, and measurement
8. **Validate**: verify all campaign types identified before generating report
9. Generate YouTube-specific findings report with health score

## Campaign Types Assessment

### Skippable In-Stream (TrueView)
- Length: 12s minimum, 15-30s recommended (can be longer)
- Bidding: Target CPV or Target CPA
- Skip rate benchmark: 65-80% is normal
- View rate: ≥15% is good
- Evaluate: hook quality in first 5 seconds, CTA card usage

### Non-Skippable In-Stream
- Length: up to 60s (expanded 2025; previously 15s/20s)
- Bidding: Target CPM
- Best for: brand awareness, reach campaigns
- Evaluate: message completeness, frequency capping, optimal length testing

### Bumper Ads
- Length: exactly 6s (non-skippable)
- Bidding: Target CPM
- Best for: reach extension, brand reinforcement
- Evaluate: single-message focus, brand visibility throughout

### YouTube Shorts Ads
- Format: vertical 9:16 (1080x1920)
- Length: up to 60s
- Best for: younger demographics, mobile-first
- Evaluate: native feel (not repurposed horizontal), sound-on optimization

### Demand Gen (replaces Discovery)
- Placements: YouTube Home Feed, Watch Next, Discover, Gmail
- Formats: image + video carousel, product feeds
- Evaluate: creative diversity, product feed quality, audience signals

## Creative Quality Assessment

### Hook Analysis (First 5 Seconds)
- Does the video capture attention immediately?
- Brand mention within first 5 seconds (recommended for awareness)
- Problem/benefit statement upfront (recommended for action campaigns)
- No slow intros, title cards, or logos-only openings

### Production Quality
- Audio quality: clear, professional, background music appropriate
- Visual quality: HD minimum (1080p), proper lighting
- Subtitles/captions: present (85% of Facebook video watched muted, ~30% on YouTube)
- End screen: CTA, subscribe button, related video cards

### Creative Volume
- ≥3 video variations per campaign (different hooks, lengths, messages)
- Mix of lengths tested (6s bumper + 15-60s non-skip + 30s skippable)
- Vertical (9:16) and horizontal (16:9) versions available
- Refresh cadence: every 4-8 weeks for top-performing campaigns

## Audience Targeting

### YouTube-Specific Targeting Options
- **Custom Intent**: target users searching for specific terms on YouTube/Google
- **In-Market Audiences**: users actively researching purchase categories
- **Affinity Audiences**: broad interest-based targeting for awareness
- **Customer Match**: first-party list upload for retargeting
- **Similar Audiences**: expansion from Customer Match seeds (if available)
- **Placement Targeting**: specific channels, videos, or topics

### Targeting Best Practices
- Separate campaigns for prospecting vs retargeting
- Layer audience signals in Demand Gen campaigns
- Exclude converted users from prospecting campaigns
- Use frequency capping (3-5 per week for awareness, 1-2 for direct response)

## Measurement

### Key YouTube Metrics
| Metric | Benchmark | Notes |
|--------|-----------|-------|
| View Rate (skippable) | ≥15% | Higher = better hook |
| CPV (skippable) | $0.01-0.10 | Varies by targeting |
| VTR (bumper) | 90%+ | Non-skippable, should be near 100% |
| CPM (non-skip) | $6-15 | Varies by market |
| CTR (Demand Gen) | ≥0.5% | Image+video combined |
| Brand Lift | Measurable | Requires Google Brand Lift Study |

### Attribution Considerations
- YouTube is upper/mid-funnel — don't judge by last-click alone
- Use data-driven attribution in Google Ads
- Track view-through conversions (important for video)
- Consider Brand Lift Studies for awareness campaigns
- Cross-channel impact: YouTube often assists Search/Shopping conversions

## Health Score

### YouTube Ads Health Score (0-100)

Weighted assessment from `ads/references/scoring-system.md`:

```
Category Weights:
Creative Quality:   30%  ██████████
Campaign Setup:     25%  ████████░░
Audience Targeting: 25%  ████████░░
Measurement:        20%  ██████░░░░

Grade: A (90-100), B (75-89), C (60-74), D (40-59), F (<40)
```

## Output

### YouTube Ads Report

```
YouTube Ads Assessment

Campaign Types:     ████████░░  Active formats evaluated
Creative Quality:   ██████████  Hook, production, volume
Audience Targeting: ███████░░░  Strategy and coverage
Measurement:        █████░░░░░  Attribution and tracking
```

### Deliverables
- `YOUTUBE-ADS-REPORT.md` — Campaign-by-campaign analysis
- Creative quality scorecard per video
- Audience strategy recommendations
- Measurement gap analysis
- Quick Wins for immediate improvement
