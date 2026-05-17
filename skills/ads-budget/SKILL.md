---
name: ads-budget
description: "Budget allocation and bidding strategy review across all ad platforms. Evaluates spend distribution, bidding strategy appropriateness, scaling readiness, and identifies campaigns to kill or scale. Uses 70/20/10 rule, 3x Kill Rule, and 20% scaling rule. Use when user says budget allocation, bidding strategy, ad spend, ROAS target, media budget, or scaling."
user-invokable: false
tested_date: 2026-05-17
tested_with: claude-code v2.x
---

<!-- Updated: 2026-04-13 | v1.5 -->

# Budget Allocation & Bidding Strategy

## Process

1. Collect budget and performance data across all active platforms
2. Read `ads/references/budget-allocation.md` for allocation framework
3. Read `ads/references/bidding-strategies.md` for strategy decision trees
4. Read `ads/references/benchmarks.md` for CPC/CPA benchmarks
5. Read `ads/references/scoring-system.md` for health score algorithm
6. **Validate**: confirm spend data covers ≥14 days before evaluating kill/scale decisions
7. Evaluate budget allocation, bidding strategy, and scaling readiness
8. **Validate**: verify kill list candidates have sufficient data (≥20 clicks or ≥$100 spend) before recommending pause
9. Generate recommendations with kill list and scale list

## Budget Allocation Framework

### 70/20/10 Rule
- **70%** on proven channels (consistent ROAS/CPA targets met)
- **20%** on scaling channels (showing promise, need more data)
- **10%** on testing channels (new platforms, audiences, creatives)

### Platform Selection Matrix

| Business Type | Primary | Secondary | Testing |
|---------------|---------|-----------|---------|
| SaaS B2B | Google Search, LinkedIn | Meta, YouTube | TikTok, Microsoft |
| E-commerce | Google Shopping, Meta | TikTok, YouTube | Microsoft, LinkedIn |
| Local Service | Google Search, Google LSA | Meta | Microsoft, YouTube |
| B2B Enterprise | LinkedIn, Google Search | Meta | Microsoft, TikTok |
| Info Products | Meta, YouTube | Google Search | TikTok |
| Mobile App | Meta, Google UAC | TikTok | Apple Ads |
| Real Estate | Google Search, Meta | YouTube | Microsoft |
| Healthcare | Google Search | Meta | Microsoft, YouTube |
| Finance | Google Search, Meta | LinkedIn | Microsoft |
| Agency (clients) | Varies by client | N/A | N/A |

### Budget Sufficiency Rules

| Platform | Minimum Daily | Learning Phase Budget |
|----------|--------------|----------------------|
| Google Search | $20/day | Sufficient for 15+ conv/month |
| Google PMax | $50/day | Sufficient for algorithm optimization |
| Meta | $20/day per ad set | ≥5x target CPA per ad set |
| LinkedIn | $50/day Sponsored Content | 15+ conversions/month |
| TikTok | $50/day campaign, $20/day ad group | ≥50x target CPA per ad group |
| Microsoft | No strict minimum | Sufficient for stable delivery |

## Bidding Strategy Evaluation

### Google Ads Bidding Decision Tree

```
Start
├─ <30 conversions/month?
│  └─ Use Maximize Clicks (cap CPC at benchmark)
│     └─ When >30 conv/month → Maximize Conversions
├─ 30-50 conversions/month?
│  └─ Use Maximize Conversions
│     └─ When stable CPA → Target CPA
├─ >50 conversions/month?
│  └─ Use Target CPA
│     └─ When revenue tracking → Target ROAS
└─ Revenue tracking active + >50 conv/month?
   └─ Use Target ROAS
```

### Meta Ads Bidding
- **Lowest Cost (default)**: best for volume, may have CPA variance
- **Cost Cap**: sets CPA ceiling, may reduce volume
- **Bid Cap**: maximum bid per auction, most control
- **ROAS Goal**: target return on ad spend
- **CBO vs ABO**: CBO for proven campaigns, ABO for testing

### LinkedIn Bidding
- **Cost Per Send (CPS)**: for Message Ads
- **Manual CPC**: recommended starting point for cost control
- **Cost Cap**: efficiency at scale with predictable CPA
- **Maximum Delivery**: highest volume, most expensive. Use only for scale with established data
- **Target Cost**: for predictable CPA

