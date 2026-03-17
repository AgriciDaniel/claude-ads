---
name: ads-linkedin
description: "LinkedIn Ads deep analysis for B2B advertising. Evaluates 25 checks across technical setup, audience targeting, creative quality, lead gen forms, and bidding strategy. Includes Thought Leader Ads, ABM, and predictive audiences. Use when user says 'LinkedIn Ads', 'B2B ads', 'sponsored content', 'lead gen forms', 'InMail', or 'LinkedIn campaign'."
---

# LinkedIn Ads Deep Analysis

## Process

1. Collect LinkedIn Ads data (Campaign Manager export, Insight Tag status)
2. Read `ads/references/linkedin-audit.md` for full 25-check audit
3. Read `ads/references/benchmarks.md` for LinkedIn-specific benchmarks
4. Read `ads/references/scoring-system.md` for weighted scoring
5. Evaluate all applicable checks as PASS, WARNING, or FAIL
6. Calculate LinkedIn Ads Health Score (0-100)
7. Generate findings report with action plan

## What to Analyze

### Technical Setup (25% weight)
- Insight Tag installed and firing on all pages (L01)
- Conversions API (CAPI) active — launched 2025 (L02)
- Conversion events configured for full funnel
- Revenue attribution tracking enabled

### Audience Targeting (25% weight)
- Job title targeting uses specific titles, not just functions (L03)
- Company size filtering matches ICP (L04)
- Seniority level appropriate for offer (L05)
- Matched Audiences active: retargeting + contact lists (L06)
- ABM company lists uploaded (up to 300,000 companies) (L07)
- Audience expansion OFF for precision campaigns, ON for scale (L08)
- Predictive audiences tested — replaced Lookalikes Feb 2024 (L09)

### Creative Quality (20% weight)
- Thought Leader Ads active, ≥30% budget allocation for B2B (L10)
- Ad format diversity: ≥2 formats tested (L11)
- Video ads tested (L12)
- Creative refresh every 4-6 weeks (L13)

### Lead Gen & Performance (15% weight)
- Lead Gen Form ≤5 fields (13% CVR benchmark) (L14)
- Lead Gen Form synced to CRM in real-time (L15)
- Campaign objective matches funnel stage (L18)
- A/B testing active: creative or audience (L19)
- Message ad frequency ≤1 per 30-45 days (L20)

### Bidding & Budget (15% weight)
- Bid strategy: CPS for Messages, Max Delivery for Content (L16)
- Daily budget ≥$50 for Sponsored Content (L17)
- CTR ≥0.44% for Sponsored Content (L21)
- CPC within benchmark: $5-7 average, senior $6.40+ (L22)
- Lead-to-opportunity rate tracked, not just CPL (L23)
- Attribution: 30-day click / 7-day view configured (L24)
- Demographics report reviewed monthly (L25)

## Thought Leader Ads (TLA) Assessment

Thought Leader Ads use employee/executive personal posts as sponsored content:
- CPC typically $2.29-$4.14 vs $13.23 for standard Sponsored Content
- CTR typically 2-3x higher than corporate-branded ads
- Best for: B2B thought leadership, brand awareness, engagement

Evaluate:
- Are TLAs being used? (If not, HIGH priority recommendation)
- Are they getting ≥30% of total LinkedIn budget?
- Are the right employees selected (industry credibility, active posters)?
- Is post content authentic and valuable (not salesy)?

## ABM Strategy Assessment

For B2B Enterprise accounts:
- Company list uploaded and segmented by tier (Tier 1, 2, 3)
- Custom content per tier (personalized messaging)
- Account penetration tracking (contacts reached per target account)
- Integration with CRM/ABM platform (Demandbase, 6sense, etc.)

## LinkedIn Context

| Setting | Value |
|---------|-------|
| Minimum audience size | 500 (for ads to run) |
| Lead Gen Form CVR benchmark | 13% |
| TLA CPC range | $2.29-$4.14 |
| Standard SC CPC | $13.23 average |
| Hierarchy rename | Oct 2025 (Campaign Group → Campaign → Ad) |
| Predictive Audiences | Replaced Lookalikes Feb 2024 |

## Key Thresholds

| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| CTR (Sponsored Content) | ≥0.44% | 0.30-0.44% | <0.30% |
| CPC (average) | ≤$7.00 | $7-10 | >$10.00 |
| Lead Gen CVR | ≥10% | 5-10% | <5% |
| Message frequency | ≤1/30 days | 1/15-30 days | >1/15 days |
| TLA budget share | ≥30% | 15-30% | <15% |

## Output

### LinkedIn Ads Health Score

```
LinkedIn Ads Health Score: XX/100 (Grade: X)

Technical Setup:   XX/100  ████████░░  (25%)
Audience:          XX/100  ██████████  (25%)
Creative:          XX/100  ███████░░░  (20%)
Lead Gen:          XX/100  █████░░░░░  (15%)
Budget & Bidding:  XX/100  ████████░░  (15%)
```

### Deliverables
- `LINKEDIN-ADS-REPORT.md` — Full 25-check findings with pass/warning/fail
- TLA adoption roadmap (if not using)
- ABM strategy recommendations (for B2B)
- Lead Gen Form optimization priorities
- Quick Wins sorted by impact
