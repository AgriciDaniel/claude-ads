---
name: ads-competitor
description: "Competitor ad intelligence analysis across Google, Meta, LinkedIn, TikTok, Microsoft, and Apple Ads. Analyzes competitor ad copy, creative strategy, keyword targeting, estimated spend via Meta Ad Library / Google Ads Transparency Center / TikTok Top Ads, and identifies competitive gaps and opportunities. Use when user says competitor ads, ad spy, competitive analysis, competitor PPC, ad intelligence, Meta Ad Library, Facebook Ad Library, Google Ads Transparency, competitor creative, or competitor research."
user-invokable: false
tested_date: 2026-05-17
tested_with: claude-code v2.x
---

<!-- Updated: 2026-04-13 | v1.5 -->

# Competitor Ad Intelligence

## Process

1. Identify target competitors (from user input or industry analysis)
2. Read `ads/references/benchmarks.md` for industry CPC/CTR/CVR baselines
3. Research competitor ad presence across platforms
4. Analyze ad copy, creative, and messaging themes
5. Estimate competitor spend and keyword strategy
6. Identify gaps and opportunities
7. Generate competitive intelligence report

## Data Sources

### Free Intelligence Sources
| Source | Platform | What You Can Find |
|--------|----------|------------------|
| Google Ads Transparency Center | Google | Active ads, formats, geo targeting |
| Meta Ad Library | Meta/Instagram | All active ads, creative, copy, spend range |
| LinkedIn Ad Library | LinkedIn | Active ads from company pages |
| TikTok Creative Center | TikTok | Top ads, trending creative, hashtags |
| Microsoft Ads | Microsoft | Limited: use auction insights |
| Apple Ads (App Store) | Apple | Search tab ads, Today tab ads, product page creatives |

### Google Ads Auction Insights
Available from the user's own Google Ads account:
- Impression share vs competitors
- Overlap rate (how often you compete)
- Outranking share (who wins more often)
- Top of page rate and absolute top of page rate
- Available for Search and Shopping campaigns

### Platform-Specific Research

#### Google
- Ads Transparency Center: search by advertiser name or domain
- Search for competitor brand terms to see their ads live
- Auction Insights for impression share comparison

#### Meta
- Ad Library: filter by advertiser, country, platform (FB/IG), date range
- Shows creative (image/video), ad copy, active dates
- Shows platform placement (Facebook, Instagram, Audience Network)

#### LinkedIn
- Ad Library: search by company name
- Shows Sponsored Content, Message Ads
- Limited data compared to Meta Ad Library

#### TikTok
- Creative Center 2.0: top-performing ads by industry, country, objective with enhanced filtering
- Hashtag analytics: trending sounds and hashtags
- TikTok Shop: review competitor storefronts, catalogs, reviews, and live shopping
- No per-advertiser library; use Creative Center for industry trends

#### Apple Ads
- App Store search: search competitor brand terms to see their Search tab ads
- Today tab ads: check competitor presence on App Store homepage
- Custom Product Pages: analyze competitor CPP variants via App Store listings

## 2025-2026 Platform Updates

### Meta
- **Andromeda creative clustering** (launched October 2025): ads with >60% similarity are suppressed. Competitor creative analysis must assess genuine conceptual diversity, not just volume
- **Advantage+ Sales** (renamed from ASC): unified shopping campaign type. Check if competitors are running Advantage+ Sales vs manual campaigns

### Google
- **Demand Gen replaced VAC** (April 2026): Video Action Campaigns fully deprecated. Analyze competitor Demand Gen adoption (multi-format video+image)
- **AI Max for Search**: AI-powered campaign type with 14% conversion lift. Check competitor adoption via Ads Transparency Center
- **Expanded Ads Transparency Center**: richer data on competitor ad history, formats, and targeting regions

### TikTok
- **Creative Center 2.0**: enhanced industry benchmarking, top ads filtering by objective and format
- **Symphony AI variations** (2025): AI-generated creative at scale. Assess whether competitors use Symphony-generated vs original content
- **TikTok Shop competitor analysis**: review competitor Shop tabs, product catalogs, reviews, and live shopping activity

### LinkedIn
- **Thought Leader Ads expansion** (March 2025): now supports non-employee creators and influencers. Check if competitors sponsor external thought leaders
- **CRM integration** (June 2025): enhanced audience matching. Competitors with CRM integration show more precise targeting patterns

