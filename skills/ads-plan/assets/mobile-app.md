<!-- Updated: 2026-05-17 -->
# Mobile App Paid Advertising Template

## Industry Characteristics

- App install is the primary conversion event
- Post-install events (registration, purchase, subscription) determine true value
- LTV (lifetime value) optimization is critical; not all installs are equal
- App store optimization (ASO) and paid acquisition work together
- Deep linking required for seamless ad-to-app experience
- Attribution complexity; AdAttributionKit/SKAdNetwork (iOS); Google Play Install Referrer + GA4 + MMP (Android, post Privacy Sandbox retirement Oct 17, 2025)
- High install volume needed for algorithm optimization (especially Google UAC)

## Recommended Platform Mix

| Platform | Role | Budget % | Why |
|----------|------|----------|-----|
| Apple Ads | Primary | 25-30% | High-intent (searching App Store), iOS-specific, best CVR |
| Google App (UAC) | Primary | 25-30% | Cross-network reach (Search, Play, YouTube, Display) |
| Meta App Installs | Primary | 20-25% | Precise targeting, Advantage+ App Campaigns |
| TikTok | Secondary | 15-20% | High engagement, young demographics, low CPM |

## Campaign Architecture

```
Account; Meta
├── Advantage+ App Campaigns (AAC)
│   └── Auto-optimized for app events
├── App Install; Prospecting
│   ├── Ad Set: Lookalike 1% of high-LTV users
│   ├── Ad Set: Interest-based (app category relevant)
│   └── Ad Set: Broad (creative-driven, at scale)
├── App Install; Value Optimization
│   └── Optimize for purchase/subscription (not just install)
├── Re-engagement
│   ├── Ad Set: Lapsed users (30-60 days inactive)
│   ├── Ad Set: Trial users (didn't subscribe)
│   └── Ad Set: Free users (upsell to premium)
└── Testing
    └── New creative, new audiences, new events

Account; Google
├── UAC; Install Volume
│   └── Maximize conversions (install)
├── UAC; In-App Action
│   └── Optimize for registration/purchase/subscription
├── UAC; Value
│   └── Target ROAS on in-app purchases
└── UAC; Pre-Registration (if applicable)

Account; Apple Ads
├── Brand
│   └── Exact match on app name
├── Category
│   ├── Discovery: Search Match enabled
│   └── Exact: [category] + app, best [category] app
├── Competitor
│   └── Competitor app names
└── Discovery
    └── Broad match, search match for keyword research

Account; TikTok
├── App Install
│   ├── Spark Ads (organic content boosted)
│   └── In-Feed (demo/tutorial style)
├── Smart+ App Campaigns
│   └── Auto-optimized
└── Re-engagement
    └── Lapsed user deep links
```

## Creative Strategy

### What Works for Mobile Apps
- **App demo videos**: 15-30s showing core functionality
- **Screen recordings**: actual app usage with finger taps/swipes
- **UGC reactions**: users discovering the app for the first time
- **Problem → solution**: "Tired of [problem]? This app fixes it in 10 seconds"
- **Social proof**: "10M+ downloads", "4.8★ on App Store"
- **Before/after**: life without app vs with app

### Creative by Platform
| Platform | Format | Length | Notes |
|----------|--------|--------|-------|
| Meta | Video (9:16 + 1:1) | 15-30s | Multiple aspect ratios required |
| Google UAC | Video + image + HTML5 | 15-30s video | Provide 20+ creative assets |
| TikTok | Vertical video (9:16) | 15-30s | Native-looking, not polished |
| Apple Ads | App Store screenshots | N/A | Custom Product Pages recommended |

### App Store Creative Alignment
- Ad creative should match App Store listing (message match)
- Custom Product Pages (Apple) for different ad campaigns
- Custom Store Listings (Google Play) for different campaigns
- App preview video on store listing should match ad creative themes

## Targeting Strategy

### Meta
- **Lookalikes**: 1% of highest-LTV users (best), subscribers, power users
- **Interest-based**: app category interests, competitor apps
- **Broad**: works well at scale with Advantage+ App Campaigns
- **Exclusions**: existing app users (device-based), past installers

