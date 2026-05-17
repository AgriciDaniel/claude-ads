---
name: ads-dna
description: "Brand DNA extractor for paid advertising. Scans a website URL to extract visual identity, tone of voice, color palette, typography, and imagery style. Outputs brand-profile.json to the current directory. Run before /ads create or /ads generate for brand-consistent creative. Triggers on: brand DNA, brand profile, extract brand, brand identity, brand colors, what is the brand voice, analyze brand, brand style guide."
user-invokable: false
tested_date: 2026-05-17
tested_with: claude-code v2.x
---

# Ads DNA: Brand DNA Extractor

Extracts brand identity from a website and saves it as `brand-profile.json`
for use by `/ads create`, `/ads generate`, and `/ads photoshoot`.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/ads dna <url>` | Full brand extraction → `brand-profile.json` |
| `/ads dna https://acme.com --quick` | Fast extraction (homepage only) |

## Process

### Step 1: Collect URL

If the user hasn't provided a URL, ask:
> "What website URL should I analyze for brand DNA? (e.g. https://yoursite.com)"

### Step 2: Fetch Pages

Use the **WebFetch tool** to retrieve each page. For each URL, use this fetch prompt:
> "Return all visible text content, the full contents of any `<style>` blocks, inline
> `style=` attributes, `<meta>` tags, Google Fonts `@import` URLs, and any `og:image`
> values found on this page."

Fetch in this order:
1. **Homepage** (`<url>`)
2. **About page**: try `<url>/about`, then `<url>/about-us`, then `<url>/our-story`
3. **Product/Services page**: try `<url>/product`, then `<url>/products`, then `<url>/services`

**If `--quick` flag was provided**: fetch the homepage only; skip steps 2 and 3.

If a secondary page returns a 404 or redirect error, continue with fewer pages and note:
"Secondary pages unavailable; extraction based on homepage only. Confidence may be lower."

### Step 2b: Capture Brand Screenshots

After fetching pages, capture 3 screenshots for comprehensive brand anchoring.
These serve as visual style references during `/ads generate`; the same approach
Pomelli uses to anchor ad images to the actual brand aesthetic.

Capture the following:

1. **Homepage hero section** (above the fold):
```bash
python ~/.claude/skills/ads/scripts/capture_screenshot.py [url]
```
Saves: `./brand-screenshots/{domain}_homepage.png`

2. **Product or services page**:
```bash
python ~/.claude/skills/ads/scripts/capture_screenshot.py [url]/products
```
Saves: `./brand-screenshots/{domain}_product.png`

3. **About page** (brand personality):
```bash
python ~/.claude/skills/ads/scripts/capture_screenshot.py [url]/about
```
Saves: `./brand-screenshots/{domain}_about.png`

If a page is not found or returns an error, skip it gracefully and continue
with the remaining pages.

**If `--quick` flag was provided**: skip screenshot capture entirely.

**If capture fails** (Playwright not installed, network error, JS-heavy SPA that times out):
- Log: `"Screenshot capture skipped; run: python3 -m playwright install chromium"`
- Continue without screenshots
- Do NOT set the `screenshots` field in brand-profile.json

### Step 3: Extract Brand Elements

From the fetched HTML, extract:

**Colors:**
- `og:image` meta tag → analyze dominant colors (note 2-3 prominent hex values)
- CSS `background-color` on `body`, `header`, `.hero`, `.btn-primary`
- CSS `color` on `h1`, `h2`, `.btn`
- CSS `border-color` or `background` on `.cta`, `.button`
- Identify: primary (most prominent brand color), secondary (supporting colors), background, text

**Typography:**
- `@import url(https://fonts.googleapis.com/...)` → extract font names from URL path
- CSS `font-family` on `h1`, `h2`, `body`, `.headline`
- If Google Fonts URL contains `family=Inter:wght@...`, heading_font = "Inter"

**Voice:**
Analyze hero headline, subheadline, About page intro, and CTA button text.
Score each axis 1-10 using these heuristics:

| Signal | Score direction |
|--------|----------------|
| Uses "you/your" frequently | formal_casual → casual (+2) |
| Uses technical jargon | expert_accessible → expert (-2) |
| Short punchy sentences (≤8 words) | bold_subtle → bold (+2) |
| Data/stats in hero | rational_emotional → rational (-2) |
| "Transform", "revolutionize", "disrupt" | traditional_innovative → innovative (+2) |
| Customer testimonials lead | rational_emotional → emotional (+2) |
| Industry awards, "trusted by X" | traditional_innovative → traditional (-1) |

### Confidence Scoring
Each voice axis gets a confidence rating based on signal count:
- **High** (3+ signals): strong evidence for axis position
- **Medium** (2 signals): moderate evidence, may need validation
- **Low** (1 signal): weak evidence, treat as estimate

