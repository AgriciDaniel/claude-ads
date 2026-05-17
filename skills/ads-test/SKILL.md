---
name: ads-test
description: "A/B test design and experiment planning for paid advertising. Structured hypothesis framework, statistical significance calculator, test duration estimator, sample size calculator, and platform-specific experiment setup guides (Meta Experiments, Google Experiments, LinkedIn A/B). Use when user says A/B test, split test, experiment design, test hypothesis, statistical significance, sample size, or test duration."
user-invokable: false
tested_date: 2026-05-17
tested_with: claude-code v2.x
---

# A/B Test Design & Experiment Planning

<!-- Created: 2026-04-13 | v1.5 -->
<!-- Source: OpenClaudia/openclaudia-skills (ab-test-setup concept) -->

## Process

1. Understand what the user wants to test (creative, audience, bidding, landing page)
2. Build structured hypothesis using the framework below
3. Calculate required sample size and estimated duration
4. Recommend platform-specific test setup
5. Define success criteria and measurement plan

## Hypothesis Framework

Every test must start with a structured hypothesis:

```
IF we [change/action]
THEN [metric] will [increase/decrease] by [estimated %]
BECAUSE [reasoning based on data or insight]

Example:
IF we replace polished product shots with UGC creator videos
THEN Meta CTR will increase by 25-40%
BECAUSE Andromeda prioritizes diverse creative formats and UGC consistently outperforms polished in 2025-2026 benchmarks
```

### Hypothesis Quality Checklist
- [ ] Single variable being tested (isolate the change)
- [ ] Specific metric defined (not "performance")
- [ ] Estimated effect size stated (needed for sample size calculation)
- [ ] Timeframe defined
- [ ] Success/failure criteria clear before launch

## Statistical Significance Calculator

```
Required Sample Size (per variant):

n = (Z_alpha + Z_beta)^2 × 2 × p × (1-p) / MDE^2

Where:
- Z_alpha = 1.96 (for 95% confidence)
- Z_beta = 0.84 (for 80% power)
- p = baseline conversion rate
- MDE = minimum detectable effect (relative %)

Simplified lookup:
```

| Baseline CVR | 5% MDE | 10% MDE | 20% MDE | 30% MDE |
|-------------|---------|---------|---------|---------|
| 1% | 612,000 | 153,000 | 38,300 | 17,000 |
| 2% | 302,400 | 75,600 | 18,900 | 8,400 |
| 5% | 116,800 | 29,200 | 7,300 | 3,200 |
| 10% | 55,200 | 13,800 | 3,450 | 1,530 |
| 20% | 24,600 | 6,150 | 1,540 | 680 |

*Per variant, 95% confidence, 80% power*

## Test Duration Estimator

```
Duration = Required Sample Size / Daily Traffic per Variant

Minimum duration: 7 days (capture weekly patterns)
Maximum recommended: 28 days (avoid seasonal drift)
Learning phase: Google 7-14 days, Meta 3-7 days, LinkedIn 7-14 days

Inputs needed:
- Daily impressions or clicks
- Number of variants (2 = A/B, 3+ = multivariate)
- Baseline conversion rate
- Minimum detectable effect desired
```

### Duration Quick Estimates

| Daily Clicks | 2% CVR, 20% MDE | 5% CVR, 20% MDE | 10% CVR, 20% MDE |
|-------------|-----------------|-----------------|-----------------|
| 100 | 189 days | 73 days | 35 days |
| 500 | 38 days | 15 days | 7 days |
| 1,000 | 19 days | 7 days | 4 days* |
| 5,000 | 4 days* | 2 days* | 1 day* |

*Minimum 7 days recommended regardless of sample sufficiency

## Platform-Specific Test Setup

### Meta Experiments
- Use Ads Manager > Experiments tab (not manual ad set duplication)
- Automatic audience splitting ensures no overlap
- Supported test types: A/B (creative, audience, placement), Holdout, Brand Survey
- Meta's Incremental Attribution (April 2025) provides AI-powered holdout testing for measuring real causal impact
- Budget: split evenly across variants; minimum $100/day per variant recommended
- Duration: 7-14 days typical; Meta auto-determines winner at 95% confidence

### Google Experiments
- Campaign Experiments (custom experiments) or Ad Variations
- Create experiment from existing campaign > select experiment type
- Traffic split: 50/50 recommended for fastest results
- Supported: bidding strategy, ad copy, landing page, audience
- Metrics: choose primary metric (conversions, CPA, ROAS) before launch
- Duration: 14-30 days recommended; minimum 2 weeks for bidding tests

### LinkedIn A/B Testing
- Built into Campaign Manager for Sponsored Content
- Duplicate ad set with single variable change
- Target: same audience segment with automatic rotation
- Minimum budget: $50/day per variant
- Key metrics: CTR (>0.44% benchmark), CPL, Lead Form CVR (13% benchmark)
- Duration: 14-21 days (LinkedIn's smaller daily volumes require longer tests)

### TikTok Split Testing
- Available in TikTok Ads Manager > Create A/B Test
- Test types: targeting, bidding, creative
- Auto-splits audience to avoid contamination
- Minimum 7 days, recommended 14 days
- Budget: minimum $20/day per ad group
- Creative tests: isolate hook (first 2-3 seconds) as the primary variable
- TikTok's enhanced split testing supports modular test variables (targeting, creative, budget, placement) via Smart+ since 2025

## What to Test (Priority Order)

### High Impact (test first)
1. **Creative concept** (different messaging angles, not just color changes)
2. **Hook/first 3 seconds** (video opening on Meta, TikTok, YouTube)
3. **Offer structure** (pricing, discount type, free trial length)
4. **Landing page** (headline, CTA, form length)
5. **Bidding strategy** (tCPA vs tROAS vs Maximize Conversions)

### Medium Impact
6. **Audience targeting** (interest vs lookalike vs broad)
7. **Ad format** (static vs video vs carousel)
8. **CTA button** (Learn More vs Sign Up vs Shop Now)
9. **Campaign structure** (CBO vs ABO, consolidated vs segmented)

### Low Impact (test last)
10. **Ad scheduling** (time of day, day of week)
11. **Device targeting** (mobile vs desktop)
12. **Minor copy variations** (word substitutions without concept change)

## Common Testing Mistakes to Avoid

- Testing too many variables at once (no clear winner attribution)
- Ending tests too early (before statistical significance)
- Testing during atypical periods (holidays, launches, incidents)
- Comparing unequal time periods
- Not documenting learnings (build institutional knowledge)
- Testing small changes when big changes are needed (optimize vs innovate)
- Ignoring learning phase on automated platforms

## Output Format

```
## A/B Test Plan

### Hypothesis
IF [change]
THEN [metric] will [direction] by [amount]
BECAUSE [reasoning]

### Test Design
| Parameter | Value |
|-----------|-------|
| Platform | [platform] |
| Test Type | [A/B / Multivariate] |
| Variable | [what's being changed] |
| Control | [current state] |
| Variant | [proposed change] |
| Primary Metric | [KPI] |
| Traffic Split | [50/50 / other] |

### Sample Size & Duration
| Metric | Value |
|--------|-------|
| Baseline CVR | [X%] |
| MDE | [X%] |
| Required Sample | [N per variant] |
| Daily Traffic | [N clicks/day] |
| Est. Duration | [X days] |
| Min Duration | 7 days |

### Success Criteria
- Winner declared at 95% confidence
- [Primary metric] improvement of [X%]+ sustained over [Y] days
- No negative impact on [secondary metric]

### Setup Instructions
[Platform-specific step-by-step]
```
