# Claude Ads — Paid Advertising Audit & Optimization Skill

## Project Overview

This repository contains **Claude Ads**, a Tier 4 Claude Code skill for comprehensive
paid advertising analysis across all major platforms. It follows the Agent Skills open
standard and the 3-layer architecture (directive, orchestration, execution). 12 sub-skills,
6 parallel subagents, and 11 industry templates cover Google, Meta, YouTube, LinkedIn,
TikTok, and Microsoft Ads with 186 weighted audit checks.

## Architecture

```
claude-ads/
  CLAUDE.md                          # Project instructions (this file)
  ads/                               # Main orchestrator skill
    SKILL.md                         # Entry point, routing table, core rules
    references/                      # On-demand knowledge files (12 files)
    scripts/                         # Python execution scripts
  skills/                            # 22 specialized sub-skills
    ads-audit/SKILL.md              # Full multi-platform audit
    ads-google/SKILL.md            # Google Ads deep analysis
    ads-meta/SKILL.md              # Meta/Facebook Ads analysis
    ads-youtube/SKILL.md           # YouTube Ads analysis
    ads-linkedin/SKILL.md         # LinkedIn Ads analysis
    ads-tiktok/SKILL.md           # TikTok Ads analysis
    ads-microsoft/SKILL.md        # Microsoft/Bing Ads analysis
    ads-creative/SKILL.md         # Creative quality assessment
    ads-landing/SKILL.md          # Landing page analysis
    ads-budget/SKILL.md           # Budget allocation optimization
    ads-plan/SKILL.md             # Strategic ad planning by industry
    ads-competitor/SKILL.md       # Competitor ad research
    paid-ads/SKILL.md             # Campaign strategy & structure (Meta)
    ad-creative/SKILL.md          # 3-angle ad copy generation
    ab-test-setup/SKILL.md        # A/B test plan design
    analytics-tracking/SKILL.md   # GA4, Pixel, CAPI, UTM setup
    html-ad/SKILL.md              # Static ad image generation (HTML→PNG)
    copywriting/SKILL.md          # Landing page & marketing copy
    page-cro/SKILL.md             # Conversion rate optimization audit
    content-strategy/SKILL.md     # Topic clusters & content calendar
    social-content/SKILL.md       # Platform-specific social posts
    revops/SKILL.md               # Lead scoring & CRM automation
  agents/                            # 6 parallel subagents
    audit-google.md                # Google Ads audit agent
    audit-meta.md                  # Meta Ads audit agent
    audit-creative.md              # Creative quality agent
    audit-tracking.md              # Conversion tracking agent
    audit-budget.md                # Budget analysis agent
    audit-compliance.md            # Compliance verification agent
  campaigns/                         # All active and past campaigns
    README.md                      # Naming conventions & structure guide
    .template/                     # Campaign file templates
  scripts/
    render-ads.py                  # Playwright HTML→PNG renderer
  install.sh / install.ps1          # Cross-platform installers
  uninstall.sh / uninstall.ps1      # Cross-platform uninstallers
```

## Commands

### Audit & Analysis
| Command | Purpose |
|---------|---------|
| `/ads audit` | Full multi-platform audit with 6 parallel agents |
| `/ads google` | Google Ads deep analysis |
| `/ads meta` | Meta/Facebook Ads analysis |
| `/ads youtube` | YouTube Ads analysis |
| `/ads linkedin` | LinkedIn Ads analysis |
| `/ads tiktok` | TikTok Ads analysis |
| `/ads microsoft` | Microsoft/Bing Ads analysis |
| `/ads creative` | Creative quality and fatigue assessment |
| `/ads landing` | Landing page conversion analysis |
| `/ads budget` | Budget allocation optimization |
| `/ads plan <type>` | Strategic ad planning by industry |
| `/ads competitor` | Competitor ad research |

### Meta Campaign Manager
| Command | Purpose | Output |
|---------|---------|--------|
| `/paid-ads` | Campaign strategy, audience, budget, structure | `campaigns/{name}/brief.md` + `structure.md` |
| `/ad-creative` | 3-angle ad copy (pain, outcome, social proof) | `campaigns/{name}/copy.md` |
| `/ab-test-setup` | A/B test plan with hypothesis and metrics | `campaigns/{name}/ab-test.md` |
| `/analytics-tracking` | Pixel, CAPI, GA4, UTM setup | `campaigns/{name}/tracking.md` |
| `/html-ad` | Generate static ad images (HTML → PNG) | `campaigns/{name}/images/` |
| `/copywriting` | Landing page and marketing copy | `campaigns/{name}/assets/` |
| `/page-cro` | Conversion rate audit (40 checks) | Scored report |
| `/content-strategy` | Topic clusters & 90-day content calendar | `research/content-strategy.md` |
| `/social-content` | Platform-specific posts and captions | Content doc |
| `/revops` | Lead scoring, CRM automation, MQL/SQL handoff | `campaigns/{name}/revops.md` |

## Campaign Management Rules

- Every campaign lives in `campaigns/{client}_{objective}_{audience}_{YYYY-MM}/`
- Naming convention: `{client}_{objective}_{audience}_{YYYY-MM}` (all lowercase, hyphens for spaces)
- Every account action must be logged in `campaigns/{name}/log.md` with timestamp
- Campaign workflow order: `/paid-ads` → `/ad-creative` → `/html-ad` → `/analytics-tracking` → `/ab-test-setup`
- Never launch a campaign without a tracking spec and UTM URLs configured
- Budget minimum: 5× target CPA per ad set per day (learning phase requirement)

## Development Rules

- Keep SKILL.md files under 500 lines / 5000 tokens
- Reference files should be focused and under 200 lines
- Scripts must have docstrings, CLI interface, and JSON output
- Follow kebab-case naming for all skill directories
- Agents invoked via Task tool with `context: fork`, never via Bash
- No hardcoded credentials; use MCP servers for external API access