### Microsoft
- **Copilot ads in conversations**: new placement in Microsoft Copilot chat. Check if competitors appear in conversational ad placements
- **CTV inventory**: ads on Netflix, Max, Hulu, and Roku via Microsoft Advertising. Assess competitor presence on connected TV

### Apple Ads
- **Rebranded to "Apple Ads"** (April 2025): formerly Apple Search Ads. All references updated
- **Custom Product Page (CPP) competitive analysis**: competitors can run different product page variants per ad group. Analyze CPP strategies
- **Maximize Conversions bidding**: AI auto-bidder (GA February 2026). Check if competitors have adopted automated bidding

> **MCP Integration**: For live API access to competitor data sources, see `ads/references/mcp-integration.md`.

## Competitive Analysis Framework

### 1. Ad Copy Analysis
For each competitor, document:
- **Headlines**: primary messages and value propositions
- **CTAs**: what action they're driving (free trial, demo, buy now, learn more)
- **Offers**: pricing, discounts, free shipping, trials
- **Tone**: professional, casual, urgent, educational, emotional
- **USPs**: unique selling propositions they emphasize
- **Pain points**: customer problems they address

### 2. Creative Strategy Analysis
- **Formats used**: image, video, carousel, collection, document
- **Visual style**: photography, illustration, UGC, stock, branded
- **Video approach**: studio quality vs UGC vs animated
- **Creative volume**: how many active ads (indicator of testing velocity)
- **Refresh frequency**: how often new creatives appear

### 3. Messaging Themes
Categorize competitor messaging into themes:
| Theme | Competitor A | Competitor B | Your Brand |
|-------|-------------|-------------|------------|
| Price/Value | ✅ Primary | ⚠️ Secondary | ? |
| Quality/Premium | ❌ | ✅ Primary | ? |
| Speed/Convenience | ⚠️ Secondary | ❌ | ? |
| Trust/Authority | ✅ Primary | ✅ Primary | ? |
| Innovation | ❌ | ⚠️ Secondary | ? |

### 4. Keyword Intelligence (Google/Microsoft/Apple Ads)
- Brand keyword bidding: are competitors bidding on your brand?
- Keyword overlap: which non-brand terms do you both target?
- Keyword gaps: terms competitors rank for that you don't target
- Match type strategy: estimated match types from ad triggers

### 5. Spend Estimation
- Meta Ad Library shows spend ranges for political/social ads
- Google Auction Insights + impression share = directional spend estimate
- Third-party tools (SEMrush, SpyFu) for more precise estimates
- Manual estimation formula:
  ```
  Estimated Monthly Spend = Impressions × CPM / 1000
  or
  Estimated Monthly Spend = Clicks × Estimated CPC
  ```

## Gap & Opportunity Identification

### Platform Gaps
- Which platforms are competitors NOT on? (opportunity to own)
- Which platforms are they underspending on? (opportunity to outspend)

### Messaging Gaps
- What customer pain points are NO competitors addressing?
- What value propositions are underrepresented in the market?
- What content formats are competitors not using?

### Audience Gaps
- What demographics/segments are competitors not targeting?
- What geographic markets are underserved?
- What funnel stages are competitors neglecting?

### Creative Gaps
- What ad formats are competitors not using? (video, UGC, Spark Ads)
- What creative styles are missing from the competitive landscape?
- What platform-specific features are competitors not leveraging?

## Competitive Response Strategy

### When Competitors Bid on Your Brand
- Always run brand campaigns to defend (low CPC, high CTR)
- Dynamic keyword insertion to show your brand prominently
- Sitelinks to key pages (pricing, features, reviews)
- Ad copy that emphasizes unique differentiators
- Consider bidding on competitor brand terms (know the rules)

### When You're Outspent
- Focus on efficiency over volume (better targeting, creative, landing pages)
- Target long-tail keywords competitors ignore
- Use Exact match for precision (less waste)
- Double down on retargeting (lower CPA than prospecting)
- Compete on creative quality, not budget

## Output

### Deliverables
- `COMPETITOR-INTELLIGENCE-REPORT.md`: Full competitive analysis
  - Per-competitor ad presence summary
  - Ad copy and messaging analysis
  - Creative strategy comparison
  - Estimated spend levels
  - Keyword overlap and gaps
- `COMPETITIVE-GAPS.md`: Opportunities identified from competitor analysis
  - Platform gaps
  - Messaging opportunities
  - Audience segments to target
  - Creative format opportunities
- Strategic recommendations for competitive positioning
- Priority actions to gain competitive advantage
