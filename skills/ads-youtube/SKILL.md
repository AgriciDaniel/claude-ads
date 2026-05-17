---
name: ads-youtube
description: "YouTube Ads specific analysis covering campaign types, creative quality, audience targeting, and measurement. Evaluates video ad performance across skippable in-stream, non-skippable, bumper, Shorts, Demand Gen, and Connected TV (CTV) formats. Covers VAC→Demand Gen migration, Shorts creative requirements, CTV shoppable ads, and frequency capping. Use when user says YouTube Ads, video ads, pre-roll, bumper ads, skippable in-stream, YouTube campaign, YouTube Shorts ads, Demand Gen, VAC, or CTV YouTube ads."
user-invokable: false
tested_date: 2026-05-17
tested_with: claude-code v2.x
---

# YouTube Ads Analysis

<!-- Updated: 2026-04-13 | v1.5: Demand Gen replaces VAC, Shorts expansion, CTV section, frequency capping -->

## Process

1. Collect YouTube Ads data (Google Ads export filtered to Video campaigns)
2. Read `ads/references/google-audit.md` for YouTube-relevant checks (incl. G-DG1 through G-DG3, G-CTV1)
3. Read `ads/references/platform-specs.md` for video specifications
4. Read `ads/references/benchmarks.md` for YouTube benchmarks
5. Read `ads/references/scoring-system.md` for health score algorithm
6. **Validate**: confirm at least one active video campaign exists before proceeding
7. **Check**: flag any remaining Video Action Campaigns (VAC). All auto-upgraded to Demand Gen by April 2026
8. Evaluate campaign setup, creative quality, targeting, and measurement
9. **Validate**: verify all campaign types identified before generating report
10. Generate YouTube-specific findings report with health score

## Campaign Types Assessment

### YT-01: Skippable In-Stream (TrueView)
- Length: 12s minimum, 15-30s recommended (can be longer)
- Bidding: Target CPV or Target CPA
- Skip rate benchmark: 65-80% is normal
- View rate: ≥15% is good
- Evaluate: hook quality in first 5 seconds, CTA card usage

### YT-02: Non-Skippable In-Stream
- Length: up to 60s (expanded 2025; previously 15s/20s)
- Bidding: Target CPM
- Best for: brand awareness, reach campaigns
- Evaluate: message completeness, frequency capping, optimal length testing

### YT-03: Bumper Ads
- Length: exactly 6s (non-skippable)
- Bidding: Target CPM
- Best for: reach extension, brand reinforcement
- Evaluate: single-message focus, brand visibility throughout

### YT-04: YouTube Shorts Ads
- Format: vertical 9:16 (1080x1920 recommended)
- Length: up to 60s, sound-on required
- Music/voiceover increases conversions by **over 20%**
- CTA button appears at **3 seconds** for PMax/App/Demand Gen, **10 seconds** for Video View/Reach
- Top-performing Shorts ads feel organic, authentic, and creator-like
- YouTube Select Shorts lineups deliver 90% longer viewing vs competitor platforms (MediaScience data)
- Placement exclusions for Shorts only work at **account level** (not campaign/ad group)
- Best for: younger demographics, mobile-first, action campaigns

### YT-05: Demand Gen (fully replaced Video Action Campaigns, April 2026)
- **All VACs auto-upgraded to Demand Gen by April 2026**. Flag any remaining VAC campaigns as deprecated
- Placements: YouTube Home Feed, Watch Next, Discover, Gmail, Google Display Network (with channel controls)
- Multi-format critical: advertisers uploading **both video AND image assets** see **20% more conversions** at same CPA vs video-only (G-DG1 check)
- DoorDash case study: 15x higher conversion rate, 50% lower CPA vs VAC
- **Major limitation: frequency capping is NOT supported** in Demand Gen. Significant loss from VAC. Only workaround: Video Frequency Groups (alpha). Flag former VAC campaigns that relied on frequency caps (G-DG3 check)
- Evaluate: creative diversity (video + image), product feed quality, audience signals, frequency monitoring

### Connected TV (CTV)
- YouTube's fastest-growing surface: ~150 million Americans watching on TV screens
- **75% of YouTube ad spend** now on CTV (Brandcast 2025)
- 30-second non-skippable ads available exclusively on CTV
- Co-viewing metrics rolled out globally for comparison with linear TV
- **Shoppable CTV (2026)**: uses Merchant Center feeds with QR codes
- **Critical limitation: Floodlight conversion measurement DOES NOT work on CTV devices** (G-CTV1 check). Use Google Ads conversion tracking or GA4 instead
- Evaluate: CTV-specific creative (larger text, simpler visuals for TV viewing distance), QR code shoppability, measurement strategy

## Creative Quality Assessment

