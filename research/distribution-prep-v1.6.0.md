# Distribution Prep — v1.6.0 (Wave 1)

Track-only. Ready-to-submit copy for the three distribution channels surfaced by
the research doc. Submit when v1.6.0 is tagged and ready for public traffic. Do
not submit before the user explicitly says ship.

---

## 1. GitHub Repo Metadata (apply on the GitHub side, no PR needed)

### Repo Description (About field — max 350 chars)

> Comprehensive paid-advertising audit & optimization skill for Claude Code, Codex, and Cursor. 250+ checks across Google, Meta, YouTube, LinkedIn, TikTok, Microsoft & Apple Ads. 19 sub-skills, 10 parallel agents, 12 industry templates, PPC math, A/B test design, PDF reports. 0-100 Ads Health Score. MIT licensed.

(347 chars — fits inside GitHub's 350-char ceiling.)

### Repo Topics (15 — paste into the GitHub Topics field)

```
claude-code, claude-skill, agent-skills, paid-advertising, google-ads, meta-ads, linkedin-ads, tiktok-ads, ppc, ads-audit, marketing-automation, ai-agents, anthropic, codex, cursor
```

### Website Field

`https://agricidaniel.com/blog/claude-code-ad-agency`

---

## 2. claudemarketplaces.com Submission

`claudemarketplaces.com` is a directory + voting system for Claude skills with
~160K monthly visitors (self-reported). Listed in the Marketing & SEO category.

**Submission text:**

> **Claude Ads — Paid Advertising Audit & Optimization Skill**
>
> Comprehensive 7-platform paid-ads audit skill with 250+ weighted checks across
> Google Ads (80), Meta Ads (50), LinkedIn Ads (27), TikTok Ads (28), Microsoft
> Ads (24), Apple Ads, and YouTube Ads. Runs 6 audit agents in parallel and
> produces a 0-100 Ads Health Score plus prioritized action plan.
>
> Includes 19 sub-skills (audit, creative, landing, budget, plan, math, A/B
> test, competitor, brand DNA, generate, photoshoot), 12 industry templates
> (SaaS, e-commerce, B2B, local-service, healthcare, finance, info-products,
> mobile-app, real-estate, agency, generic, gaming), client-ready PDF report
> generation, and AI creative-image production via banana-claude.
>
> Tested with Claude Code v2.x. MIT licensed. Security-hardened (v1.5.1: SSRF
> protection, error sanitization, SHA-pinned CI, dependabot patch-only auto-
> merge). v1.6.0 adds tested-date frontmatter on all 20 SKILL.md files and
> Andromeda/AI Max-aware trigger surface expansion.
>
> Install: `/plugin marketplace add AgriciDaniel/claude-ads`
>
> Repo: https://github.com/AgriciDaniel/claude-ads
> Demo: https://agricidaniel.com/blog/claude-code-ad-agency

**Category:** Marketing & SEO
**Tags:** paid-advertising, ppc, google-ads, meta-ads, linkedin-ads, tiktok-ads, audit, claude-code

---

## 3. awesome-claude-code PR

`awesome-claude-code` is the community-curated list of Claude Code resources.
Submit a PR adding claude-ads under an appropriate section.

**Suggested entry (paste into the README list, sorted alphabetically):**

```markdown
- [claude-ads](https://github.com/AgriciDaniel/claude-ads) — Comprehensive paid-advertising audit skill covering Google, Meta, YouTube, LinkedIn, TikTok, Microsoft & Apple Ads with 250+ weighted checks, parallel audit agents, industry templates, and PDF report generation. MIT licensed.
```

**Section to place under:** Marketing / Advertising / Business (depending on
the repo's current taxonomy).

**PR title:** `Add claude-ads — paid-advertising audit skill`

**PR body:**

```
Adds [claude-ads](https://github.com/AgriciDaniel/claude-ads) to the list — a
production-grade paid-advertising audit and optimization skill for Claude Code.

Brief: 7 platforms covered, 250+ checks, 19 sub-skills, 10 parallel agents,
client-ready PDF reports. v1.5.1 shipped security hardening (90/100 score);
v1.6.0 added cross-runtime metadata and Andromeda/AI Max-era trigger surface.

Adheres to the agentskills.io v0.9 spec (progressive disclosure, on-demand
references, deterministic Python scripts for math + URL validation).

MIT licensed. SECURITY.md + CONTRIBUTING.md + CODE_OF_CONDUCT.md + CHANGELOG.md
all present and current.
```

---

## 4. anthropics/skills inclusion request

The official Anthropic skills repo accepts community skills via issues. File
under "I want to feature this skill" or whatever the current taxonomy is.

**Issue title:** `Feature request: Add claude-ads to community skills directory`

**Issue body:**

```
**Skill:** claude-ads
**Repo:** https://github.com/AgriciDaniel/claude-ads
**Category:** Marketing / Paid Advertising
**License:** MIT
**Maintainer:** @AgriciDaniel

**What it does:**
Paid-advertising audit skill covering Google, Meta, YouTube, LinkedIn, TikTok,
Microsoft, and Apple Ads with 250+ weighted checks across 7 platforms. Runs 6
audit agents in parallel and outputs a 0-100 health score plus prioritized
action plan and optional PDF report.

**Why it might fit the directory:**
- Adheres to the Agent Skills spec (progressive disclosure, on-demand
  references, deterministic Python scripts where appropriate).
- Production-ready: 5 release tags, v1.5.1 security-hardened (SSRF protection,
  SHA-pinned CI, error sanitization, dependabot patch-only auto-merge).
- 19 sub-skills + 10 agents + 12 industry templates + 25 reference docs.
- Real-world utility: turns Claude Code into an agency-grade audit tool.
- Cross-runtime portable: Wave 2 will ship --target=<host> install for Codex CLI,
  Cursor, Windsurf, Gemini CLI, Goose.

Happy to address any feedback or follow specific submission guidelines.
```

---

## 5. Portfolio-Positioning One-Liner (cross-channel)

> Claude Ads is the only open-source agent-skill that runs 6 parallel audit
> agents across 7 ad platforms with 250+ weighted checks and ships client-ready
> PDF deliverables — every competing skill is a single-platform prompt wrapper.

Use this in:
- Twitter/X launch thread
- LinkedIn post
- Reddit r/ClaudeAI / r/PPC announcements
- HN Show
- Skool community announcement

---

## 6. Pre-Submission Checklist

Run through before submitting any of the above:

- [ ] v1.6.0 tagged + release notes attached on GitHub
- [ ] README claims (250+ checks, 7 platforms, 19 sub-skills, 10 agents) match reality
- [ ] CI green on main
- [ ] Demo GIF still works
- [ ] No new HIGH/CRITICAL security findings
- [ ] CONTRIBUTING.md + SECURITY.md + CODEOWNERS in place
- [ ] LICENSE year current
- [ ] Repo About field + topics set on the GitHub side
- [ ] Skool, blog, YouTube CTAs in README still active
- [ ] User has explicitly approved going public (no premature submission)

---

## 7. Out of Scope This Wave

- Hosted-MCP paid tier (separate strategic decision; track `cognyai` competitor moves monthly)
- ProductHunt launch (defer until cross-runtime ships in v1.7.0)
- Press / blog outreach (defer until v1.7.0 retail-media + CTV coverage lands)