Also extract structured data when available: schema.org markup, Open Graph tags (og:title, og:description, og:image), Twitter Card metadata.

**Imagery style** (from og:image and any visible hero image descriptions):
- Photography vs. illustration vs. flat design
- Subject matter (people, product, abstract, data)
- Composition style (clean/minimal vs. busy/editorial)

**Forbidden elements** (infer from brand positioning):
- Enterprise/B2B brands → add "cheesy stock photos", "consumer lifestyle imagery"
- Healthcare → add "unqualified medical claims", "before/after imagery"
- Finance → add "get rich quick imagery", "unrealistic wealth displays"
- Consumer brands → usually no forbidden elements

### Step 4: Build brand-profile.json

Read `~/.claude/skills/ads/references/brand-dna-template.md` for the exact schema.

Construct the JSON object following the schema precisely. Use `null` for any
field that cannot be confidently extracted; do not guess.

Example of a low-confidence field:
```json
"typography": {
  "heading_font": null,
  "body_font": "system-ui",
  "pairing_descriptor": "system default (Google Fonts not detected)"
}
```

### Step 5: Write brand-profile.json

Write the JSON to `./brand-profile.json` in the current working directory
(where the user is running Claude Code).

If screenshots were captured successfully in Step 2b, include a `screenshots` field:
```json
"screenshots": {
  "homepage": "./brand-screenshots/{domain}_homepage.png",
  "product": "./brand-screenshots/{domain}_product.png",
  "about": "./brand-screenshots/{domain}_about.png"
}
```
Include only the screenshots that were successfully captured. If a page was not
found or errored, omit that key. Omit the `screenshots` field entirely if Step 2b
was skipped or all captures failed.

### Step 6: Confirm and Summarize

Show the user:
```
✓ brand-profile.json saved to ./brand-profile.json

Brand DNA Summary:
  Brand: [brand_name]
  Voice: [descriptor 1], [descriptor 2], [descriptor 3]
  Primary Color: [hex]
  Typography: [heading_font] / [body_font]
  Target: [age_range] [profession]
  Screenshots: [N captured (homepage, product, about) in ./brand-screenshots/] OR [skipped]

Run `/ads create` to generate campaign concepts from this profile.
```

## Visual Designer Integration

The visual-designer agent uses the most relevant screenshot per concept as a style
reference when generating images via banana. For example, a product-focused concept
references the product page screenshot, while a brand awareness concept references
the homepage or about page screenshot.

## Limitations

- **Sparse content**: Sites with <200 words of body text produce lower-confidence profiles.
  Note: "Low confidence extraction; limited content available for analysis."
- **Dynamic sites**: JavaScript-rendered content may not be captured. Playwright is not
  used by default. If the site appears to be SPA/React with no static HTML, note this.
- **Multi-brand enterprises**: This tool creates one profile per URL. Run separately
  for each brand/product line.
- **Dark mode sites**: If body background is #333 or darker, swap background/text values.
- **CSS-in-JS**: Modern React sites may not have extractable CSS. Use og:image colors as fallback.

## brand-profile.json Schema

```json
{
  "schema_version": "1.0",
  "brand_name": "string",
  "website_url": "string",
  "extracted_at": "ISO-8601",
  "voice": {
    "formal_casual": 1-10,
    "rational_emotional": 1-10,
    "playful_serious": 1-10,
    "bold_subtle": 1-10,
    "traditional_innovative": 1-10,
    "expert_accessible": 1-10,
    "descriptors": ["adjective1", "adjective2", "adjective3"]
  },
  "colors": {
    "primary": "#hexcode or null",
    "secondary": ["#hex1", "#hex2"],
    "forbidden": ["#hex or color name"],
    "background": "#hexcode",
    "text": "#hexcode"
  },
  "typography": {
    "heading_font": "Font Name or null",
    "body_font": "Font Name or system-ui",
    "pairing_descriptor": "brief description"
  },
  "imagery": {
    "style": "professional photography | illustration | flat design | mixed",
    "subjects": ["subject1", "subject2"],
    "composition": "brief description",
    "forbidden": ["element1", "element2"]
  },
  "aesthetic": {
    "mood_keywords": ["keyword1", "keyword2", "keyword3"],
    "texture": "minimal | textured | mixed",
    "negative_space": "generous | moderate | dense"
  },
  "brand_values": ["value1", "value2", "value3"],
  "target_audience": {
    "age_range": "e.g. 25-45",
    "profession": "brief description",
    "pain_points": ["pain1", "pain2"],
    "aspirations": ["aspiration1", "aspiration2"]
  }
}
```
