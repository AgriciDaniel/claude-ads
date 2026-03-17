---
name: ads-competitor
description: "Competitor ad intelligence analysis across Google, Meta, LinkedIn, TikTok, and Microsoft. Analyzes competitor ad copy, creative strategy, keyword targeting, estimated spend, and identifies competitive gaps and opportunities. Use when user says 'competitor ads', 'ad spy', 'competitive analysis', 'competitor PPC', or 'ad intelligence'."
---

# Competitor Ad Intelligence

## Process

1. Identify target competitors (from user input or industry analysis)
2. Read `ads/references/benchmarks.md` for industry CPC/CTR/CVR baselines
3. Research competitor ad presence across platforms using free intelligence sources
4. **Validate**: confirm ≥2 competitors identified with active ads before proceeding
5. Analyze ad copy, creative, and messaging themes
6. Estimate competitor spend and keyword strategy
7. Identify gaps and opportunities
8. **Validate**: verify gap analysis references actual competitor data, not assumptions
9. Generate competitive intelligence report

## Data Sources

### Free Intelligence Sources
| Source | Platform | What You Can Find |
|--------|----------|------------------|
| Google Ads Transparency Center | Google | Active ads, formats, geo targeting |
| Meta Ad Library | Meta/Instagram | All active ads, creative, copy, spend range |
| LinkedIn Ad Library | LinkedIn | Active ads from company pages |
| TikTok Creative Center | TikTok | Top ads, trending creative, hashtags |
| Microsoft Ads | Microsoft | Limited — use auction insights |

### Google Ads Auction Insights
Available from the user's own Google Ads account:
- Impression share, overlap rate, outranking share
- Top of page rate and absolute top of page rate
- Available for Search and Shopping campaigns

## Competitive Analysis Framework

### 1. Ad Copy Analysis
For each competitor, document:
- **Headlines**: primary messages and value propositions
- **CTAs**: what action they're driving
- **Offers**: pricing, discounts, trials
- **Tone**: professional, casual, urgent, educational, emotional
- **USPs**: unique selling propositions emphasized
- **Pain points**: customer problems addressed

### 2. Creative Strategy Analysis
- **Formats used**: image, video, carousel, collection, document
- **Visual style**: photography, illustration, UGC, stock, branded
- **Creative volume**: number of active ads (testing velocity indicator)
- **Refresh frequency**: how often new creatives appear

### 3. Messaging Theme Matrix
| Theme | Competitor A | Competitor B | Your Brand |
|-------|-------------|-------------|------------|
| Price/Value | ✅ Primary | ⚠️ Secondary | ? |
| Quality/Premium | ❌ | ✅ Primary | ? |
| Speed/Convenience | ⚠️ Secondary | ❌ | ? |
| Trust/Authority | ✅ Primary | ✅ Primary | ? |
| Innovation | ❌ | ⚠️ Secondary | ? |

### 4. Keyword Intelligence (Google/Microsoft)
- Brand keyword bidding: are competitors bidding on your brand?
- Keyword overlap and gaps vs competitors
- Match type strategy estimated from ad triggers

### 5. Spend Estimation
```
Estimated Monthly Spend = Impressions × CPM / 1000
— or —
Estimated Monthly Spend = Clicks × Estimated CPC
```
Cross-reference with: Meta Ad Library spend ranges, Google Auction Insights impression share, third-party tools (SEMrush, SpyFu).

## Gap & Opportunity Identification

### Platform Gaps
- Which platforms are competitors absent from or underspending on?

### Messaging Gaps
- Unaddressed customer pain points
- Underrepresented value propositions
- Unused content formats

### Audience Gaps
- Untargeted demographics/segments
- Underserved geographic markets
- Neglected funnel stages

### Creative Gaps
- Unused ad formats (video, UGC, Spark Ads)
- Missing creative styles
- Unleveraged platform-specific features

## Competitive Response Playbook

### When Competitors Bid on Your Brand
- Run brand campaigns (low CPC, high CTR defense)
- Dynamic keyword insertion + sitelinks to key pages
- Ad copy emphasizing unique differentiators

### When You're Outspent
- Target long-tail keywords competitors ignore
- Exact match for precision, retargeting for efficiency
- Compete on creative quality and landing page experience

## Output

### Deliverables
- `COMPETITOR-INTELLIGENCE-REPORT.md` — Full competitive analysis
  - Per-competitor ad presence, copy analysis, creative comparison, spend estimates, keyword gaps
- `COMPETITIVE-GAPS.md` — Opportunities identified
  - Platform, messaging, audience, and creative gaps
- Strategic recommendations for competitive positioning
- Priority actions ranked by competitive advantage potential