### Google UAC
- **Targeting is automated**: Google optimizes across Search, YouTube, Play, Display
- **Control levers**: creative assets, bid strategy, geography, language
- **Budget**: minimum $50/day for algorithm learning

### Apple Ads
- **Exact match**: high-intent category keywords, competitor names
- **Broad match + Search Match**: keyword discovery
- **Custom Product Pages**: match search intent to landing experience

### Deep Linking (Critical)
- Deferred deep links: new users → install → open to specific content
- Standard deep links: existing users → open to specific screen
- Universal Links (iOS) and App Links (Android) configured
- Attribution parameters passed through deep links

## Budget Guidelines

| Metric | Mobile App Benchmark |
|--------|---------------------|
| Meta CPI (iOS) | $3-$8 |
| Meta CPI (Android) | $1-$4 |
| Google UAC CPI | $1-$5 |
| Apple Ads CPI | $2-$5 |
| TikTok CPI | $1-$3 |
| Meta CPA (subscription) | $15-$50 |
| Cost per subscriber | 3-5x CPI |
| Min monthly budget | $5,000+ (Meta + UAC minimum viable) |

### Budget Allocation by App Type
| App Type | Meta % | Google % | TikTok % | Apple % |
|----------|--------|----------|----------|---------|
| Gaming | 35% | 30% | 20% | 15% |
| Subscription (utility) | 40% | 25% | 15% | 20% |
| E-commerce app | 30% | 35% | 20% | 15% |
| Social/community | 30% | 25% | 30% | 15% |

## Bidding Strategy Selection

| Platform | Optimization Goal | Recommended Strategy |
|----------|------------------|--------------------|
| Meta | App installs (volume) | Lowest Cost (Advantage+ App Campaigns) |
| Meta | In-app events | Cost Cap or ROAS Goal |
| Google UAC | Install volume | Maximize Conversions (install) |
| Google UAC | In-app actions | Target CPA (registration/purchase) |
| Google UAC | Revenue | Target ROAS (in-app purchases) |
| Apple Search | Default | Cost-Per-Tap (CPT) manual bidding |
| Apple Search | Scale | Cost-Per-Acquisition (CPA) goal |
| TikTok | <50 conversions/week | Maximum Delivery |
| TikTok | 50+ conversions/week | Cost Cap |

## Attribution & Measurement

- **MMP required**: AppsFlyer, Adjust, Branch, or Singular
- **AdAttributionKit (iOS)**: dual attribution with SKAdNetwork (SKAN v1-3), configurable windows per WWDC 2025, view-through 24h post-impression; SKAN alone limited to 63 conversion values
- **Android attribution (post Oct 2025)**: Google Play Install Referrer + GA4 + MMP — Privacy Sandbox (Attribution Reporting API, Topics API, Protected Audience) was retired Oct 17, 2025
- **Cohort analysis**: Day 1, Day 7, Day 30 retention rates
- **LTV modeling**: predict 180-day LTV from Day 7 behavior
- **Key formula**: LTV > (CPI × 3) for sustainable growth

## KPI Targets

| Metric | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| CPI | Baseline | -20% | -30% |
| Day 1 Retention | Track | 30%+ | 35%+ |
| Day 7 Retention | Track | 15%+ | 20%+ |
| Install → Registration | Track | 40%+ | 50%+ |
| CPA (key event) | Baseline | Target | Target -15% |
| LTV:CPI Ratio | Track | 2:1 | 3:1+ |

## Common Pitfalls

- Optimizing for installs instead of post-install events (low-quality users)
- Not using an MMP (Mobile Measurement Partner); no cross-platform attribution
- Ignoring organic ASO; paid and organic should work together
- Same creative for iOS and Android (different user behaviors and store layouts)
- Not setting up Custom Product Pages (Apple) / Custom Store Listings (Google Play)
- Deep linking not configured; users land on App Store instead of specific content
- Budget too low for Google UAC (<$50/day, algorithm can't learn)
- Not tracking Day 7+ LTV; overspending on low-retention user segments
- Ignoring SKAdNetwork postback configuration (iOS attribution data lost)