### TikTok Bidding
- **Lowest Cost**: maximize conversions within budget (volume)
- **Cost Cap**: set maximum CPA (efficiency)
- **Bid Cap**: maximum bid per impression
- Budget ≥50x CPA per ad group for learning phase exit

### Microsoft Bidding
- Mirror Google strategy but bid 20-35% lower
- Manual CPC for low-volume campaigns (Enhanced CPC deprecated on Google March 2025; verify Microsoft availability before recommending)
- Target CPA / Target ROAS for automated (requires 15+ conversions/30 days)

## v1.5 Bidding Innovations

### Google AI Max for Search
- 14% conversion lift in early testing
- Requires strong negative keyword lists (AI Max casts a wider net)
- DSA likely consolidated into AI Max by Q2 2026
- Best for: accounts with mature conversion tracking and keyword history

### TikTok Smart+ Modular Control (2025)
- Lock targeting, creative, budget, or placement independently (mix of manual and AI)
- ROAS performance: 1.41-1.67x in early adopter data
- Replaces all-or-nothing automation approach
- Best for: advertisers wanting partial AI control without full black-box

### Apple Ads Maximize Conversions
- GA: February 26, 2026. AI-powered auto-bidder for Apple Ads
- Target CPA based on weekly average (not per-conversion)
- Daily budget must be >=5x target CPA for stable performance
- Two-week learning phase required; avoid changes during learning
- Currently supports installs only (not post-install events)

### Meta Advantage+ Bidding
- Automatic optimization across all placements within Advantage+ Sales campaigns
- Budget automatically shifts to highest-performing placements in real time
- Best combined with broad targeting and high creative volume

## Scaling Assessment

### Ready to Scale (Green Light)
- CPA consistently below target for 2+ weeks
- ≥50 conversions per week (learning phase exited)
- CTR stable or improving
- ROAS above target
- No creative fatigue signals

### 20% Rule
Never increase budget by more than 20% at a time:
- Week 1: $100/day → $120/day
- Week 2: $120/day → $144/day
- Week 3: $144/day → $173/day
- Monitor 3-5 days after each increase for performance stability

### Scaling Methods
1. **Vertical**: increase budget on winning campaigns (20% rule)
2. **Horizontal**: duplicate winning campaigns to new audiences
3. **Platform expansion**: add budget on new platforms
4. **Geographic expansion**: test new markets/regions
5. **Format expansion**: test new ad formats on same platform

## Kill List Assessment

### 3x Kill Rule
- Any campaign/ad group with CPA >3x target → **flag for pause**
- Review spend in last 14 days with no conversions → **flag for pause**
- Creative with CTR >50% below platform benchmark → **flag for creative kill**

### Kill Decision Framework
| Scenario | Data Required | Action |
|----------|---------------|--------|
| CPA >3x target | ≥7 days data, ≥20 clicks | Pause immediately |
| No conversions | ≥$100 spend or ≥50 clicks | Pause and diagnose |
| CTR <50% of benchmark | ≥1,000 impressions | Kill creative, test new |
| ROAS <50% of target | ≥14 days data | Reduce budget 50% or pause |

## MER (Marketing Efficiency Ratio)

```
MER = Total Revenue / Total Marketing Spend
```

- Assess blended efficiency across all platforms
- Target MER varies by business: 3x-10x depending on margins
- Use MER to evaluate overall health, not just per-platform ROAS
- Incrementality testing recommended for MER accuracy

## Output

### Budget & Bidding Assessment

```
Budget Allocation Health

Allocation Strategy:  ████████░░  XX/100
Bidding Strategies:   ██████████  XX/100
Scaling Readiness:    ███████░░░  XX/100
Budget Sufficiency:   █████░░░░░  XX/100
```

### Deliverables
- `BUDGET-STRATEGY-REPORT.md`: Full allocation and bidding analysis
- Current vs recommended budget split (pie chart data)
- Bidding strategy recommendations per platform/campaign
- Scale list: campaigns ready for more budget
- Kill list: campaigns/ad groups to pause immediately
- MER analysis and trend
- Quick Wins for immediate budget optimization
