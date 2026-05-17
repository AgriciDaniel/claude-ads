---
name: ads-math
description: "PPC financial calculator and modeling tool. CPA, ROAS, CPL calculations, break-even analysis, impression share opportunity sizing, budget forecasting, LTV:CAC ratio analysis, and MER (Marketing Efficiency Ratio) assessment. Requires zero API access. Works with pasted data from exports. Use when user says PPC math, ad calculator, break-even, budget forecast, ROAS calculator, CPA calculator, impression share, LTV CAC, or MER."
user-invokable: false
tested_date: 2026-05-17
tested_with: claude-code v2.x
---

# PPC Financial Calculator & Modeling

<!-- Created: 2026-04-13 | v1.5 -->
<!-- Source: itallstartedwithaidea/google-ads-skills (PPC math concept) -->

## Process

1. Ask the user what calculation they need (or detect from context)
2. Collect required inputs (from pasted data, exports, or verbal description)
3. Perform calculations with clear formulas shown
4. Present results with interpretation and recommendations
5. Flag any concerning metrics or benchmarks

## Calculators

### 1. CPA Calculator

```
CPA = Total Spend / Total Conversions

Inputs needed:
- Total ad spend (period)
- Total conversions (same period)

Output:
- CPA with period context
- CPA trend (if historical data provided)
- Comparison to industry benchmark (from benchmarks.md)
```

### 2. ROAS Calculator

```
ROAS = Revenue from Ads / Ad Spend
ROAS% = (Revenue - Spend) / Spend × 100

Inputs needed:
- Total ad spend
- Total revenue attributed to ads

Output:
- ROAS as ratio (e.g., 3.5x) and percentage (250%)
- Break-even ROAS (based on margins if provided)
- Comparison to platform benchmarks
```

### 3. Break-Even Analysis

```
Break-Even CPA = Average Order Value × Profit Margin
Break-Even ROAS = 1 / Profit Margin

Inputs needed:
- Average order value (AOV) OR average deal value
- Profit margin (gross margin %)
- Current CPA or ROAS

Output:
- Maximum profitable CPA
- Minimum profitable ROAS
- Current headroom (how far above/below break-even)
- Recommendation: scale, maintain, or cut
```

### 4. Impression Share Opportunity

```
Impression Share Lost (Budget) = opportunity from budget increase
Impression Share Lost (Rank) = opportunity from bid/quality improvement

Revenue Opportunity = Current Revenue × (1 / Current IS - 1)

Inputs needed:
- Current impression share %
- IS lost to budget %
- IS lost to rank %
- Current spend and conversions

Output:
- Estimated additional conversions from full IS
- Budget needed for full IS (estimated)
- Priority: budget increase vs quality improvement
```

### 5. Budget Forecasting

```
Projected Spend = Daily Budget × Days in Period
Projected Conversions = Projected Spend / Historical CPA
Projected Revenue = Projected Conversions × AOV

Scaling scenarios:
- Conservative: +20% budget → estimated impact
- Moderate: +50% budget → estimated impact
- Aggressive: +100% budget → estimated impact (with diminishing returns caveat)

Inputs needed:
- Current daily budget
- Historical CPA (last 30 days)
- Forecast period
- AOV (if revenue projection needed)

Output:
- 3 scenarios with spend, conversions, revenue projections
- Diminishing returns warning for aggressive scaling
- 20% scaling rule reminder (never increase >20% at a time)
```

### 6. LTV:CAC Ratio

```
CAC = Total Marketing Spend / New Customers Acquired
LTV = Average Revenue per Customer × Average Customer Lifespan
LTV:CAC Ratio = LTV / CAC

Inputs needed:
- Total marketing spend (all channels)
- New customers acquired
- Average revenue per customer (monthly or annual)
- Average customer lifespan (months)
- Optional: gross margin for unit economics

Output:
- LTV:CAC ratio with interpretation:
  - <1:1 = losing money on every customer
  - 1:1-2:1 = break-even to marginal
  - 3:1 = healthy (SaaS benchmark)
  - 5:1+ = may be under-investing in growth
- Payback period: months to recover CAC
- Recommendation based on ratio
```

### 7. MER (Marketing Efficiency Ratio)

```
MER = Total Revenue / Total Marketing Spend

Inputs needed:
- Total business revenue (period)
- Total marketing spend across ALL channels (same period)

Output:
- MER ratio (e.g., 5.0x)
- Interpretation:
  - E-commerce: 3-5x typical, 8x+ excellent
  - SaaS: 5-10x typical (higher margins)
  - Local service: 3-8x typical
- Comparison to business-type benchmark
- Note: MER captures blended efficiency including organic, brand, and retention
```

### Incrementality & Advanced Measurement

For advanced accounts evaluating cross-channel contribution:
- **Meta Incremental Attribution** (launched April 2025): AI-powered holdout testing measuring real causal impact. Evaluate if budget exceeds $5K/month.
- **Google Meridian** (2025): Open-source Marketing Mix Model for incrementality measurement across channels.
- These tools complement PPC math calculations by measuring what would NOT have happened without the ad spend.

For large accounts detecting small effects (5% MDE), multiply the 10% MDE sample by ~4x.

## Quick Formulas Reference

| Metric | Formula |
|--------|---------|
| CPA | Spend / Conversions |
| ROAS | Revenue / Spend |
| CTR | Clicks / Impressions × 100 |
| CVR | Conversions / Clicks × 100 |
| CPC | Spend / Clicks |
| CPM | (Spend / Impressions) × 1,000 |
| CPL | Spend / Leads |
| Break-Even CPA | AOV × Margin% |
| Break-Even ROAS | 1 / Margin% |
| LTV | ARPU × Avg Lifespan |
| CAC | Total Marketing / New Customers |
| MER | Total Revenue / Total Marketing |
| Impression Share Opp | Revenue × (1/IS - 1) |

## Output Format

```
## PPC Financial Analysis

### [Calculator Name]

**Inputs:**
- [Listed inputs with values]

**Results:**
| Metric | Value | Benchmark | Status |
|--------|-------|-----------|--------|
| [Metric] | [Value] | [Benchmark] | PASS/WARNING/FAIL |

**Interpretation:**
[1-2 sentence analysis]

**Recommendation:**
[Actionable next step]
```

## Data to Request

If the user doesn't provide enough data, ask for:
- Platform and campaign type
- Time period for analysis
- Spend and conversion data
- Revenue data (if ROAS/break-even needed)
- Margin data (if break-even/LTV needed)
- Business type (for benchmark comparison)
