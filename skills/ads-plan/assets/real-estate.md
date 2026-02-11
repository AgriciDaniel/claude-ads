<!-- Updated: 2026-02-11 -->
# Real Estate Paid Advertising Template

## Industry Characteristics

- **Special Ad Category**: housing ads require Fair Housing compliance (Meta, Google)
- Geographic hyper-targeting essential (neighborhoods, ZIP codes, school districts)
- Visual-first — high-quality property photos and video tours drive engagement
- Lead generation focus — phone calls, form fills, showing requests
- Seasonal patterns: spring/summer peak, winter slowdown
- Dual audience: buyers and sellers require different campaigns
- Agent personal brand often matters as much as brokerage brand
- Long consideration phase but individual listings have time pressure

## Special Ad Category Requirements

### Meta — Special Ad Category: Housing
- **Must declare** housing category for all real estate ads
- **Restricted targeting**: no age, gender, ZIP code, or detailed demographics
- **Minimum radius**: 15 miles (cannot target tighter)
- **Lookalike unavailable**: use Special Ad Audiences instead
- **Interest exclusions limited**: cannot exclude based on demographics

### Google — Fair Housing Compliance
- Housing/real estate ads subject to personalized ad policies
- Cannot target based on protected characteristics
- Location targeting allowed but cannot exclude specific demographics
- Employment and credit ads have similar restrictions

## Recommended Platform Mix

| Platform | Role | Budget % | Why |
|----------|------|----------|-----|
| Meta Lead Forms | Primary | 40-50% | Visual property ads, listing promotion, seller leads, lead gen forms |
| Google Search | Primary | 30-40% | High-intent "homes for sale in [area]" queries |
| LinkedIn | Testing | 5-10% | Luxury real estate, investor targeting, relocation |
| YouTube | Testing | 5-10% | Property tours, neighborhood guides, agent brand |

## Campaign Architecture

```
Account — Google
├── Brand
│   └── [Brokerage name], [agent name]
├── Buyer Intent
│   ├── Campaign: Homes for Sale
│   │   ├── Ad Group: homes for sale in [city]
│   │   ├── Ad Group: [neighborhood] real estate
│   │   └── Ad Group: [property type] for sale
│   ├── Campaign: Property Types
│   │   ├── Ad Group: condos for sale [area]
│   │   ├── Ad Group: luxury homes [area]
│   │   └── Ad Group: new construction [area]
│   └── Campaign: Open Houses
│       └── Ad Group: open houses near me / this weekend
├── Seller Intent
│   ├── Ad Group: sell my house [city]
│   ├── Ad Group: home value estimate
│   └── Ad Group: best realtor [city]
├── Retargeting (RLSA)
│   └── Website visitors searching real estate terms
└── YouTube
    └── Property tour videos, neighborhood guides

Account — Meta (Special Ad Category: Housing)
├── Listing Promotion
│   ├── Carousel: featured listings (auto-updated)
│   └── Video: property tour/walkthrough
├── Buyer Lead Gen
│   ├── Lead Form: home search criteria
│   └── Traffic: IDX/MLS search page
├── Seller Lead Gen
│   ├── Lead Form: free home valuation
│   └── Video: market update + "thinking of selling?"
├── Retargeting
│   ├── Website visitors (listing page viewers)
│   └── Video viewers (property tours)
└── Agent Brand
    └── Community content, market updates, testimonials
```

## Creative Strategy

### What Works for Real Estate
- **Property tour videos**: 30-60s walkthrough with agent narration
- **Drone footage**: aerial views of property and neighborhood
- **Carousel ads**: multiple listings or room-by-room tour
- **Market update videos**: agent-to-camera with local market data
- **Just Sold/Just Listed posts**: social proof + urgency
- **Home valuation offer**: "What's your home worth?" (seller leads)
- **Neighborhood guides**: lifestyle content showing the area

### Creative by Audience
| Audience | Creative Type | Message |
|----------|-------------|---------|
| Buyers | Property carousels, video tours | "Your dream home is here" |
| Sellers | Market update, home value | "Your home could be worth more" |
| Investors | ROI data, rental yield | "Cap rate and cash flow analysis" |
| First-time buyers | Educational, step-by-step | "How to buy your first home" |

## Targeting Strategy

### Google
- **Location**: city, county, or ZIP code level
- **Keywords**: "[city] homes for sale", "realtor near me", "sell my house [city]"
- **Negative keywords**: rent, rental, apartment (unless targeting rentals), jobs, salary
- **Ad schedule**: active during showing hours + evening research (6-10 PM peak)

### Meta (Special Ad Category Restrictions Apply)
- **Radius**: 15+ miles around target area (minimum enforced)
- **Special Ad Audiences**: based on purchaser data or website visitors
- **Interests**: limited options — home improvement, real estate related
- **Retargeting**: website visitors, video viewers, lead form openers
- **Cannot use**: age, gender, ZIP code, income, family status targeting

### Listing Feed Integration
- Dynamic ads from MLS/IDX feed (if available)
- Auto-update listing status (active, pending, sold)
- Custom labels: price range, property type, neighborhood

## Budget Guidelines

| Metric | Real Estate Benchmark |
|--------|---------------------|
| Google CPC | $1.55-$2.53 |
| Google CTR | 8.43% |
| Google CVR | 3.28% |
| Meta CPL (buyer lead) | $5-$25 |
| Meta CPL (seller lead) | $15-$50 |
| YouTube CPV | $0.05-$0.15 |
| Cost per showing request | $50-$150 |
| Cost per listing appointment | $100-$300 |
| Min monthly budget | $2,500+ (Google + Meta) |

### Budget by Agent Type
| Agent Type | Monthly Budget | Primary Channel |
|-----------|---------------|-----------------|
| New agent | $1,000-$2,000 | Google Search (high intent) |
| Established agent | $3,000-$5,000 | Google + Meta balanced |
| Team/brokerage | $5,000-$20,000 | Full platform mix |
| Luxury specialist | $5,000-$15,000 | Google + YouTube + Meta |

## Bidding Strategy Selection

| Platform | Monthly Conversions | Recommended Strategy |
|----------|--------------------|--------------------|
| Google | <15 | Maximize Clicks (cap CPC) |
| Google | 15-29 | Maximize Conversions |
| Google | 30+ | Target CPA (recommended for lead gen) |
| Meta | Default | Lowest Cost (Special Ad Category limits optimization) |
| Meta | Efficiency priority | Cost Cap |

## KPI Targets

| Metric | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| CPL (buyer) | <$25 | <$15 | <$10 |
| CPL (seller) | <$50 | <$35 | <$25 |
| Lead → Showing Rate | Track | 10%+ | 15%+ |
| Lead → Closing Rate | Track | 1-2% | 2-3% |
| Cost per Closing | Track | Baseline | Optimize |

## Common Pitfalls

- Not declaring Special Ad Category on Meta (account suspension risk)
- Running same campaigns for buyers and sellers (different intent, different creative)
- Listing ads for properties already under contract (stale data)
- Ignoring seller leads — focusing only on buyer acquisition
- No IDX/MLS integration — sending traffic to generic website
- Geographic targeting too broad (city-wide when you serve specific neighborhoods)
- Not tracking lead → showing → closing pipeline (can't calculate true ROI)
- Video tours without agent on-camera (missed personal branding opportunity)
