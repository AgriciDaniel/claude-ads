---
name: content-strategy
description: >
  Topic clusters, content calendar, SEO angle planning, and pillar/cluster
  content architecture to support paid ad campaigns with organic reach.
  Triggers on: "content strategy", "content plan", "content calendar",
  "topic clusters", "SEO content", "blog strategy", "content marketing".
argument-hint: "<industry> | <target audience> | <goals>"
allowed-tools:
  - Read
  - Write
  - WebFetch
  - Glob
  - Grep
---

# Content Strategy — Topic Clusters & Content Calendar

Builds a content architecture that supports Meta ad campaigns with organic
reach and retargeting audiences. Covers pillar pages, cluster content,
content calendar, and SEO angle planning.

## Process

1. Identify industry, target audience, and business goals
2. Read campaign context from `campaigns/` if available
3. Map topic clusters around core business themes
4. Generate content calendar (90-day)
5. Identify SEO angles for each cluster
6. Suggest retargeting audience segments from content traffic

---

## Topic Cluster Architecture

### Pillar Pages (1–3 per quarter)
Long-form, comprehensive content on core topics (2,000–4,000 words).
Each pillar page:
- Targets a high-volume, competitive keyword
- Internally links to all cluster pages on the same topic
- Serves as the cornerstone for organic authority building

### Cluster Content (5–10 per pillar)
Focused articles, guides, or tools that support the pillar.
Each cluster piece:
- Targets a specific long-tail keyword variant
- Answers one specific question the audience has
- Links back to the pillar page

### Content Funnel Mapping
Map content to funnel stage so it can feed Meta retargeting audiences:

| Stage | Content Type | Meta Audience Segment |
|-------|-------------|----------------------|
| TOFU | Blog posts, guides, how-tos | Visitors (180-day) |
| MOFU | Case studies, comparisons, calculators | Visitors (30-day) |
| BOFU | Pricing, demos, testimonials | Visitors (7-day) |

---

## 90-Day Content Calendar

Produce a content calendar with:
- 12 posts per month (3 per week = sustainable pace)
- Mix of pillar support pieces, thought leadership, and tactical guides
- Seasonal or industry event alignment
- Format variety: article, how-to, list, case study, tool

| Week | Title | Type | Funnel Stage | Target Keyword | CTA |
|------|-------|------|-------------|---------------|-----|
| 1 | {title} | Article | TOFU | {keyword} | Subscribe |
| 2 | {title} | How-to | TOFU | {keyword} | Download |
| 3 | {title} | Case study | MOFU | {keyword} | Book Demo |
| 4 | {title} | Comparison | MOFU | {keyword} | Start Trial |

---

## SEO Angle Planning

For each pillar topic, identify:

### Keyword Tiers
- **Head term** (1–2 words): high volume, high competition — target with pillar
- **Body keywords** (2–3 words): medium volume — target with cluster content
- **Long-tail** (4+ words): lower volume, high intent — target with specific posts

### Intent Mapping
- **Informational** ("how to X"): drives TOFU traffic → retargeting audiences
- **Navigational** (brand searches): brand authority signal
- **Commercial** ("best X for Y"): drives MOFU traffic → trial/demo CTAs
- **Transactional** ("buy X", "X pricing"): BOFU → direct conversion

### Content Differentiation
For each piece, identify the angle that makes it better than current ranking
content:
- More comprehensive (longer, more examples)
- More current (updated data, 2026 benchmarks)
- More specific (niche audience, specific use case)
- More actionable (step-by-step, templates, downloads)

---

## Content-to-Ad Connection

Content strategy should feed Meta ad campaigns:
1. Best-performing organic posts → repurpose as ad creative angles
2. Content readers → retargeting audience in Meta
3. High-intent readers (pricing, comparison pages) → hot retargeting segment
4. Email subscribers from content → Custom Audience seed for Lookalikes

---

## Output

Deliver a content strategy document covering:
- 3 pillar topics with rationale
- 5 cluster content ideas per pillar (15 total)
- 90-day content calendar
- Keyword tier map for each pillar
- Content-to-Meta retargeting audience plan

If applicable, save to `research/content-strategy.md`.
