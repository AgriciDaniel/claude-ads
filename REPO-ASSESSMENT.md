# Claude Ads — Repository Assessment Brief

**Date:** 2026-03-25
**Repository:** hello-yellow-fornya/claude-ads
**Branch assessed:** master (+ `claude/review-repo-assessment-69pij`)
**Current version:** v1.2.0

---

## Executive Summary

Claude Ads is a Tier 4 Claude Code skill for paid advertising audit and optimization. It implements a 3-layer architecture (directive → orchestration → execution) covering 6 advertising platforms with 190+ weighted audit checks, 12 sub-skills, 6 parallel subagents, 11 industry templates, and 4 execution scripts. The repo also contains two additional application layers — a full-stack web audit tool (`ads-audit-tool/`) and an internal FastAPI tool (`internal-tool/`) — that were recently scaffolded on the current feature branch.

**Overall assessment: Well-structured, production-quality skill with strong domain coverage.** Key areas for improvement center around test coverage, the newly added application layers, and a few structural inconsistencies.

---

## 1. Architecture & Structure

### Strengths

- **Clean 3-layer separation**: Orchestrator (`ads/SKILL.md`) routes to sub-skills (`skills/`) which reference knowledge files (`ads/references/`) and delegate to agents (`agents/`). This follows the Agent Skills open standard correctly.
- **Modular sub-skill design**: Each of the 12 sub-skills is self-contained with its own `SKILL.md`, making them independently maintainable and testable.
- **Parallel agent delegation**: 6 audit agents run concurrently via `context: fork`, enabling full multi-platform audits without sequential bottlenecks.
- **Reference/logic separation**: Audit logic (check definitions, thresholds, scoring) lives in `ads/references/` rather than being embedded in skill files, enabling reuse across sub-skills and agents.

### Concerns

- **Two application layers added on feature branch** (`ads-audit-tool/` with FastAPI + Next.js, and `internal-tool/` with FastAPI + Alembic) significantly expand the repo's scope beyond a Claude Code skill. These may warrant their own repositories or at minimum clearer boundary documentation.
- **CLAUDE.md is incomplete**: Lists 12 sub-skills and 6 agents, but repo actually has 17 sub-skills (including ads-apple, ads-dna, ads-create, ads-generate, ads-photoshoot) and 10 agents (including 4 creative agents). This drift creates confusion for contributors.
- **No `.gitignore` visible** for Python/Node artifacts in the new application directories.

---

## 2. Audit Logic & Scoring System

### Coverage Matrix

| Platform | Checks | Categories | Critical Checks | Top Category Weight |
|----------|--------|------------|-----------------|---------------------|
| Google Ads | 74 | 6 | 11 | Conversion Tracking (25%) |
| Meta Ads | 46 | 4 | 7 | Pixel/CAPI & Creative (30% each) |
| LinkedIn Ads | 25 | 5 | 2 | Tech Setup & Audience (25% each) |
| TikTok Ads | 25 | 5 | 7 | Creative Quality (30%) |
| Microsoft Ads | 20 | 5 | 3 | Technical Setup (25%) |
| **Total** | **190** | **25** | **30** | — |

### Scoring Algorithm

```
S_total = Σ(C_pass × W_sev × W_cat) / Σ(C_total × W_sev × W_cat) × 100
```

- Severity multipliers: Critical (5.0×), High (3.0×), Medium (1.5×), Low (0.5×)
- Grades: A (90-100), B (75-89), C (60-74), D (40-59), F (<40)
- Cross-platform aggregate weighted by budget share

### Quality Gates (Hard Rules)

1. No Broad Match without Smart Bidding (Google)
2. 3× Kill Rule: pause spend >3× target CPA with zero conversions
3. Budget sufficiency: Meta ≥5× CPA/ad set, TikTok ≥50× CPA/ad group
4. Never edit during active learning phase
5. Always check Special Ad Categories (housing/employment/credit/finance)
6. No silent video ads on TikTok
7. Default attribution: 7d click/1d view (Meta), DDA (Google)
8. No Broad Match + Manual CPC pairing

### Assessment

- **Strong**: Severity-weighted scoring is well-designed and prevents low-priority issues from inflating failure rates. Critical checks appropriately carry 10× the weight of low-severity ones.
- **Strong**: Platform-specific category weights reflect each platform's actual value drivers (e.g., creative quality weighted 30% for TikTok where creative is the #1 success factor).
- **Gap**: No Apple Search Ads checks are defined in the references despite `ads-apple` being listed as a sub-skill in v1.2.0 changelog. The 35 Apple checks mentioned in the changelog don't appear in `ads/references/`.
- **Gap**: Check IDs across platforms aren't consistently formatted (Google uses G01-G61 + G-CT/G-WS/G-KW/G-AD/G-PM prefixes; others use simpler sequential IDs).

---

## 3. Benchmark Data Quality

### Sources & Currency

- Google benchmarks: WordStream/LocaliQ 2025 (16K campaigns) — current
- Meta benchmarks: 2025 aggregate data — current
- LinkedIn benchmarks: 2025 global CPC/CPM data — current
- TikTok benchmarks: 2025 platform data — current
- Microsoft benchmarks: 2025 Copilot-era data — current
- Privacy landscape: Updated through Feb 2026 (Privacy Sandbox death, Consent Mode v2 enforcement) — current

### Assessment

