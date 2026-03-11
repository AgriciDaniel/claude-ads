---
name: copywriting
description: >
  Landing page copy, headlines, feature page copy, and CTA copy for
  marketing pages supporting Meta ad campaigns. Optimized for conversion
  from paid traffic. Triggers on: "landing page copy", "page copy",
  "headline copy", "write copy", "marketing copy", "CTA copy", "hero
  section", "above the fold".
argument-hint: "<page type> | <offer description>"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - WebFetch
---

# Copywriting — Landing Page & Marketing Copy

Produces conversion-focused copy for landing pages and marketing pages
that receive paid traffic from Meta campaigns. Follows direct-response
principles: clear offer, strong hook, benefits over features, social proof,
and a single CTA.

## Process

1. Read campaign brief from `campaigns/{name}/brief.md` if available
2. Identify page type (landing page, feature page, pricing page, etc.)
3. Generate copy for the specified page
4. Provide copy in sections ready for implementation

## Page Types Supported

| Page Type | What It Does | Primary Metric |
|-----------|-------------|---------------|
| Lead gen landing page | Captures name + email via form | Lead form conversion rate |
| Sales landing page | Drives purchase decision | Conversion rate, ROAS |
| Feature page | Explains product capabilities | Scroll depth, demo requests |
| Pricing page | Converts evaluation to purchase | Plan selection rate |
| Thank-you page | Post-conversion confirmation | Email open rate (nurture) |

---

## Landing Page Copy Structure

Produce copy for each section in order:

### 1. Hero Section (Above the Fold)
The most important section. Must answer: What is it? Who is it for? Why now?

- **Headline:** 1 sentence, ≤12 words. Lead with outcome or problem relief.
  Write 3 options.
- **Subheadline:** 1–2 sentences. Expand on headline, add specificity.
- **Primary CTA button:** Action verb + benefit. Not "Submit." Try:
  "Get My Free [Resource]" / "Start My Free Trial" / "Book a Demo"
- **Supporting element:** Social proof snippet, trust badge, or hero visual
  direction

### 2. Problem / Agitation Section
Make the reader feel their problem before introducing the solution.
- 2–4 bullet points or short paragraphs
- Use language your audience uses to describe their own pain
- End with a transition toward the solution

### 3. Solution Introduction
Introduce the product/service as the answer to the problem above.
- 1 clear positioning sentence
- 3–5 benefit bullet points (benefits, not features)
- Optional: product screenshot or visual direction

### 4. How It Works (3 Steps)
Reduce anxiety by making the process simple and clear.
```
Step 1: {action} — {brief description}
Step 2: {action} — {brief description}
Step 3: {action / result} — {brief description}
```

### 5. Social Proof Section
Choose the most credible form available:
- Client testimonials (2–3, with name, title, company)
- Case study stat ("Company X increased leads by 40% in 30 days")
- Review count and rating ("4.8/5 from 500+ customers")
- Logo wall (list notable client names for direction)

### 6. Features / Details Section
Address rational objections and confirm suitability.
- 4–6 features with 1-line descriptions
- Include any relevant specifications, integrations, or compatibility

### 7. FAQ Section
Pre-empt the 4–6 most common objections or questions.
Format as Q&A pairs. Common topics: price, time to results, support,
cancellation, who it's for, what's included.

### 8. Final CTA Section
Repeat the primary CTA with urgency or scarcity framing (if genuine).
- Headline: reinforce the transformation
- CTA button: same as hero section
- Optional: risk reversal ("No credit card required" / "30-day guarantee")

---

## CTA Copy Principles

- Use first-person: "Get My Report" > "Get Your Report" > "Download"
- Be specific: "Start My Free 14-Day Trial" > "Get Started"
- Remove friction: lead with the benefit, end with the action
- Avoid vague: never use "Submit", "Click Here", "Learn More" as primary CTA

## Headline Formulas (for Variants)

| Formula | Example |
|---------|---------|
| [Number] [Outcome] in [Timeframe] | "27 Leads in 30 Days Without a Sales Team" |
| Stop [Pain]. Start [Outcome]. | "Stop Wasting Ad Budget. Start Getting Qualified Leads." |
| [Target Audience]: [Outcome] | "Agency Owners: Fill Your Pipeline Without Cold Outreach" |
| How [Customer] [Achieved Outcome] | "How Acme Corp Cut CAC by 40% in One Quarter" |
| The [Adjective] Way to [Outcome] | "The Faster Way to Scale Your Ad Campaigns" |

---

## Output

Deliver copy in clean, section-labeled markdown ready for a developer or
no-code builder to implement. Include:
- All copy sections in order
- 3 headline variants for the hero section
- 2 CTA variants for A/B testing
- Notes on visual direction where relevant

If a campaign is active, save to `campaigns/{name}/assets/landing-page-copy.md`.
