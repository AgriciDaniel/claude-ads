---
name: ads-creative
user-invocable: false
description: >
  Cross-platform creative quality audit covering ad copy, video, image, and
  format diversity across all platforms. Detects creative fatigue, evaluates
  platform-native compliance, and provides production priorities. Use when
  user says "creative audit", "ad creative", "creative fatigue", "ad copy",
  "ad design", or "creative review".
---

# Cross-Platform Creative Quality Audit

## Process

1. Collect creative assets or performance data from active platforms
2. Read `ads/references/platform-specs.md` for creative specifications
3. Read `ads/references/benchmarks.md` for CTR/engagement benchmarks
4. Read `ads/references/scoring-system.md` for weighted scoring algorithm
5. Evaluate creative quality per platform
6. Assess cross-platform creative consistency
7. Generate production priority recommendations

## Per-Platform Assessment

### Google Ads Creative
- RSA: ≥8 unique headlines, ≥3 descriptions per ad group
- RSA ad strength: "Good" or "Excellent"
- Pin usage: minimal and strategic (over-pinning kills RSA flexibility)
- Extensions: sitelinks (≥4), callouts (≥4), structured snippets, image
- PMax asset groups: text + image + video + optional product feed
- YouTube: video quality, hook, subtitles (see ads-youtube sub-skill)

### Meta Ads Creative
- Format diversity: ≥3 formats active (image, video, carousel, collection)
- Creative volume: ≥5 creatives per ad set
- Fatigue detection: CTR declining >20% over 14 days = FAIL
- Video length: 15s max Stories/Reels, 30s max Feed
- UGC/testimonial content tested
- Advantage+ Creative enhancements enabled
- Headline under 40 chars, primary text under 125 chars

### LinkedIn Creative
- Thought Leader Ads active, ≥30% budget for B2B
- Format diversity: ≥2 formats tested (single image, carousel, video, document)
- Video ads tested
- Creative refresh: every 4-6 weeks
- Professional tone appropriate for platform

### TikTok Creative
- ≥6 creatives per ad group (Critical requirement)
- All video 9:16 vertical 1080x1920 (non-negotiable)
- Native-looking content (not corporate)
- Hook in first 1-2 seconds
- No creative active >7 days with declining CTR
- Spark Ads tested (~3% CTR vs ~2% standard)
- Sound-on optimization (never silent)
- Safe zone compliance: X:40-940, Y:150-1470
- Trending audio used

### Microsoft Creative
- RSA: ≥8 headlines, ≥3 descriptions
- Multimedia Ads tested (unique rich format)
- Ad copy optimized for Bing demographics (older, higher income, professional)
- Action Extension utilized (unique to Microsoft)
- Filter Link Extension tested

## Creative Fatigue Detection

### Signals of Fatigue
| Signal | Threshold | Action |
|--------|-----------|--------|
| CTR declining | >20% over 14 days | Refresh creative |
| Frequency (Meta) | >5.0 prospecting, >12.0 retargeting | New audience or creative |
| Watch time declining (TikTok) | <3s average | New hook needed |
| QS declining (Google) | Drop of 2+ points | Refresh ad copy |
| Engagement rate drop | >30% decline | Full creative overhaul |

### Refresh Cadence by Platform
| Platform | Recommended Refresh |
|----------|-------------------|
| Google Search | Every 8-12 weeks |
| Meta | Every 2-4 weeks |
| LinkedIn | Every 4-6 weeks |
| TikTok | Every 5-7 days (fastest fatigue) |
| Microsoft | Every 8-12 weeks |
| YouTube | Every 4-8 weeks |

## Format Diversity Matrix

Evaluate which formats are active per platform:

| Format | Google | Meta | LinkedIn | TikTok | Microsoft |
|--------|--------|------|----------|--------|-----------|
| Static Image | RSA image ext | ✅ | ✅ | ❌ | Multimedia |
| Video | YouTube, PMax | ✅ | ✅ | ✅ (required) | ❌ |
| Carousel | ❌ | ✅ | ✅ | ❌ | ❌ |
| Collection | ❌ | ✅ | ❌ | ❌ | ❌ |
| Document | ❌ | ❌ | ✅ | ❌ | ❌ |
| Shopping | PMax, Shopping | Catalog | ❌ | Shop | Shopping |

## Universal Creative Best Practices

### Cross-Platform Safe Zone
- 900x1000px usable area works across all vertical placements
- Keep critical elements centered and within safe margins
- Test on mobile devices (75%+ of ad impressions are mobile)

### Ad Copy Principles
- Lead with benefit, not feature
- Include clear CTA (what should they do next?)
- Match ad message to landing page (message match)
- Use numbers and specifics over vague claims
- Test emotional vs rational appeals

### Video Production Standards
- H.264 codec, AAC audio, MP4 container
- Minimum 720p (1080p preferred)
- Subtitles/captions always (accessibility + sound-off viewing)
- Brand mention within first 5s (awareness) or at CTA (performance)

## Output

### Creative Quality Report

```
Cross-Platform Creative Health

Google:     ████████░░  X/X checks passing
Meta:       ██████████  X/X checks passing
LinkedIn:   ███████░░░  X/X checks passing
TikTok:     █████░░░░░  X/X checks passing
Microsoft:  ████████░░  X/X checks passing
```

### Deliverables
- `CREATIVE-AUDIT-REPORT.md` — Per-platform creative assessment
- Fatigue alerts (any creative past refresh cadence)
- Format diversity gaps per platform
- Production priority list (most impactful creative to produce next)
- Quick Wins (format conversions, CTA changes, Spark Ads setup)
