# Meta Ads Audit Checklist

<!-- Updated: 2026-02-11 -->
<!-- Sources: Google Research PDF 1 (M01-M40), Claude Research (42-item extended), Gemini Research -->
<!-- Total Checks: 46 | Categories: 4 | See scoring-system.md for weights and algorithm -->

## Quick Reference

| Category | Weight | Check Count |
|----------|--------|-------------|
| Pixel / CAPI Health | 30% | M01-M10 (10 checks) |
| Creative (Diversity & Fatigue) | 30% | M25-M32 (8 checks) + M-CR1 through M-CR4 (4 extended) |
| Account Structure | 20% | M11-M18 + M33-M40 (16 checks) + M-ST1, M-ST2 (2 extended) |
| Audience & Targeting | 20% | M19-M24 (6 checks) |

---

## Pixel / CAPI Health (30% weight)

| ID | Check | Severity | Pass | Warning | Fail |
|----|-------|----------|------|---------|------|
| M01 | Meta Pixel installed | Critical | Pixel firing on all pages | Firing on most pages (>90%) | Pixel not firing |
| M02 | Conversions API (CAPI) active | Critical | Server-side events sending alongside pixel | CAPI planned but not deployed | No CAPI (30-40% data loss post-iOS 14.5) |
| M03 | Event deduplication | Critical | event_id matching between pixel and CAPI events; ≥90% dedup rate | event_id present but <90% dedup rate | Missing event_id (double-counting) |
| M04 | Event Match Quality (EMQ) | Critical | EMQ ≥8.0 for Purchase event | EMQ 6.0-7.9 | EMQ <6.0 |
| M05 | Domain verification | High | Business domain verified in Business Manager | — | Domain not verified |
| M06 | Aggregated Event Measurement (AEM) | High | Top 8 events configured and prioritized correctly | Events configured but not prioritized | AEM not configured |
| M07 | Standard events vs custom | High | Using standard events (Purchase, AddToCart, Lead, etc.) | Mix of standard and custom | Custom events replacing standard events |
| M08 | CAPI Gateway | Medium | CAPI Gateway deployed for simplified server-side | Direct CAPI integration active | — |
| M09 | iOS attribution window | High | 7-day click / 1-day view configured | 1-day click only | Attribution not configured |
| M10 | Data freshness | Medium | Events firing in real-time (no >1hr lag in Events Manager) | <4hr lag | >4hr lag or intermittent firing |

---

## Creative — Diversity & Fatigue (30% weight)

| ID | Check | Severity | Pass | Warning | Fail |
|----|-------|----------|------|---------|------|
| M25 | Creative format diversity | Critical | ≥3 formats active (static image, video, carousel) | 2 formats | Only 1 format used |
| M26 | Creative volume per ad set | High | ≥5 creatives per ad set (ideal: 5-8 for Andromeda) | 3-4 creatives | <3 creatives per ad set |
| M27 | Video aspect ratios | High | 9:16 vertical video present for Reels/Stories | Only 1:1 or 4:5 video | No video assets |
| M28 | Creative fatigue detection | Critical | No creatives with CTR drop >20% over 14 days while active | CTR drop 10-20% | CTR drop >20% + frequency >3 (fatigue confirmed) |
| M29 | Hook rate (video) | High | Video ads: <50% skip rate in first 3 seconds | 50-70% skip rate | >70% skip rate in first 3s |
| M30 | Social proof utilization | Medium | Top organic posts boosted as partnership/Spark ads | Some organic boosting | No organic content leveraged |
| M31 | UGC / social-native content | High | ≥30% of creative assets are UGC or social-native | 10-30% UGC content | <10% UGC (all polished/corporate) |
| M32 | Advantage+ Creative | Medium | Advantage+ enhancements enabled (test vs control) | — | Not tested |
| M-CR1 | Creative freshness | High | New creative tested within last 30 days | New creative 30-60 days ago | No new creative in >60 days |
| M-CR2 | Frequency — Prospecting (ad set) | High | Ad set frequency <3.0 in last 7 days | Frequency 3.0-5.0 | Frequency >5.0 (audience exhausted) |
| M-CR3 | Frequency — Retargeting | Medium | Ad set frequency <8.0 in last 7 days | Frequency 8.0-12.0 | Frequency >12.0 |
| M-CR4 | CTR benchmark | High | CTR ≥1.0% | CTR 0.5-1.0% | CTR <0.5% |

---

## Account Structure (20% weight)

