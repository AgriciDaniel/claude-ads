---
name: html-ad
description: >
  Generates static Meta ad images as HTML/CSS files, then renders them to
  PNG using Playwright. Produces print-ready 1080×1080px and 1080×1350px
  ad creative files. Triggers on: "ad image", "static ad", "html ad",
  "generate creative", "ad PNG", "ad visual", "create ad image".
argument-hint: "<campaign-name> | <angle: pain|outcome|proof>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# HTML Ad — Static Ad Image Generator

Generates Meta ad creative as self-contained HTML/CSS files and renders them
to PNG using Playwright. Output lands in `campaigns/{name}/images/`.

## Process

1. Read campaign brief and copy from `campaigns/{name}/brief.md` and `copy.md`
2. Extract image overlay directions for each angle
3. Generate HTML/CSS file for each ad variant
4. Render each HTML file to PNG using Playwright (1080×1080 and 1080×1350)
5. Save PNGs to `campaigns/{name}/images/`
6. Log in `campaigns/{name}/log.md`

## Meta Ad Image Specifications

| Format | Dimensions | Aspect Ratio | Use Case |
|--------|-----------|-------------|---------|
| Square | 1080×1080px | 1:1 | Feed (Facebook, Instagram) |
| Portrait | 1080×1350px | 4:5 | Feed (Instagram, optimal reach) |
| Story | 1080×1920px | 9:16 | Stories / Reels |

**Text rule:** Text must cover <20% of image area (Meta policy).
**Safe zone:** Keep critical content 14% from all edges for Stories.
**File format:** PNG or JPG, max 30MB (PNG preferred for text legibility).

## HTML/CSS Template

Generate a self-contained HTML file per ad variant. Structure:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1080px;
    height: 1080px; /* or 1350px for 4:5 */
    overflow: hidden;
    font-family: {brand-font}, system-ui, sans-serif;
  }
  .ad-container {
    position: relative;
    width: 100%;
    height: 100%;
    background: {background-color or image};
  }
  .overlay-text {
    position: absolute;
    /* position based on design */
    color: {text-color};
    font-size: {size}px;
    font-weight: {weight};
    line-height: 1.2;
    max-width: 70%; /* keeps text within 20% area rule */
  }
  .logo {
    position: absolute;
    bottom: 40px;
    left: 40px;
  }
  .cta-badge {
    position: absolute;
    /* CTA badge positioning */
    background: {cta-color};
    color: white;
    padding: 16px 32px;
    border-radius: 4px;
    font-weight: 700;
  }
</style>
</head>
<body>
  <div class="ad-container">
    <!-- Background: solid color, gradient, or img -->
    <div class="overlay-text">{headline text}</div>
    <div class="logo">{logo or brand name}</div>
    <div class="cta-badge">{CTA text}</div>
  </div>
</body>
</html>
```

Customize for each angle:
- **Pain angle:** Darker colors, problem-focused headline, urgent feel
- **Outcome angle:** Bright/aspirational, result-focused headline, positive feel
- **Social proof angle:** Clean, data or quote prominent, trust-building feel

## Design System (Request from User if Not Provided)

Before generating, confirm or ask for:
- Brand primary color (hex)
- Brand font (or use system sans-serif)
- Logo or wordmark (file path or skip)
- Background style: solid color | gradient | stock photo direction

## Playwright Rendering Script

After generating HTML files, run:

```bash
python scripts/render-ads.py \
  --input campaigns/{campaign-name}/images/html/ \
  --output campaigns/{campaign-name}/images/ \
  --width 1080 \
  --height 1080
```

The render script:
1. Launches headless Chromium via Playwright
2. Opens each HTML file
3. Takes a full-page screenshot at exact dimensions
4. Saves as `{ad-name}.png`

If Playwright is not installed:
```bash
pip install playwright
playwright install chromium
```

## File Naming

```
campaigns/{campaign-name}/images/
  html/
    pain_image_v1.html
    outcome_image_v1.html
    proof_image_v1.html
  pain_image_v1.png         ← 1080×1080
  pain_image_v1_4x5.png     ← 1080×1350
  outcome_image_v1.png
  outcome_image_v1_4x5.png
  proof_image_v1.png
  proof_image_v1_4x5.png
```

## Output

1. Write HTML files to `campaigns/{name}/images/html/`
2. Run render script to produce PNGs
3. Confirm file list to user
4. Log in `campaigns/{name}/log.md`

After completing, confirm: "{N} ad images saved to `campaigns/{name}/images/`. Upload to Meta Ads Manager → Ads → Creative."