### YT-06: Hook Analysis (First 5 Seconds)
- Does the video capture attention immediately?
- Brand mention within first 5 seconds (recommended for awareness)
- Problem/benefit statement upfront (recommended for action campaigns)
- No slow intros, title cards, or logos-only openings
- ABCD framework: Attention (hook immediately) → Branding (show up early) → Connection (humanize) → Direction (explicit CTA). Ads following ABCDs deliver 30% lift in short-term sales likelihood and 17% lift in long-term brand contribution (Google/Kantar)

### YT-07: Production Quality
- Audio quality: clear, professional, background music appropriate
- Visual quality: HD minimum (1080p), proper lighting
- Subtitles/captions: present (85% of Facebook video watched muted, ~30% on YouTube)
- End screen: CTA, subscribe button, related video cards

### YT-08: Creative Volume
- ≥3 video variations per campaign (different hooks, lengths, messages)
- Mix of lengths tested (6s bumper + 15-60s non-skip + 30s skippable)
- Vertical (9:16) and horizontal (16:9) versions available (YT-09)
- Refresh cadence: every 4-8 weeks for top-performing campaigns

## Audience Targeting

### YT-10: YouTube-Specific Targeting Options
- **Custom Intent**: target users searching for specific terms on YouTube/Google
- **In-Market Audiences**: users actively researching purchase categories
- **Affinity Audiences**: broad interest-based targeting for awareness
- **Customer Match**: first-party list upload for retargeting
- **Similar Audiences**: expansion from Customer Match seeds (if available)
- **Placement Targeting**: specific channels, videos, or topics

### YT-11: Remarketing Setup
- Separate campaigns for prospecting vs retargeting
- Layer audience signals in Demand Gen campaigns
- Exclude converted users from prospecting campaigns

### YT-12: Frequency Management
- Use frequency capping (3-5 per week for awareness, 1-2 for direct response). For Target Frequency campaigns, set up to 4/week. 95%+ of campaigns achieved their goals. Nielsen MMM: brands can increase frequency from 1 to 3/week with consistent ROI
- **Triscuit case study**: Target frequency 2/week = 93% higher absolute ad recall lift at 40% cheaper cost per lifted user
- **Note**: Demand Gen does NOT support frequency capping. DV360 lifetime frequency caps deprecated after Feb 28, 2025 (max period now 30 days)

## Measurement

### YT-13: Key YouTube Metrics
| Metric | Benchmark | Notes |
|--------|-----------|-------|
| View Rate (skippable) | ≥15% | Higher = better hook |
| CPV (skippable) | $0.01-0.10 | Varies by targeting |
| VTR (bumper) | 90%+ | Non-skippable, should be near 100% |
| CPM (non-skip) | $6-15 | Varies by market |
| CTR (Demand Gen) | ≥0.5% | Image+video combined |
| Brand Lift | Measurable | Requires Google Brand Lift Study |

### YT-13 (continued): Attribution Considerations
- YouTube is upper/mid-funnel; don't judge by last-click alone
- Use data-driven attribution in Google Ads
- Track view-through conversions (important for video)
- Consider Brand Lift Studies for awareness campaigns (YT-14)
- Cross-channel impact: YouTube often assists Search/Shopping conversions

### YT-15: CTV Measurement
- **Critical**: Floodlight conversion measurement does NOT work on CTV devices (G-CTV1 check)
- Use Google Ads conversion tracking or GA4 for CTV attribution
- Co-viewing metrics available globally for comparison with linear TV
- CTV Brand Lift studies recommended for awareness campaigns on TV screens

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

## Shorts Hook Template

High-performing Shorts ad pattern:
1. **Problem identification** (0-2s): Open with a relatable pain point or attention-grabbing question
2. **Product reveal** (2-5s): Show the product/solution in context
3. **CTA with urgency** (final 2s): Clear next step with time or quantity pressure

## Quick Wins

| Check | Fix | Time |
|-------|-----|------|
| YT-05: Demand Gen migration | Upgrade remaining VACs to Demand Gen with video+image | 15 min |
| YT-04: Shorts vertical | Create 9:16 vertical cuts of existing ads | 10 min |
| YT-09: Add image assets | Upload image assets to Demand Gen (20% more conversions) | 10 min |
| YT-12: Frequency monitoring | Set Target Frequency to 4/week for awareness campaigns | 5 min |

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
- `YOUTUBE-ADS-REPORT.md`: Campaign-by-campaign analysis
- Creative quality scorecard per video
- Audience strategy recommendations
- Measurement gap analysis
- Quick Wins for immediate improvement

## Deprecated (v1.5)

- **Video Action Campaigns**: Fully deprecated April 2026, replaced by Demand Gen
- **Overlay ads**: Discontinued April 6, 2023
- **Rule-based attribution** (first click, linear, time decay, position-based): All auto-upgraded to DDA
- **DV360 lifetime frequency caps**: Max period now 30 days (changed Feb 28, 2025)
