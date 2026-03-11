---
name: ab-test-setup
description: >
  Designs structured A/B test plans for Meta ad campaigns: hypothesis,
  variants, sample size calculation, success metrics, and test duration.
  Follows Meta's A/B Testing tool methodology. Triggers on: "A/B test",
  "split test", "test hypothesis", "creative test", "audience test",
  "ad test", "Meta experiment".
argument-hint: "<campaign-name> | <what to test>"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
---

# A/B Test Setup — Meta Ads Experiment Design

Designs structured split tests for Meta campaigns following the scientific
method: one variable, clear hypothesis, sufficient sample size, defined
success metrics, and a fixed test duration.

## Process

1. Read campaign brief from `campaigns/{name}/brief.md` if available
2. Identify what to test (creative angle, audience, placement, bid strategy)
3. Generate test plan with hypothesis, variants, and success criteria
4. Calculate minimum sample size and test duration
5. Write plan to `campaigns/{name}/ab-test.md`
6. Log in `campaigns/{name}/log.md`

## What to Test (Priority Order)

Test one variable at a time. Start with the highest-impact variables:

| Priority | Variable | What It Reveals |
|----------|----------|----------------|
| 1 | Creative angle (pain vs. outcome vs. proof) | Which message resonates |
| 2 | Ad format (image vs. video vs. carousel) | Which format converts |
| 3 | Audience (interest vs. LAL vs. Advantage+) | Which targeting works |
| 4 | Headline variant | Which hook pulls clicks |
| 5 | CTA button | Which action converts better |
| 6 | Landing page (if multiple exist) | Which page converts |
| 7 | Bid strategy (Lowest Cost vs. Cost Cap) | Efficiency vs. volume |

## Test Plan Structure

For each test, produce:

### Test Information
```
Test Name: {descriptive name}
Campaign: {campaign name}
Variable Tested: {single variable}
Test Type: Meta A/B Testing tool (preferred) or manual split
Start Date: {date}
End Date: {date} (minimum 7 days, recommended 14 days)
```

### Hypothesis
```
We believe that {variant B} will outperform {variant A} for {metric}
because {reason based on audience insight or previous data}.
```

### Variants
```
Control (A): {description of existing / baseline}
Variant (B): {description of what changes}
(Optional C): {third variant if budget allows}
```

**Rule:** Change only one element between A and B. Everything else identical.

### Budget Allocation
- Minimum budget per variant: $50/day (below this, results are unreliable)
- Split: 50/50 between variants (Meta A/B Testing tool handles this)
- Total test budget: ${daily per variant} × {variants} × {days}

### Sample Size Requirement

Use this formula to estimate required conversions per variant:
- Minimum: 50 conversion events per variant to reach significance
- Target: 100+ for reliable results
- At current CPL/CPA, estimate days to reach significance:
  `days = (100 × CPA) / (daily_budget_per_variant)`

### Success Metrics

Primary metric (one only — the metric that decides the winner):
- Lead Gen: Cost per Lead (CPL)
- E-commerce: Cost per Purchase (CPA) or ROAS
- Traffic: Cost per Landing Page View (CPLPV)
- Awareness: Cost per 1000 Impressions (CPM)

Secondary metrics (diagnostic only, don't use to pick winner):
- CTR (Link Click-Through Rate)
- CPC (Cost per Click)
- Landing page conversion rate

### Statistical Significance Target
- Minimum: 90% confidence
- Preferred: 95% confidence
- Use Meta's built-in significance reporting in A/B Testing tool

### Decision Criteria
```
If {primary metric} for Variant B is {X%} lower than Variant A
AND confidence level ≥ 90%
→ Declare B the winner and scale

If no statistically significant difference after {N} days
→ Extend by 7 days OR declare a draw and test a different variable
```

## Test Isolation Rules

1. Run only one test per campaign at a time
2. Do not adjust budgets during a test (invalidates results)
3. Do not add creatives to an active test
4. Do not change audience during a test
5. Run tests for full weeks (avoid weekend vs. weekday bias)

## Output

Write to `campaigns/{campaign-name}/ab-test.md`:

```markdown
# A/B Test Plan — {Campaign Name}

## Test: {Test Name}
**Variable:** {variable}
**Duration:** {start} → {end} ({N} days)
**Budget:** ${total test budget}

## Hypothesis
{hypothesis statement}

## Variants
**Control (A):** {description}
**Variant (B):** {description}

## Success Metrics
**Primary:** {metric} — winner if {condition}
**Secondary:** CTR, CPC (diagnostic only)

## Significance Target
90% confidence minimum | 95% preferred
Minimum 50 conversions per variant

## Decision Date
{date} — review results and declare winner or extend
```

After writing, confirm: "A/B test plan saved to `campaigns/{name}/ab-test.md`. Schedule a review for {decision date}."
