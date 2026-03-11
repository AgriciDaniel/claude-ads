---
name: social-content
description: >
  Platform-specific social media posts, captions, threads, and content
  scheduling strategy to support Meta ad campaigns with organic content.
  Triggers on: "social content", "social posts", "Instagram caption",
  "Facebook post", "LinkedIn post", "content scheduling", "organic content",
  "social media copy".
argument-hint: "<platform> | <topic or campaign>"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
---

# Social Content — Platform-Specific Posts & Captions

Generates organic social media content that supports Meta ad campaigns.
Organic content warms audiences, builds trust, and reduces CPL by giving
paid ads a social proof foundation to work from.

## Process

1. Identify platform(s), brand voice, and campaign theme
2. Read campaign brief if available (`campaigns/{name}/brief.md`)
3. Generate platform-optimized content for each specified platform
4. Provide scheduling recommendations

---

## Platform Specifications

### Facebook (Meta)
- **Post length:** 40–80 characters for best engagement; 1–3 paragraphs max
- **Format options:** link post (with preview), photo post, video post, Reel
- **Posting frequency:** 1–2x per day (avoid over-posting)
- **Best times:** Tue–Thu, 9am–3pm local time
- **Organic reach:** Boosting top organic posts as ads is highly effective
- **Caption style:** Lead with the hook, then context, then CTA
- **Link placement:** In first comment to avoid algorithm reach penalty

### Instagram
- **Caption length:** 138 characters shows in feed (rest hidden behind "more")
- **Optimal caption:** Hook in first 2 lines, story in middle, CTA at end
- **Hashtags:** 3–5 highly relevant (not 30 generic tags)
- **Stories:** Short (3–5 frames), use polls/questions for engagement
- **Reels:** 15–30 seconds, hook in first 2 seconds, caption optional
- **Posting frequency:** 4–7x per week (feed + Reels)
- **Best times:** Mon–Fri, 6am–9am and 5pm–7pm local time

### LinkedIn
- **Post length:** 150–300 characters for short posts; 1,200–1,500 for long
- **Format:** Text only (highest reach), image, document/carousel, video
- **Hook format:** Bold statement or contrarian opinion on line 1
- **Line breaks:** Single sentences with white space (scannable)
- **No links in post:** Post link in first comment for better reach
- **Posting frequency:** 3–5x per week
- **Best times:** Tue–Thu, 8am–10am and 5pm–6pm

---

## Content Formats

### Short Post (≤3 paragraphs)
For daily or near-daily posting. Fast to consume, single idea.

Structure:
```
[Hook — strong opinion, surprising fact, or question]

[Context — 1-2 sentences of support]

[CTA — comment, share, follow, or click]
```

### Long-Form Post (LinkedIn / Facebook)
For thought leadership and organic reach building.

Structure:
```
[Hook — bold opening line]

[Personal story or client story — 2-3 paragraphs]

[Key insight or lesson — numbered list or clear takeaway]

[Implication for the reader]

[CTA — follow, comment with experience, or link in comments]
```

### Carousel / Document Post (LinkedIn / Instagram)
High engagement format. Each slide = one idea.

Structure:
- Slide 1: Cover — bold headline + visual hook
- Slides 2–7: One point per slide, brief text, supporting visual
- Last slide: CTA + follow prompt

### Thread (Facebook Groups / LinkedIn)
Multi-part posts for deep-dive topics.

Structure:
```
Post 1: Provocative question or statement (gets initial engagement)
Post 2: Context and setup
Post 3–6: Main points (one per reply)
Final: Takeaway + CTA
```

---

## Organic-to-Paid Amplification

Use top-performing organic posts to reduce paid ad CAC:

1. **Boost winning posts:** Posts with >3% engagement rate → boost as Meta ad
2. **Social proof for ads:** High-comment posts → screenshot for ad creative
3. **Audience seeding:** Engaged post audience → Custom Audience for retargeting
4. **Content testing:** Test angles organically first, scale paid for winners

---

## Content Calendar Template (Monthly)

| Week | Platform | Format | Topic | Angle | CTA |
|------|----------|--------|-------|-------|-----|
| 1 | Instagram | Reel | {topic} | Pain | Follow |
| 1 | LinkedIn | Long post | {topic} | Thought leadership | Comment |
| 1 | Facebook | Photo post | {topic} | Outcome | Share |
| 2 | Instagram | Carousel | {topic} | How-to | Save |
| 2 | LinkedIn | Short post | {topic} | Contrarian | Repost |
| ... | ... | ... | ... | ... | ... |

---

## Output

Deliver content in platform-labeled sections:
- 5–10 posts per platform requested
- Include caption copy, hashtags (Instagram), and CTA
- Flag which posts are strong boost candidates for Meta ads
- Provide 30-day scheduling recommendation
