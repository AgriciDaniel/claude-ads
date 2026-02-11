<!-- Updated: 2026-02-11 -->
# E-commerce Paid Advertising Template

## Industry Characteristics

- Transaction-focused with short purchase cycles
- ROAS is the primary success metric
- Product catalog/feed drives Shopping and PMax performance
- Seasonal demand patterns (Q4 holiday, back-to-school, etc.)
- High creative volume needed across formats (static, video, UGC)
- Price competition and margin pressure require efficiency focus
- Mobile commerce dominates (82.9% of ad clicks)

## Recommended Platform Mix

| Platform | Role | Budget % | Why |
|----------|------|----------|-----|
| Meta (FB/IG) | Primary | 50-68% | Prospecting + Advantage+ Shopping Campaigns, highest scale for DTC |
| Google Shopping/PMax | Secondary | 23-30% | High-intent product searches, Shopping ads |
| TikTok | Secondary | 5-15% | Product discovery, UGC, TikTok Shop |
| Email | Supporting | 5% | Retention, repeat purchase, owned audience |
| Microsoft Shopping | Testing | 2-5% | Google import, higher-income audience |

## Campaign Architecture

```
Account — Google
├── Brand Search (always-on)
├── PMax — Core Products
│   ├── Asset Group: Best Sellers
│   ├── Asset Group: New Arrivals
│   └── Asset Group: Sale Items
├── PMax — Categories
│   ├── Asset Group: Category A
│   └── Asset Group: Category B
├── Standard Shopping (price-sensitive categories)
└── Search — Non-Brand (category terms)

Account — Meta
├── Advantage+ Shopping Campaign (ASC)
│   └── 150+ creatives (image + video + UGC mix)
├── Prospecting — Interest/Lookalike
│   ├── Ad Set: Top Performers lookalike
│   └── Ad Set: Interest stacks
├── Retargeting
│   ├── Ad Set: View Content (7 days)
│   ├── Ad Set: Add to Cart (14 days)
│   └── Ad Set: Past Purchasers (180 days, upsell/cross-sell)
└── Testing
    └── New creatives, audiences, formats

Account — TikTok
├── TikTok Shop (if eligible)
├── Smart+ Campaigns
├── Spark Ads (creator content)
└── Standard In-Feed (product demos)
```

## Creative Strategy

### What Works for E-commerce
- **UGC unboxing/review**: authentic customer content outperforms studio (Spark Ads ~3% CTR vs ~2% standard)
- **Product demos**: show product in use, feature close-ups
- **Before/after**: transformation content for applicable products
- **Price anchoring**: was/now pricing, bundle savings
- **Social proof**: review count, star ratings, "best seller" badges
- **Lifestyle imagery**: product in context, aspirational

### Creative Volume Requirements
| Platform | Min Active Creatives | Refresh Cadence |
|----------|---------------------|-----------------|
| Meta ASC | 150+ in campaign | 2-4 weeks |
| Meta Standard | 5+ per ad set | 2-4 weeks |
| TikTok | 6+ per ad group | 5-7 days |
| Google PMax | Text + 20 images + 5 videos per asset group | 4-8 weeks |

### Seasonal Creative Calendar
- **Q1**: New year deals, resolution products
- **Q2**: Mother's Day, spring/summer launch
- **Q3**: Back-to-school, Labor Day, early fall
- **Q4**: Black Friday, Cyber Monday, holiday gifting (increase budget 2-3x)

## Targeting Strategy

### Google
- **Shopping/PMax**: feed-driven, optimize product titles and descriptions
- **Search**: category terms, "buy [product]", "[product] near me"
- **Exclusions**: negative keywords for informational queries, competitor brands (unless strategic)

### Meta
- **Advantage+ Audiences**: let Meta's algorithm optimize (broad works with good creative)
- **Lookalike**: top 5% purchasers, high AOV customers
- **Interest stacks**: combine 3-5 interests for refined prospecting
- **Exclusions**: past purchasers (unless cross-sell campaign)

### Product Feed Optimization (Critical)
- Product titles: [Brand] + [Product Name] + [Key Attribute] + [Size/Color]
- High-quality images: white background for Shopping, lifestyle for PMax
- Accurate pricing and availability (stale data = disapprovals)
- Custom labels for bid segmentation (margin tiers, best sellers, seasonal)
- Supplemental feeds for additional attributes

## Budget Guidelines

| Metric | E-commerce Benchmark |
|--------|---------------------|
| Google Shopping CPC | $0.50-$1.50 |
| Google Search CPC | $1.15 |
| Google Search CTR | 4.13% |
| Google ROAS | 3.68 |
| Meta CPC | $0.70-$1.32 (seasonal) |
| Meta ROAS | 2.19 (median), 4.52 (ASC) |
| TikTok CPM | $3.21-$10 |
| TikTok Shop CVR | >10% |
| CPA (Triple Whale) | $23.74 (median, +12.35% YoY) |
| Min monthly budget | $3,000+ (Google + Meta minimum viable) |

### Bidding Strategy Selection

| Platform | Monthly Conversions | Recommended Strategy |
|----------|--------------------|--------------------|
| Google | <15 | Maximize Clicks (cap CPC) |
| Google | 15-29 | Maximize Conversions |
| Google | 30+ | Target CPA |
| Google | 50+ with dynamic values | Target ROAS (recommended for e-commerce) |
| Meta | Default | Lowest Cost |
| Meta | Efficiency priority | Cost Cap at target CPA |
| Meta | Revenue tracking | ROAS Goal (4.0+ target) |
| TikTok | <50 conversions/week | Maximum Delivery |
| TikTok | 50+ conversions/week | Cost Cap |

### Seasonal Budget Adjustments
- **Q4 (Oct-Dec)**: increase 2-3x (CPMs rise 30-50%, but CVR rises too)
- **January**: reduce to baseline or below (post-holiday dip)
- **Sale events**: allocate 20% budget surge 3 days before through event

## KPI Targets

| Metric | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| ROAS | 2.0 (learning) | 3.0 | 4.0+ |
| CPA | Baseline | -15% | -25% |
| AOV | Baseline | +5% (bundles) | +10% |
| New Customer % | Track | 40%+ | 40%+ |
| MER | Track | 3.0 | 4.0+ |
| Google QS (weighted avg) | Track | ≥6 | ≥7 |
| Meta EMQ | Track | ≥7.0 | ≥8.0 (87% of advertisers are below this) |

## Common Pitfalls

- Running PMax without a well-optimized product feed (garbage in, garbage out)
- Not segmenting products by margin tier (bidding same for 10% and 60% margin)
- Ignoring new vs returning customer tracking (ROAS looks great on repeat buyers)
- Creative fatigue on Meta — not refreshing every 2-4 weeks
- TikTok Shop eligibility: only available in 11 countries (US, UK, Southeast Asia)
- Q4 panic: starting holiday campaigns in November instead of October (learning phase)
- Not running brand campaigns — letting competitors steal your branded traffic
- Measuring platform-reported ROAS without blended MER check (double-counting)
