---
name: ads-apple
description: "Apple Search Ads (ASA) deep analysis for mobile app advertisers. Evaluates campaign structure, bid health, Creative Sets, MMP attribution, budget pacing, TAP coverage (Today/Search/Product Pages), and goal CPA benchmarks by country. Use when user says 'Apple Search Ads', 'ASA', 'App Store ads', 'Apple ads', 'Search Ads', or is advertising a mobile app on iOS."
---

# Apple Search Ads (ASA) Deep Analysis

## Process

1. Collect ASA account data (exports from Apple Search Ads dashboard or pasted metrics)
2. **Validate**: confirm data includes campaign-level spend, installs, and CPT for ≥30 days
3. Identify active placement types (Search Results, Search Tab, Today Tab, Product Pages)
4. Evaluate all applicable checks as PASS, WARNING, or FAIL
5. Calculate ASA Health Score (0-100)
6. Generate findings report with action plan

## What to Analyze

### Campaign Structure (25% weight)

**BOFU — Bottom of Funnel (Search Results, Exact Match brand)**
- Brand keyword campaign present (own app name + misspellings)
- Competitor campaign present (competitor app names as keywords)
- Category campaigns targeting high-intent generic terms (e.g. "workout app", "budget tracker")

**MOFU — Middle of Funnel (Search Match / broad discovery)**
- Search Match campaigns active in at least one ad group for discovery
- Search Match ad groups isolated from Exact Match (separate ad groups — never mix)
- Search Terms Report reviewed to mine converting queries for Exact Match promotion

**Campaign Architecture Rules:**
- Brand / Category / Competitor should be separate campaigns (different CPT bids, budgets)
- Search Match ad groups isolated from manual keyword ad groups — NEVER mix in same ad group
- Goal: let Search Match discover, then promote winners to Exact Match campaigns

### Bid Health (20% weight)

**CPT (Cost Per Tap) vs Install Rate by Match Type:**
- CPT vs category benchmarks (see Benchmarks section below)
- TTR (Tap-Through Rate): benchmark >2.5% for Search Results, >1.5% for Search Tab
- Conversion Rate (tap → install): benchmark 50-65% for brand terms, 20-40% for category
- CPT/CPG (Cost Per Goal): compare against target CPI/CPA from MMP

