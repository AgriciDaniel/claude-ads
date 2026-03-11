---
name: page-cro
description: >
  Full conversion rate optimization audit for landing pages and marketing
  pages receiving paid traffic. Scores 40 CRO checks across messaging
  match, trust signals, form friction, page speed, and mobile experience.
  Triggers on: "CRO", "conversion rate", "page audit", "landing page audit",
  "why isn't my page converting", "improve conversions", "page optimization".
argument-hint: "<URL or page description>"
allowed-tools:
  - Read
  - Write
  - WebFetch
  - Glob
  - Grep
---

# Page CRO — Conversion Rate Optimization Audit

Audits landing pages for conversion rate issues using 40 weighted checks
across 5 categories. Produces a scored report with prioritized fixes.

## Process

1. Get page URL or content (screenshot, copy paste, or URL via WebFetch)
2. Evaluate all 40 checks across 5 categories
3. Score each check: PASS / WARNING / FAIL
4. Calculate CRO Health Score (0–100)
5. Generate prioritized action plan

---

## The 40 CRO Checks (8 per category)

### Category 1 — Message Match (25% weight)
Traffic from Meta ads must land on a page that matches the ad's promise.
Any mismatch kills conversion rate.

1. Headline matches or continues the ad's primary message
2. Offer on page matches the offer in the ad (same product, price, terms)
3. Visual style/tone consistent with ad creative
4. Target audience recognized within 3 seconds of landing
5. CTA on page matches ad's CTA button (no bait-and-switch)
6. Page URL contains campaign-relevant path (not just homepage)
7. Retargeting ads link to a different page than cold traffic ads
8. A/B test variants send traffic to matching page variants

### Category 2 — Trust & Credibility (20% weight)
Visitors from paid traffic have no prior relationship. Trust must be built fast.

9. Social proof visible above the fold (reviews, logos, counts)
10. Real testimonials with name, photo, and company (not generic)
11. Trust badges present (SSL, payment logos, guarantees, certifications)
12. Contact information visible (email, phone, or chat widget)
13. Privacy policy link present near any form
14. No broken links, 404 pages, or placeholder content
15. Author/company identity clear (who is behind this?)
16. Media mentions or partnerships displayed if available

### Category 3 — Offer Clarity (25% weight)
The visitor must immediately understand what they're getting, what it costs,
and why they should act now.

17. Headline clearly states the primary benefit (not the feature)
18. Offer described in plain language (no jargon)
19. Price or cost of inaction stated clearly
20. What's included in the offer is explicit (no vague promises)
21. Single, clear primary CTA (not competing with secondary actions)
22. CTA uses first-person, action-oriented copy
23. Urgency or scarcity present (if genuine — not fake countdown timers)
24. Risk reversal present (guarantee, free trial, no credit card required)

### Category 4 — Form & Friction (15% weight)
Every unnecessary field or click reduces conversion rate.

25. Form asks only for essential fields (name + email = minimum)
26. Each extra field reduces conversion ~11% — justified by lead quality need?
27. Form labels above fields (not placeholder text that disappears on click)
28. Submit button is CTA copy, not "Submit" or "Send"
29. Error messages are specific and helpful (not just "required field")
30. Auto-fill enabled for name, email, phone fields
31. Multi-step form used if >5 fields (reduces abandonment)
32. Thank-you page confirms what happens next (sets expectations)

### Category 5 — Technical & Mobile (15% weight)
Page speed and mobile experience are conversion rate multipliers.

33. Page load time under 3 seconds (use PageSpeed Insights)
34. Core Web Vitals: LCP <2.5s, CLS <0.1, FID <100ms
35. Mobile layout tested: no horizontal scroll, text legible without zoom
36. CTA button is finger-tap size on mobile (≥48px tap target)
37. Form fields are large enough to tap accurately on mobile
38. Images are compressed and lazy-loaded
39. No intrusive pop-ups on mobile (Google penalty risk)
40. Page renders correctly in Safari (iOS) — top Meta traffic browser

---

## Scoring System

| Score | Grade | Status |
|-------|-------|--------|
| 90–100 | A | Excellent — optimize for incremental gains |
| 75–89 | B | Good — fix warnings to push above 90 |
| 60–74 | C | Fair — significant conversion losses occurring |
| 45–59 | D | Poor — major issues require immediate fixes |
| <45 | F | Critical — page likely converting well below 1% |

**Scoring method:**
- PASS = full points
- WARNING = 50% of points
- FAIL = 0 points
- Score = (points earned / total points possible) × 100

---

## Benchmark Conversion Rates

| Page Type | Excellent | Good | Average | Poor |
|-----------|-----------|------|---------|------|
| Lead gen (Meta traffic) | >15% | 8–15% | 4–8% | <4% |
| E-commerce (Meta traffic) | >4% | 2–4% | 1–2% | <1% |
| SaaS free trial | >10% | 5–10% | 2–5% | <2% |
| Webinar registration | >30% | 20–30% | 10–20% | <10% |

---

## Output Format

```
CRO Health Score: XX/100 (Grade: X)

Message Match:    XX/100  ████████░░  (25%)
Trust:            XX/100  ██████████  (20%)
Offer Clarity:    XX/100  ███████░░░  (25%)
Form & Friction:  XX/100  █████░░░░░  (15%)
Technical/Mobile: XX/100  ████░░░░░░  (15%)

## Critical Issues (Fix This Week)
1. {issue} — {specific fix}

## Warnings (Fix This Month)
1. {issue} — {specific fix}

## Quick Wins (Easy Improvements)
1. {issue} — {specific fix}

## Estimated CVR Impact
Current estimated CVR: {range}%
Expected CVR with fixes: {range}%
Estimated additional leads/month at {budget}: {number}
```
