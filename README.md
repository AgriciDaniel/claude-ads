<p align="center">
  <img src="assets/banner.png" alt="Claude Ads: Paid Advertising Audit Skill for Claude Code" width="100%">
</p>

# Claude Ads: Paid Advertising Audit Skill for Claude Code

Comprehensive paid advertising audit and optimization skill for Claude Code. Covers Google Ads, Meta Ads, YouTube Ads, LinkedIn Ads, TikTok Ads, Microsoft Ads, and Apple Ads with **250+ audit checks**, industry-specific templates, parallel subagent delegation, PPC financial modeling, A/B test design, and PDF report generation.

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blue)](https://claude.ai/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/github/v/release/AgriciDaniel/claude-ads)](https://github.com/AgriciDaniel/claude-ads/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/AgriciDaniel/claude-ads/ci.yml?branch=main&label=CI)](https://github.com/AgriciDaniel/claude-ads/actions)

> **Blog:** [Read the full ad audit breakdown](https://agricidaniel.com/blog/claude-code-ad-agency)

## Contents

- [Installation](#installation)
- [Demo](#demo)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [Features](#features)
- [Architecture](#architecture)
- [How It Analyzes Your Ads](#how-it-analyzes-your-ads)
- [FAQ](#faq)
- [Requirements](#requirements)
- [Uninstall](#uninstall)
- [Related Projects](#related-projects)
- [License](#license)

## Installation

### Plugin Install (Recommended)

Add the marketplace and install in Claude Code:

```shell
/plugin marketplace add agricidaniel/claude-ads
/plugin install claude-ads@agricidaniel-claude-ads
```

This registers claude-ads as a native plugin with auto-updates, namespace isolation, and proper version tracking.

> **macOS workaround:** Use lowercase `agricidaniel/claude-ads` (not `AgriciDaniel/claude-ads`). Mixed-case names trigger a rename failure on case-insensitive macOS filesystems ([#17](https://github.com/AgriciDaniel/claude-ads/issues/17)). The lowercase form works identically.

### One-Command Install (Unix/macOS/Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/AgriciDaniel/claude-ads/main/install.sh | bash
```

### One-Command Install (Windows PowerShell)

```powershell
irm https://raw.githubusercontent.com/AgriciDaniel/claude-ads/main/install.ps1 | iex
```

### Manual Install

```bash
git clone https://github.com/AgriciDaniel/claude-ads.git
cd claude-ads
./install.sh          # Unix/macOS/Linux
```

```powershell
.\install.ps1         # Windows PowerShell
```

<p align="center">
  <img src="assets/diagrams/20-install-methods.svg" alt="Installation Methods Comparison" width="100%">
</p>

## Demo

<p align="center">
  <img src="assets/demo.gif" alt="Claude Ads Demo" width="100%">
</p>

## Quick Start

```bash
# Start Claude Code
claude

# Run a full multi-platform audit
/ads audit

# Deep analysis for a single platform
/ads google
/ads meta
/ads linkedin

# Strategic planning by business type
/ads plan saas
/ads plan ecommerce
/ads plan local-service

# Cross-platform creative audit
/ads creative

# Budget and bidding strategy review
/ads budget
```

<p align="center">
  <img src="assets/diagrams/06-how-it-works.svg" alt="How It Works: 5-Step Process" width="100%">
</p>

## Commands

| Command | Description |
|---------|-------------|
| `/ads audit` | Full multi-platform audit with parallel subagent delegation |
| `/ads google` | Google Ads deep analysis (Search, PMax, Display, YouTube, Demand Gen) |
| `/ads meta` | Meta Ads deep analysis (FB, IG, Advantage+ Shopping) |
| `/ads youtube` | YouTube Ads specific analysis (Skippable, Shorts, Demand Gen) |
| `/ads linkedin` | LinkedIn Ads deep analysis (B2B, Lead Gen, TLA) |
| `/ads tiktok` | TikTok Ads deep analysis (Creative, Shop, Smart+) |
| `/ads microsoft` | Microsoft/Bing Ads deep analysis (Copilot, Import validation) |
| `/ads creative` | Cross-platform creative quality audit and fatigue detection |
| `/ads landing` | Landing page quality assessment for ad campaigns |
| `/ads budget` | Budget allocation and bidding strategy review |
| `/ads apple` | Apple Ads deep analysis (campaign structure, bids, CPPs, Maximize Conversions, TAP) |
| `/ads plan <type>` | Strategic ad plan with industry templates |
| `/ads competitor` | Competitor ad intelligence across all platforms |
| `/ads math` | PPC financial calculator (CPA, ROAS, break-even, budget forecasting, LTV:CAC) |
| `/ads test` | A/B test design (hypothesis framework, significance, sample size, duration) |
| `/ads report` | Generate PDF audit report for client deliverables |

### `/ads audit`
**Full Multi-Platform Audit**

Spawns 6 parallel subagents to analyze your ad accounts simultaneously:
- **audit-google**: 80 checks across Search, PMax, AI Max, Demand Gen, CTV, YouTube
- **audit-meta**: 50 checks across Pixel/CAPI, Andromeda creative diversity, Structure, Audience
- **audit-creative**: 21+ cross-platform creative quality checks with Andromeda and Symphony awareness
- **audit-tracking**: 8+ conversion tracking and privacy infrastructure checks (Consent Mode V2, CAPI, Events API, AdAttributionKit)
- **audit-budget**: 24 budget and bidding strategy checks
- **audit-compliance**: 18+ compliance checks (ECPC deprecated, VAC deprecated, EU messaging, Apple rebrand)

Generates a unified **Ads Health Score (0-100)** with prioritized action plan.

<p align="center">
  <img src="assets/diagrams/02-parallel-audit.svg" alt="Parallel Audit Pipeline" width="100%">
</p>

<p align="center">
  <img src="assets/diagrams/19-audit-lifecycle.svg" alt="Audit Lifecycle" width="100%">
</p>

### `/ads plan <business-type>`
**Strategic Ad Planning**

Industry-specific templates with platform mix, campaign architecture, creative strategy, targeting, budget guidelines, and KPI targets.

**Supported business types:**
- `saas`: Trial/demo focus, Google + LinkedIn primary
- `ecommerce`: Shopping/PMax, ROAS-focused, seasonal
- `local-service`: Google Search + LSA, call tracking, geo radius
- `b2b-enterprise`: LinkedIn ABM, long sales cycle, pipeline metrics
- `info-products`: Meta + YouTube, webinar/VSL funnels
- `mobile-app`: Meta + Google UAC, MMP required, LTV:CPI
- `real-estate`: Special Ad Category (housing), buyer/seller campaigns
- `healthcare`: HIPAA compliance, LegitScript, restricted targeting
- `finance`: Special Ad Category (credit), required disclosures
- `agency`: Multi-client management, reporting framework
- `generic`: Universal template with platform selection questionnaire

<p align="center">
  <img src="assets/diagrams/08-industry-templates.svg" alt="Industry Templates" width="100%">
</p>

### `/ads math` and `/ads test`

<p align="center">
  <img src="assets/diagrams/18-ppc-calculators.svg" alt="PPC Calculators" width="48%">
  <img src="assets/diagrams/17-ab-testing.svg" alt="A/B Test Design" width="48%">
</p>

### `/ads report`

Generate professional PDF audit reports for client deliverables with health score gauge, platform comparison charts, pass/fail distribution, formatted tables, and zero-overlap layout.

<p align="center">
  <img src="assets/diagrams/16-pdf-pipeline.svg" alt="PDF Report Pipeline" width="100%">
</p>

## Features

### 250+ Audit Checks
Comprehensive coverage across all platforms with weighted severity scoring:

| Platform | Checks | Key Areas |
|----------|--------|-----------|
| Google Ads | 80 | Search, PMax, AI Max, Demand Gen, CTV, YouTube |
| Meta Ads | 50 | Pixel/CAPI, Andromeda creative diversity, Structure, Audience |
| LinkedIn Ads | 27 | B2B targeting, TLA, Lead Gen, CRM integration |
| TikTok Ads | 28 | Creative-first, Smart+, GMV Max, Search Ads, Events API |
| Microsoft Ads | 24 | Google import safety, Copilot, CTV, LinkedIn targeting, video |
| Apple Ads | 35+ | Campaign structure, CPPs, Maximize Conversions, AdAttributionKit |
| Cross-platform | 3 | Privacy infrastructure, creative diversity, refresh cadence |

<p align="center">
  <img src="assets/diagrams/15-platform-grid.svg" alt="Platform Coverage Grid" width="100%">
</p>

<p align="center">
  <img src="assets/diagrams/04-platform-checks.svg" alt="Platform Check Distribution" width="100%">
</p>

### Ads Health Score (0-100)
Weighted scoring algorithm with severity multipliers:

| Grade | Score | Action Required |
|-------|-------|-----------------|
| A | 90-100 | Minor optimizations only |
| B | 75-89 | Some improvement opportunities |
| C | 60-74 | Notable issues need attention |
| D | 40-59 | Significant problems present |
| F | <40 | Urgent intervention required |

<p align="center">
  <img src="assets/diagrams/13-scoring-algorithm.svg" alt="Scoring Algorithm" width="100%">
</p>

### Industry Detection
Auto-detects business type from ad account signals (product feeds, conversion events, platform mix, targeting patterns) and loads industry-specific benchmarks and templates.

### Quality Gates
Hard rules enforced during every audit:
- Never recommend Broad Match without Smart Bidding (Google)
- 3x Kill Rule: flag CPA >3x target for immediate pause
- Budget sufficiency: Meta >=5x CPA/ad set, TikTok >=50x CPA/ad group
- Learning phase protection: no edits during active learning
- Compliance: auto-check Special Ad Categories (housing/credit/finance)
- **Privacy infrastructure gate**: verify tracking stack (Consent Mode V2, CAPI, Events API, AdAttributionKit) before optimization recommendations
- **Andromeda creative diversity**: flag Meta accounts with <10 genuinely distinct creatives

<p align="center">
  <img src="assets/diagrams/05-quality-gates.svg" alt="Quality Gates" width="100%">
</p>

### Creative Pipeline

AI-powered creative generation with 4 specialized agents:

<p align="center">
  <img src="assets/diagrams/14-creative-pipeline.svg" alt="Creative Pipeline" width="100%">
</p>

### Reference Data
25 built-in reference files with 2026-current benchmarks, bidding decision trees, platform specifications, compliance requirements, conversion tracking guides, MCP integration guide, and additional platform coverage.

### Data Handling & Privacy
Claude Ads runs entirely on your local machine via Claude Code. No ad account data is sent to external servers. When using MCP servers for live API access, data flows directly between your machine and the ad platform APIs. All analysis happens locally.

<p align="center">
  <img src="assets/diagrams/12-privacy-flow.svg" alt="Privacy and Data Flow" width="100%">
</p>

## Architecture

<p align="center">
  <img src="assets/diagrams/01-architecture.svg" alt="3-Layer Architecture" width="100%">
</p>

```
~/.claude/skills/ads/              # Main orchestrator
~/.claude/skills/ads/references/   # 25 RAG reference files
~/.claude/skills/ads-*/            # 19 sub-skills (17 original + ads-math + ads-test)
~/.claude/skills/ads-plan/assets/  # 12 industry templates
~/.claude/agents/                  # 10 agents (6 audit + 4 creative)
```

### How It Works

1. **Orchestrator** (`/ads`) routes commands to specialized sub-skills
2. **Sub-skills** provide deep single-domain analysis with structured output
3. **Agents** run in parallel during full audits for maximum speed
4. **References** load on-demand (RAG pattern); only what's needed per analysis
5. **Templates** provide industry-specific strategy frameworks

## How It Analyzes Your Ads

**Claude Ads works with data you provide**; exports, screenshots, or pasted metrics from your ad platform dashboards. It does not connect to any ad platform API automatically.

**To get accurate, account-specific recommendations:**
1. Export your account data (last 30 days recommended)
2. Run the relevant command: `/ads google`, `/ads audit`, etc.
3. Claude will ask for your industry and budget context first; provide these for relevant benchmarks
4. Paste or share your data when prompted

<p align="center">
  <img src="assets/diagrams/07-data-flow.svg" alt="Data Flow" width="100%">
</p>

### Live Data Integration (Optional)

For direct API access without manual exports, pair Claude Ads with MCP servers. See `ads/references/mcp-integration.md` for setup guides:
- **Google Ads**: [mcp-google-ads](https://github.com/cohnen/mcp-google-ads): 29 GAQL tools for live API access
- **Meta Ads**: [Adspirer MCP](https://www.adspirer.com) or use included `scripts/fetch_meta_ads.py`
- **LinkedIn Ads**: [GrowthSpree MCP](https://www.growthspreeofficial.com) or [Adzviser MCP](https://adzviser.com)

<p align="center">
  <img src="assets/diagrams/10-mcp-integration.svg" alt="MCP Integration" width="100%">
</p>

## FAQ

**Can Claude Ads log into my ad manager automatically?**
No. Claude Ads analyzes data you provide (exports, screenshots, or pasted metrics). It doesn't connect to ad platforms automatically. See the Live Data Integration section above for Google Ads API access via MCP.

**Does it use real account data or generic benchmarks?**
Benchmarks are based on industry research (WordStream, Triple Whale, etc.) covering 16,000+ campaigns. They're averages; your results will vary by industry, budget level, and account maturity. Always provide your industry and monthly spend when running audits for the most relevant comparisons.

**Is ad posting or campaign creation still manual?**
Yes. Claude Ads is an audit and strategy tool. It finds issues, recommends fixes, and builds campaign plans; but creating, editing, or posting ads remains manual in your ad platform.

**Why do some recommendations seem off for my account size?**
Benchmarks and best practices differ significantly between a $500/month account and a $50k/month account. Always tell Claude your budget upfront: *"I spend $2k/month on Google Ads for a local plumbing business"* gives much better results than running `/ads google` without context.

**Does it support [platform] ads?**
Currently supported: Google, Meta (Facebook/Instagram), YouTube, LinkedIn, TikTok, Microsoft/Bing, and Apple Ads. Additional platforms (Reddit, CTV/OTT, Pinterest, Snapchat) are covered in the reference guide for strategic planning.

## Requirements

- Claude Code CLI
- Python 3.10+ with Playwright (optional, for live landing page analysis)
- reportlab (optional, for PDF report generation via `/ads report`)

## Uninstall

### Unix/macOS/Linux

```bash
curl -fsSL https://raw.githubusercontent.com/AgriciDaniel/claude-ads/main/uninstall.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/AgriciDaniel/claude-ads/main/uninstall.ps1 | iex
```

## Related Projects

- [Claude SEO](https://github.com/AgriciDaniel/claude-seo); Comprehensive SEO analysis skill for Claude Code

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built for Claude Code by [@AgriciDaniel](https://github.com/AgriciDaniel)

---

## Author

Built by [Agrici Daniel](https://agricidaniel.com/about) - AI Workflow Architect.

- [Blog](https://agricidaniel.com/blog) - Deep dives on AI marketing automation
- [AI Marketing Hub](https://www.skool.com/ai-marketing-hub) - Free community, 2,800+ members
- [YouTube](https://www.youtube.com/@AgriciDaniel) - Tutorials and demos
- [All open-source tools](https://github.com/AgriciDaniel)