**Bid Strategy:**
- Manual CPT bidding appropriate? (Or use Apple's CPA Goals auto-bidding for scaled accounts)
- CPA Goals available at campaign level — evaluate if conversion volume supports it (>100 installs/month per campaign)
- Are bids differentiated by match type? (Brand Exact > Category Exact > Search Match)
- Keyword-level CPT bids set, not just ad group default?

**Keyword Health:**
- Irrelevant Search Terms (from Search Match) identified and excluded via negative keywords
- Low-performing keywords paused or bid reduced (TTR <1% + high CPT)
- High-volume generic terms checked for intent quality (avoid "free apps" type queries)

### Creative Sets (15% weight)

**Custom Product Pages (CPP):**
- Custom Product Pages created in App Store Connect? (ASA Creative Sets pull from CPPs)
- At least 3 CPP variants tested per campaign type (different value props per audience)
- Creative Sets assigned to high-spend ad groups
- Screenshot/preview variations aligned with keyword intent (e.g. fitness keywords → fitness screenshots)

**Default (Store Listing) Creative:**
- App icon, subtitle, and first 3 screenshots optimized — these show in ads by default
- Short description (170 chars) compelling and keyword-rich
- Preview video present (strongly recommended for TTR improvement)

**Creative Testing:**
- Are different Creative Sets being A/B tested within ad groups?
- CPP performance compared: which Creative Set has highest TTR and lowest CPI?

### Attribution & MMP Health (15% weight)

**MMP Integration (Critical):**
- MMP (AppsFlyer / Adjust / Branch / Singular) integrated with ASA via SKAdNetwork + ATT
- ASA is properly connected as a partner in MMP dashboard
- In-app events being sent back to ASA (enables CPA Goals and ROAS optimization)
- Post-install event quality: are purchase, subscription_start, or other revenue events tracked?

**SKAdNetwork & ATT:**
- SKAdNetwork conversion values configured in MMP (maps user actions to conversion windows)
- ATT opt-in rate monitored (low ATT rate = less MMP data, more reliance on SKAN)
- Privacy threshold considerations: are campaigns getting SKAN postbacks or null reports?

**Attribution Windows:**
- Default ASA attribution: 30-day click, 1-day view — appropriate for app install goals?
- For re-engagement or subscription goals: evaluate longer lookback windows

### Budget Pacing (10% weight)

- Daily cap set at campaign level (budget pacing in ASA is daily, not monthly)
- Actual daily spend vs daily cap ratio: flag if consistently hitting cap (could be missing volume)
- Conversely: flag if spend is <50% of daily cap (creative or bid issue, not budget)
- Budget split across placement types aligned with performance (don't over-invest in underperforming placements)
- Lifetime budget campaigns (if used): check end dates and pacing curves

### TAP Coverage — Placement Types (10% weight)

ASA offers 4 placement types — evaluate coverage and performance:

| Placement | Where | Best for | Benchmark CPT |
|-----------|-------|----------|----------------|
| Search Results | Below search results | High intent, bottom funnel | $0.50-$3.00 |
| Search Tab | Top of Search tab | Discovery, mid funnel | $0.30-$1.50 |
| Today Tab | App Store home | Brand awareness | $1.00-$5.00 |
| Product Pages | Competitor/related app pages | Competitor conquesting | $0.50-$2.00 |

**Evaluation:**
- Search Results: must be active (highest intent placement)
- Search Tab: active for scale? Evaluate CPT and TTR vs Search Results
- Today Tab: only if budget >$3k/month and brand awareness is a goal (high CPT, low intent)
- Product Pages: competitive opportunity — are competitor CPPs being targeted?

### Goal CPA / KPI Assessment (5% weight)

**Benchmarks by Category (2025-2026 ASA averages):**
| Category | Avg CPT | Avg TTR | Avg Install CVR | Target CPI |
|----------|---------|---------|-----------------|------------|
| Games | $0.50-$1.00 | 3-5% | 55-70% | $1.00-$3.00 |
| Health & Fitness | $1.50-$3.00 | 2-4% | 45-60% | $3.00-$8.00 |
| Productivity | $1.00-$2.50 | 2-3.5% | 50-65% | $2.00-$5.00 |
| Finance | $2.00-$5.00 | 1.5-3% | 40-55% | $5.00-$15.00 |
| Education | $1.00-$2.00 | 2-4% | 50-65% | $2.00-$6.00 |
| Shopping | $0.80-$2.00 | 2.5-4% | 45-60% | $2.00-$5.00 |
| Lifestyle | $0.80-$1.80 | 2-3.5% | 45-60% | $2.00-$5.00 |

**Country-level benchmarks:**
- Tier 1 (US, UK, AU, CA, JP): CPT 2-3× above global average; highest LTV
- Tier 2 (DE, FR, KR, SG, HK): CPT 1-1.5× above global average
- Tier 3 (BR, IN, MX): CPT 30-60% below Tier 1; high volume, lower LTV

**Checks:**
- Actual CPI vs target CPI (from MMP) — flag if >2x target
- CPI trend over 30 days (improving or worsening?)
- Revenue events: is ROAS positive within MMP attribution window?

## Output Format

```
## Apple Search Ads Audit

**ASA Health Score: [X]/100**

### Critical Issues ([count])
- [Issue with specific impact and fix]

### High Priority ([count])
- [Issue]

### Campaign Structure
PASS/WARNING/FAIL for each check category

### Benchmark Comparison
[Metric] | Your Account | ASA Benchmark | Status

### Quick Wins (do this week)
1. [Most impactful fix with expected outcome]
2.
3.

### Recommended Next Steps
[Prioritized action plan]
```

## Scoring Weights

| Category | Weight |
|----------|--------|
| Campaign Structure | 25% |
| Bid Health | 20% |
| Creative Sets | 15% |
| Attribution & MMP | 15% |
| Budget Pacing | 10% |
| TAP Coverage | 10% |
| Goal KPI Assessment | 5% |

## Data to Request from User

If not provided, ask for:
- Campaign list with spend, installs, CPT, TTR, CVR (last 30 days)
- Active placement types
- MMP being used (AppsFlyer, Adjust, Branch, Singular, or none)
- Target CPI / CPA and app category
- Countries/regions active
- Whether Custom Product Pages are set up in App Store Connect
