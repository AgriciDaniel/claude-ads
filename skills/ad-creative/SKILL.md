---
name: ad-creative
description: >
  Generates Meta ad copy across three proven angles (pain, outcome, social
  proof) with full headline variants, primary text, CTA, link headline,
  description, and image overlay directions. Triggers on: "ad copy", "ad
  creative", "write ads", "copy variants", "Meta copy", "Facebook copy",
  "ad angles", "creative angles".
argument-hint: "<campaign-name> | <offer description>"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
---

# Ad Creative — 3-Angle Meta Copy Generation

Generates complete Meta ad copy across three angles for every ad set in a
campaign. Produces headline variants, primary text, CTA, link headline,
description, and image overlay directions for each.

## Process

1. Read campaign brief from `campaigns/{name}/brief.md` (if it exists)
2. If no brief, collect: offer, target audience, transformation, proof points
3. Generate copy for all three angles
4. Write output to `campaigns/{name}/copy.md`
5. Log generation in `campaigns/{name}/log.md`

## The Three Angles

Every Meta campaign should test these three angles simultaneously:

### Angle 1 — Pain
Lead with the problem the audience is experiencing. Make them feel seen.
The ad should articulate the pain better than they can themselves.

**Formula:**
- Primary text opens with the problem, agitates it, then offers relief
- Headline names the problem or the solution to it
- CTA: "Learn More" or "Get Free [Resource]"

**Pain angle triggers:** cost, time wasted, frustration, missed opportunity,
fear of falling behind, watching competitors succeed

### Angle 2 — Outcome
Lead with the transformation. Show them what life looks like after they buy.
Specific, vivid, believable results outperform vague promises.

**Formula:**
- Primary text opens with a specific result or scenario
- Headline leads with the outcome (number, timeframe, or transformation)
- CTA: "See How" or "Get Started" or "Book a Call"

**Outcome angle triggers:** revenue increase, time saved, leads generated,
growth achieved, problem eliminated, goal reached

### Angle 3 — Social Proof
Lead with validation. Others like them have already done it.
Trust reduces friction. Specificity beats generality.

**Formula:**
- Primary text opens with a client result, testimonial, or data point
- Headline reinforces the proof ("How [Company] achieved [Result]")
- CTA: "See Results" or "Read the Story" or "Join [Number]+ Others"

**Social proof triggers:** case study stats, client quotes, customer count,
reviews, awards, media mentions, before/after data

---

## Copy Specifications

For each of the three angles, produce all of the following:

### Primary Text (Body Copy)
- Length: 80–125 characters for mobile-first delivery
- Format: 1–3 short paragraphs or line breaks
- No emojis unless brand voice calls for it
- Include a soft CTA in the final line
- Write 2 variants per angle (A and B)

### Headline
- Max 40 characters (truncation threshold)
- Direct, specific, benefit-led or curiosity-led
- Write 3 headline options per angle

### Link Headline (below image)
- Max 25 characters
- Action-oriented or benefit-focused

### Description (below link headline)
- Max 30 characters
- Reinforce the offer or add urgency

### CTA Button
Select from: Learn More | Sign Up | Get Quote | Book Now | Download |
Apply Now | Contact Us | Watch More | Send Message | Get Offer

### Image Overlay Direction
Brief text direction for the static ad creative:
- Background concept (photo, illustration, flat color)
- Overlay text (max 20% of image area per Meta policy)
- Visual hierarchy note

---

## Output Format

Write to `campaigns/{campaign-name}/copy.md`:

```markdown
# Ad Copy — {Campaign Name}

Generated: {YYYY-MM-DD}
Angles: Pain | Outcome | Social Proof

---

## Angle 1 — Pain

### Primary Text A
{copy}

### Primary Text B
{copy}

### Headlines
1. {headline}
2. {headline}
3. {headline}

### Link Headline
{text}

### Description
{text}

### CTA Button
{button label}

### Image Overlay Direction
{brief visual direction}

---

## Angle 2 — Outcome

[same structure]

---

## Angle 3 — Social Proof

[same structure]

---

## Copy Usage Map

| Ad Name | Angle | Primary Text | Headline |
|---------|-------|-------------|---------|
| pain_image_v1 | Pain | Primary Text A | Headline 1 |
| pain_image_v2 | Pain | Primary Text B | Headline 2 |
| outcome_image_v1 | Outcome | Primary Text A | Headline 1 |
| outcome_image_v2 | Outcome | Primary Text B | Headline 2 |
| proof_image_v1 | Social Proof | Primary Text A | Headline 1 |
| proof_image_v2 | Social Proof | Primary Text B | Headline 2 |
```

After writing, confirm: "Copy saved to `campaigns/{name}/copy.md`. 6 ad variants across 3 angles. Next: run `/html-ad` to generate static ad images."
