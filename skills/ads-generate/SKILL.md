---
name: ads-generate
description: "AI image generation for paid ad creatives. Reads campaign-brief.md and brand-profile.json to produce platform-sized ad images using Gemini (default) or a configured provider. Requires GOOGLE_API_KEY or ADS_IMAGE_PROVIDER + matching key. Triggers on: 'generate ads', 'create images', 'make ad creatives', 'generate visuals', 'create ad images', 'generate campaign images', 'make the images', 'generate from brief'."
---

# Ads Generate — AI Ad Image Generator

Generates platform-sized ad creative images from your campaign brief and brand
profile. Uses Gemini by default (`gemini-2.5-flash-image`, stable GA).

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/ads generate` | Generate all images from campaign-brief.md |
| `/ads generate --platform meta` | Generate Meta assets only |
| `/ads generate --prompt "text" --ratio 9:16` | Standalone generation without brief |
| `/ads generate --batch` | Use Gemini Batch API (50% cost, 24h turnaround) |

## Environment Setup

**Required before running:**

```bash
# Gemini (default — recommended)
export GOOGLE_API_KEY="your-key"
# Get a key: console.cloud.google.com/apis/credentials

# Switch to a different provider (optional)
export ADS_IMAGE_PROVIDER="openai"
export OPENAI_API_KEY="your-key"

export ADS_IMAGE_PROVIDER="stability"
export STABILITY_API_KEY="your-key"

export ADS_IMAGE_PROVIDER="replicate"
export REPLICATE_API_TOKEN="your-token"
```

If the API key is not set, this skill will display the setup instructions above
and stop. It will never fail silently.

## Process

### Step 1: Check API Key

Verify the required environment variable is set before proceeding:

```bash
python3 -c "
import os, sys
provider = os.environ.get('ADS_IMAGE_PROVIDER', 'gemini')
keys = {'gemini': 'GOOGLE_API_KEY', 'openai': 'OPENAI_API_KEY',
        'stability': 'STABILITY_API_KEY', 'replicate': 'REPLICATE_API_TOKEN'}
env_var = keys.get(provider, 'GOOGLE_API_KEY')
if not os.environ.get(env_var):
    print(f'Error: {env_var} not set (provider: {provider})', file=sys.stderr)
    sys.exit(1)
print(f'OK: {env_var} is set')
"
```

If this exits with code 1, display the Environment Setup section above and stop.

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

### Step 5: Spawn Visual Designer Agent

Spawn the `visual-designer` agent using the Task tool with `context: fork`.

The agent will:
- Parse the image generation briefs from campaign-brief.md
- Inject brand colors and mood from brand-profile.json
- Call generate_image.py for each asset
- Save to `./ad-assets/[platform]/[concept]/` directory structure
- Write `generation-manifest.json`

### Step 6: Validate with Format Adapter

After the visual-designer completes, spawn the `format-adapter` agent
with `context: fork` to validate dimensions and report missing formats.

### Step 7: Report Results

Present a summary:
```
Generation complete:

  Generated assets:
    ✓ ./ad-assets/meta/concept-1/feed-1080x1350.png
    ✓ ./ad-assets/tiktok/concept-1/vertical-1080x1920.png
    ✗ ./ad-assets/google/concept-1/landscape-1200x628.png [error reason]

  Format validation: See format-report.md

  Cost estimate: ~$[N] at $0.067/image (Gemini 1K)

  Next steps:
    1. Review assets in ./ad-assets/
    2. Check format-report.md for any missing formats
    3. Upload to your ad platform managers
```

## Cost Transparency

Before generating, estimate and show the cost:
- Count the number of image briefs in campaign-brief.md
- Multiply by $0.067 (Gemini default 1K)
- Show: "Estimated cost: [N] images × $0.067 = ~$[total]"
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

Calls generate_image.py directly:
```bash
python ~/.claude/skills/ads/scripts/generate_image.py \
  "[user prompt]" \
  --size [WxH] \
  --output [filename] \
  --json
```

## Reference Files

- `~/.claude/skills/ads/references/image-providers.md` — provider config, pricing, limits
- `~/.claude/skills/ads/references/[platform]-creative-specs.md` — per-platform specs
- `~/.claude/skills/ads/references/brand-dna-template.md` — brand injection schema