| ID | Check | Severity | Pass | Warning | Fail |
|----|-------|----------|------|---------|------|
| M11 | Campaign count | High | ≤5 active campaigns per country/funnel stage | 6-8 campaigns per segment | >8 campaigns (over-fragmented) |
| M12 | CBO vs ABO appropriateness | High | CBO for >$500/day; ABO for testing <$100/day | Mismatched but functional | CBO on <$100/day OR ABO on >$500/day |
| M13 | Learning phase status | Critical | <30% of ad sets in "Learning Limited" | 30-50% Learning Limited | >50% ad sets "Learning Limited" |
| M14 | Learning phase resets | High | No unnecessary edits during learning phase | 1-2 minor resets | Frequent resets from edits during learning |
| M15 | Advantage+ Sales campaign | Medium | ASC active for e-commerce with catalog | ASC tested but paused | Not tested despite eligible catalog |
| M16 | Ad set consolidation | High | No overlapping ad sets targeting same audience | Minor overlap (<20%) | Significant audience overlap (>30%) |
| M17 | Budget distribution | High | All ad sets getting ≥$10/day | Some ad sets $5-$10/day | Ad sets getting <$5/day |
| M18 | Campaign objective alignment | High | Objective matches actual business goal | — | Objective mismatched (e.g., Traffic for Sales) |
| M33 | Advantage+ Placements | Medium | Advantage+ Placements enabled (unless exclusion needed) | Manual placements (justified) | Manual placements limiting delivery without reason |
| M34 | Placement performance review | Medium | Breakdown reviewed monthly; underperformers excluded | Reviewed quarterly | Never reviewed |
| M35 | Attribution setting | High | 7-day click / 1-day view attribution | 1-day click only | Attribution not configured |
| M36 | Bid strategy appropriateness | High | Cost Cap for margin protection; Lowest Cost for volume | — | Bid Cap set below historical CPA |
| M37 | Frequency cap monitoring (campaign) | High | Campaign-level prospecting frequency <4.0 (7-day) | Frequency 4.0-6.0 | Frequency >6.0 |
| M38 | Breakdown reporting | Medium | Age, gender, placement, platform reviewed monthly | Reviewed quarterly | Never reviewed |
| M39 | UTM parameters | Medium | UTM parameters on all ad URLs for GA4 attribution | UTMs on some ads | No UTM parameters |
| M40 | A/B testing active | Medium | At least 1 active A/B test (Experiments) | Test planned | No testing infrastructure |
| M-ST1 | Budget adequacy | High | Daily budget ≥5× target CPA per ad set | Budget 2-5× CPA | Budget <2× target CPA |
| M-ST2 | Budget utilization | Medium | >80% of daily budget being utilized | 60-80% utilization | <60% utilization |

---

## Audience & Targeting (20% weight)

| ID | Check | Severity | Pass | Warning | Fail |
|----|-------|----------|------|---------|------|
| M19 | Audience overlap | High | <20% overlap between active ad sets | 20-40% overlap | >40% overlap between ad sets |
| M20 | Custom Audience freshness | High | Website Custom Audiences refreshed within 180 days | 180-365 days old | >365 days old or not created |
| M21 | Lookalike source quality | Medium | Lookalike source ≥1,000 users from high-value events | 500-1,000 users | <500 users or low-value source |
| M22 | Advantage+ Audience testing | Medium | Advantage+ Audience tested vs manual | — | Not tested |
| M23 | Exclusion audiences | High | Purchasers/converters excluded from prospecting | Partial exclusions | No purchaser exclusions from prospecting |
| M24 | First-party data utilization | High | Customer list uploaded for Custom Audience + Lookalike | List uploaded but not refreshed | No first-party data uploaded |

---

## Context Notes

- **Detailed targeting exclusions removal (2025-2026)**: Meta phased out detailed targeting exclusions starting March 2025, with full removal by January 2026. Advertisers must now use Custom Audience exclusions or Advantage+ Audience instead.
- **Flexible Ads (2024)**: Format launched mid-2024 that automatically optimizes creative elements (headline, image, video) per placement. Evaluate adoption alongside Advantage+ Creative enhancements.
- **Financial Products Special Ad Category (Jan 2025)**: Financial products (loans, insurance, credit cards, investment services) are now enforced as a Special Ad Category with the same targeting restrictions as Housing/Employment/Credit.

---

## Quick Wins (Meta)

| Check | Fix | Time |
|-------|-----|------|
| M02 — CAPI setup | Deploy via CAPI Gateway (simplified) or direct integration | 15 min (Gateway) |
| M05 — Domain verification | Verify domain in Business Manager | 5 min |
| M09 — Attribution window | Set to 7-day click / 1-day view in ad set settings | 2 min |
| M23 — Exclusion audiences | Create Custom Audience of purchasers, exclude from prospecting | 10 min |
| M25 — Format diversity | Add video or carousel to single-image-only ad sets | 15 min |
| M39 — UTM parameters | Add UTM template at campaign level | 5 min |
| M35 — Attribution setting | Switch from 1-day click to 7-day click / 1-day view | 2 min |

---

## Special Ad Categories Compliance

If running ads in restricted categories, these ADDITIONAL checks apply:

| Category | Requirement | Enforcement |
|----------|-------------|-------------|
| Housing | No ZIP code targeting, age 18-65+ only, no Lookalike | Campaign disapproval |
| Employment | Same as Housing | Campaign disapproval |
| Credit | Same as Housing | Campaign disapproval |
| Financial Products | New Jan 2025 — enforced as Special Category | Campaign disapproval |

Must declare Special Ad Category BEFORE campaign creation. See `compliance.md` for full details.
