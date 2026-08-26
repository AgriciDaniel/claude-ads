# Bidding Strategy Decisions

**Verified:** 2026-08-25
**Refresh due:** 2026-09-24
**Primary source:** `google-smart-bidding-official` — [Google Ads Help: About Smart Bidding](https://support.google.com/google-ads/answer/7065882)
**Supporting source:** `google-target-roas-official` — [Google Ads Help: About Target ROAS](https://support.google.com/google-ads/answer/6268637)

Bidding is a control system, not a ladder unlocked by a universal conversion
count. Select an eligible strategy from the campaign objective, value signal,
delivery constraint, and measurement quality shown in the current account UI.

Google describes Target CPA, Target ROAS, Maximize conversions, and Maximize
conversion value as Smart Bidding strategies that optimize at auction time.
Google also documents a June 2026 label transition that does not change the
underlying bidding behavior. Availability and labels can change by campaign
type, so verify them at run time.

## Decision inputs

- Primary business objective: visibility, traffic, accepted conversions, value,
  profit proxy, or another explicit outcome.
- Conversion action, counting method, value source, attribution, and lag.
- Historical volume and variance over complete conversion cycles.
- Budget limitation, inventory limitation, seasonality, and auction coverage.
- Owner-approved CPA, ROAS, contribution, cash, and policy boundaries.
- Campaign-type eligibility and any beta, regional, or account restrictions.

If optimization data are incomplete or corrupted, repair measurement before
changing the bidder unless containment is required.

## Strategy logic

| Goal | Candidate strategy | Evidence to verify |
| --- | --- | --- |
| Maximize accepted conversion volume within budget | Conversion-maximizing strategy | Primary conversion is valid; budget and lag are understood |
| Hold an average acquisition-cost goal | Target-cost strategy | Target reflects mature account economics and is eligible |
| Maximize accepted value within budget | Value-maximizing strategy | Values are complete, comparable, and timely |
| Hold an average return goal | Target-return strategy | Value tracking and target economics are sound |
| Visibility or reach | Impression/reach strategy | Outcome is truly visibility; placement and frequency constraints are explicit |
| Exploration or measurement repair | Manual/traffic strategy where available | Time-boxed purpose, stop condition, and downstream risk are documented |

The exact platform label is an observed capability, not a cross-platform
translation. Do not assume that similarly named strategies have identical
auction behavior.

## Setting a target

Derive targets from accepted economics and mature account history. For Google
Target ROAS, official guidance recommends using business goals and historical
ROAS and evaluating over conversion cycles; the same page warns that an overly
high target can restrict traffic. The page also carries an August 2026 bidding
system update, so the active campaign state remains controlling evidence. This
is platform guidance, not a guaranteed outcome.

Do not apply fixed target multipliers, fixed minimum conversion counts, or a
fixed adjustment cadence across accounts. Record the source window, lag maturity,
confidence interval or variance, and expected volume trade-off.

## Change discipline

Before a bid change:

1. Confirm no concurrent budget, conversion, targeting, creative, or policy
   change would confound interpretation.
2. Use the platform's current simulator or experiment feature when suitable.
3. Define the evaluation window in conversion cycles, not arbitrary calendar days.
4. Draft a reversible change with owner-approved boundaries.
5. Verify delivery, spend, accepted outcomes, and remote state after application.

For Google target adjustments, the official guidance says the bidder reacts to
target changes but may need one to two conversion cycles to reach the target.
Treat that duration as Google-specific guidance and verify it against the active
campaign, not as a universal freeze period.

## Diagnostic questions

- Is under-delivery caused by target strictness, budget, eligibility, inventory,
  creative, audience, policy, or tracking?
- Is apparent efficiency an attribution or mix shift rather than incremental value?
- Are values net of cancellations, low-quality leads, and repeat-customer rules?
- Is a portfolio strategy grouping campaigns with genuinely compatible goals?
- Would a bid change violate a learning, experiment, or contractual constraint?

## Unsafe recommendations

- “Use manual bidding below N conversions” without platform/account evidence.
- “Change the target by N% every N days” as a universal rule.
- Broad match, negative keywords, placement expansion, or automation adoption
  prescribed solely from the bid strategy name.
- Vendor-reported lift used as a forecast.
- A bid mutation without exact account/object IDs, approval, verification, and rollback.
