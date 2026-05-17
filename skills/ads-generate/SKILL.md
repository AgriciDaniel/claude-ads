---
name: ads-generate
description: "AI image generation for paid ad creatives. Reads campaign-brief.md and brand-profile.json to produce platform-sized ad images using banana-claude. Requires banana-claude (v1.4.1+) with nanobanana-mcp configured. Triggers on: generate ads, create images, make ad creatives, generate visuals, create ad images, generate campaign images, make the images, generate from brief."
user-invokable: false
tested_date: 2026-05-17
tested_with: claude-code v2.x
---

# Ads Generate: AI Ad Image Generator

Generates platform-sized ad creative images from your campaign brief and brand
profile. Uses banana-claude as the image generation provider.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/ads generate` | Generate all images from campaign-brief.md |
| `/ads generate --platform meta` | Generate Meta assets only |
| `/ads generate --prompt "text" --ratio 9:16` | Standalone generation without brief |

## Environment Setup

**Required before running:**

- Requires banana-claude (v1.4.1+) with nanobanana-mcp configured
- Run `/banana setup` to configure API key and MCP
- Fallback: if banana is not available, use `scripts/generate_image.py` (deprecated)

If banana-claude is not installed, this skill will display setup instructions
and stop. It will never fail silently.

If banana-claude is unavailable, alternatives include: OpenAI gpt-image-1 ($0.040/image), Stability SD 3.5 ($0.065), or Replicate FLUX.1 Pro ($0.055). Configure via ADS_IMAGE_PROVIDER env var.

## Process

### Step 1: Verify banana-claude

Verify banana-claude is installed (run `/banana setup` to check). If not installed,
display setup instructions and exit.

### Step 2: Locate Source Files

Check for:
- `campaign-brief.md` → primary source for prompts and dimensions
- `brand-profile.json` → brand color/style injection (optional but recommended)

**If campaign-brief.md is found**: Use `## Image Generation Briefs` section as the
generation job list.

**If no campaign-brief.md**: Enter standalone mode (Step 2b).

#### Step 2b: Standalone Mode

Ask the user:
1. Generation prompt (what should the image show?)
2. Target platform (to set correct dimensions)
3. Output filename (optional)

Then skip to Step 5.

### Step 3: Read Provider Config

Load `~/.claude/skills/ads/references/image-providers.md` to confirm:
- Active provider pricing (show user the cost estimate)
- Rate limits for current tier
- Batch API availability

### Step 4: Read Platform Specs

For each platform in the campaign brief, load the relevant spec reference:
- `~/.claude/skills/ads/references/meta-creative-specs.md`
- `~/.claude/skills/ads/references/google-creative-specs.md`
- `~/.claude/skills/ads/references/tiktok-creative-specs.md`
- `~/.claude/skills/ads/references/linkedin-creative-specs.md`
- `~/.claude/skills/ads/references/youtube-creative-specs.md`
- `~/.claude/skills/ads/references/microsoft-creative-specs.md`

### Step 5: Prepare banana Configuration

Create banana brand preset from brand-profile.json if one does not already exist
at `~/.banana/presets/{brand-slug}.json`.

Select banana domain mode based on campaign brief content:
- **Product**: e-commerce, packshots
- **Editorial**: brand awareness, lifestyle
- **Cinema**: video thumbnails, dramatic
- **UI/Web**: app install, SaaS
- **Portrait**: testimonials, people

### Step 6: Spawn Visual Designer Agent

Spawn the `visual-designer` agent using the Task tool with `context: fork`,
passing the selected domain mode and preset name.

The agent will:
- Parse the image generation briefs from campaign-brief.md
- Inject brand colors and mood from brand-profile.json
- Use banana-claude with the configured domain mode for each asset
- Save to `./ad-assets/[platform]/[concept]/` directory structure
- Write `generation-manifest.json`

### Step 7: Validate with Format Adapter

After the visual-designer completes, spawn the `format-adapter` agent
with `context: fork` to validate dimensions and report missing formats.

### Step 8: Quality Gate

Use Claude vision to assess each generated image against the brief (score 1 to 10
on brand alignment, composition, platform fit). If any image scores below 6,
regenerate once with an adjusted prompt.

Quality Gate Rubric:
- 9-10: Professional quality, brand-aligned, platform-optimized, no issues
- 7-8: Good quality, minor composition or brand alignment improvements possible
- 5-6: Acceptable but needs regeneration. Text readability issues, poor composition, or brand mismatch
- Below 5: Reject. Regenerate with adjusted prompt

### Step 9: Aggregate Costs

Read banana cost data from `~/.banana/costs.json` and include total creative spend
in generation-manifest.json.

### Step 10: Report Results

Present a summary:
```
Generation complete:

  Generated assets:
    ✓ ./ad-assets/meta/concept-1/feed-1080x1350.png
    ✓ ./ad-assets/tiktok/concept-1/vertical-1080x1920.png
    ✗ ./ad-assets/google/concept-1/landscape-1200x628.png [error reason]

  Format validation: See format-report.md

  Cost: $[N] total creative spend (from ~/.banana/costs.json)

  Next steps:
    1. Review assets in ./ad-assets/
    2. Check format-report.md for any missing formats
    3. Upload to your ad platform managers
```

## Cost Transparency

Before generating, estimate and show the cost:
- Count the number of image briefs in campaign-brief.md
- Show estimated cost based on banana pricing tiers
- If >$1.00, ask for confirmation before proceeding

## Standalone Mode (No campaign-brief.md)

When running without a campaign brief:

```
Platform target → dimensions used:
  meta-feed     → 1080×1350 (4:5)
  meta-reels    → 1080×1920 (9:16)
  tiktok        → 1080×1920 (9:16)
  google-pmax   → 1200×628 (1.91:1)
  linkedin      → 1080×1080 (1:1)
  youtube       → 1280×720 (16:9)
  youtube-short → 1080×1920 (9:16)
```

Use `/banana generate` directly with the specified prompt and aspect ratio.

## Reference Files

- `~/.claude/skills/ads/references/image-providers.md`: provider config, pricing, limits
- `~/.claude/skills/ads/references/[platform]-creative-specs.md`: per-platform specs
- `~/.claude/skills/ads/references/brand-dna-template.md`: brand injection schema