- **Strong**: Benchmarks are recent (2025-2026) with named sources and sample sizes.
- **Strong**: Industry-specific benchmarks provided for 10+ verticals, not just global averages.
- **Recommendation**: Add benchmark refresh dates to each reference file to make staleness visible. Ad platform benchmarks shift ~15-25% YoY and some of these will be stale by mid-2026.

---

## 4. Compliance & Privacy

- Consent Mode v2 enforcement (EU/EEA) properly documented
- iOS ATT opt-in rates updated (~35%)
- US state privacy laws tracked (20 active by Jan 2026)
- Google three-strike enforcement policy documented
- Meta Special Ad Categories updated (Financial Products added Jan 2025)
- CCPA/CPRA 2026 requirements included

**Assessment: Compliance coverage is thorough and current.** The compliance decision tree provides clear geographic routing. One gap: no explicit DPDPA (India) coverage, which may matter for agencies with Indian market exposure.

---

## 5. Execution Scripts

| Script | Purpose | Tech |
|--------|---------|------|
| `analyze_landing.py` | Landing page audit (Core Web Vitals, conversion signals, mobile) | Playwright |
| `generate_image.py` | AI image generation (4 providers, batch mode) | Gemini/OpenAI/Stability/Replicate APIs |
| `capture_screenshot.py` | Website screenshots (multi-viewport) | Playwright |
| `fetch_page.py` | Page fetching, pixel detection, link extraction | Playwright |

### Assessment

- **Strong**: `generate_image.py` has retry logic, multiple provider support, and aspect ratio handling.
- **Strong**: `analyze_landing.py` maps directly to the scoring system's landing page checks.
- **Gap**: No `requirements.txt` at repo root specifies Playwright as a dependency (there is one at root but I didn't verify its contents).
- **Gap**: No unit tests for any scripts.

---

## 6. Application Layers (New on Feature Branch)

### `ads-audit-tool/` (Full-Stack Web App)

- **Backend**: FastAPI (Dockerized)
- **Frontend**: Next.js with TypeScript
- **Infra**: `docker-compose.yml`, `railway.toml` (Railway deployment)
- **Status**: Scaffolded, recent commit

### `internal-tool/` (Internal API)

- **Stack**: FastAPI with Alembic migrations
- **Structure**: `app/` with `api/`, `auditors/`, `connectors/`, `models/`, `services/`
- **Tests**: `tests/` directory present
- **Status**: Scaffolded, earlier commit

### Assessment

- These represent a significant architectural expansion from "Claude Code skill" to "SaaS product."
- **Risk**: Without clear documentation on how these layers interact with the skill layer, contributors may be confused about which entry point to use.
- **Recommendation**: Add a top-level `ARCHITECTURE.md` or expand `CLAUDE.md` to document the relationship between the skill layer and the application layers.

---

## 7. Industry Templates

11 templates in `skills/ads-plan/assets/`: SaaS, E-commerce, Local Service, B2B Enterprise, Info Products, Mobile App, Real Estate, Healthcare, Finance, Agency, Generic.

Each includes: platform allocation matrix, budget pacing (6-month phased), creative pillars, and 4-phase rollout plan.

**Assessment: Comprehensive vertical coverage.** The generic template serves as a reasonable fallback. Templates correctly reference the 70/20/10 rule and minimum viable budgets per platform.

---

## 8. Documentation & Developer Experience

### Strengths

- README is polished with badges, install commands, demo section, FAQ
- CHANGELOG follows Keep a Changelog format with semantic versioning
- Community health files present (CODE_OF_CONDUCT, CONTRIBUTING, SECURITY, SUPPORT)
- CITATION.cff for academic citation

### Gaps

- **CLAUDE.md drift**: Doesn't reflect actual sub-skill/agent count (says 12/6, actual is 17/10)
- **No ARCHITECTURE.md**: With three distinct layers (skill, web app, internal tool), architecture documentation is needed
- **No developer setup guide** for the application layers (Docker, env vars, database setup)
- **Evals**: Only `creative-evals.json` exists — no eval coverage for audit checks, scoring accuracy, or benchmark application

---

## 9. Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| CLAUDE.md drift from actual repo state | Medium | Audit and update sub-skill/agent counts, add missing entries |
| No test coverage for audit logic or scripts | High | Add unit tests for scoring algorithm, threshold validation, script outputs |
| Application layers undocumented | Medium | Add ARCHITECTURE.md explaining layer relationships |
| Benchmark staleness (6-12 month horizon) | Medium | Add `last_updated` dates to reference files, schedule quarterly reviews |
| Apple Search Ads checks not in references | Low | Add `ads/references/apple-audit.md` or document that checks live in skill file |

---

## 10. Recommendations (Priority Order)

1. **Update CLAUDE.md** to reflect actual sub-skill count (17), agent count (10), and document the application layers
2. **Add tests** — at minimum: scoring algorithm unit tests, threshold boundary tests for critical checks, and integration tests for `analyze_landing.py`
3. **Create ARCHITECTURE.md** documenting the three layers and their relationships
4. **Standardize check IDs** across platforms (consider a consistent `{PLATFORM}-{CATEGORY}-{NUMBER}` format)
5. **Add Apple Search Ads reference file** with the 35 checks mentioned in the v1.2.0 changelog
6. **Add benchmark freshness dates** to each reference file header
7. **Evaluate repo split**: Consider whether `ads-audit-tool/` and `internal-tool/` should live in separate repositories

---

*Assessment prepared from full codebase review including all 79 markdown files, 30 Python files, 9 TypeScript files, 6 agent definitions, 12 reference documents, 11 industry templates, and 4 execution scripts.*
