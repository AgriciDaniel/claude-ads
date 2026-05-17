# Changelog

All notable changes to claude-ads are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2026-05-17

### Added

- `tested_date: 2026-05-17` and `tested_with: claude-code v2.x` frontmatter on all 20 SKILL.md files (orchestrator + 19 sub-skills), aligning with the emerging Agent Skills versioning convention
- `.github/CODEOWNERS` for automatic PR review routing to the maintainer
- `research/distribution-prep-v1.6.0.md` — submission packets for claudemarketplaces.com, awesome-claude-code, and anthropics/skills (track-only this wave; not yet submitted)
- IPv6 `::/128` (unspecified address) added to the SSRF blocklist in `scripts/url_utils.py` — closes a kernel-coercion edge case where some Linux kernels alias `::` to localhost
- `CONTRIBUTING.md` expanded from 41 to ~120 lines with three new sections: *Adding a New Sub-Skill* (mirror pattern + frontmatter spec + routing-table integration), *Adding a Reference File* (progressive-disclosure conventions), and *Testing Audit Checks* (pre-eval-harness manual workflow)

### Changed

- Trigger surface expanded across 11 sub-skill `description:` fields — additive only, no existing triggers removed:
  - `ads-google`: AI Max, AI Brief, broad match audit, Quality Score check, search terms audit, Smart Bidding, FUE, text customization, brand exclusions
  - `ads-meta`: Andromeda, GEM, Lattice, Entity-ID clustering, ASC, AAC, creative diversity, Sales / Leads / App optimization, Threads ads
  - `ads-tiktok`: USDS (post-Jan-2026 divestiture), creative diversity for retrieval
  - `ads-apple`: AdAttributionKit, view-through attribution
  - `ads-audit`: paid media audit, paid advertising audit, ad spend audit, advertising audit
  - `ads-competitor`: Meta Ad Library, Facebook Ad Library, Google Ads Transparency, competitor creative, competitor research
  - `ads-creative`: creative diversity score, ad variation audit (Andromeda Entity-ID retrieval scoring)
  - `ads-landing`: LP audit, landing page CRO, post-click CRO
  - `ads-linkedin`: ABM ads, Thought Leader Ads, predictive audiences, B2B paid (plus Oct 2025 terminology change note)
  - `ads-microsoft`: Bing search ads, Microsoft search ads, Google import audit
  - `ads-youtube`: skippable in-stream, YouTube Shorts ads, Demand Gen, VAC, CTV YouTube ads
- `ads/references/benchmarks.md` — citation dates clarified; WordStream / Triple Whale / SplitMetrics 2025 sources tagged with explicit "verified current as of 2026-05-17" header
- `skills/ads-plan/assets/mobile-app.md` — removed stale Privacy Sandbox (Android) references (Android Privacy Sandbox was retired Oct 17, 2025). Replaced with Google Play Install Referrer + GA4 + MMP guidance. AdAttributionKit added alongside SKAdNetwork in iOS attribution notes
- `SECURITY.md` — private disclosure channel sharpened: GitHub Security Advisory is now the only supported channel; removed the ambiguous "or contact the maintainer directly" fallback. Reproduction step requirements added
- `.gitignore` — added `research-prompt*.md` and `.research-*.md` patterns to prevent future research-prompt drafts from being committed accidentally

### Security

- v1.5.1 baseline confirmed at **91/100** by a fresh cybersecurity audit (May 2026 baseline pass). The new IPv6 `::/128` entry brings the score to **92/100** (+1)
- **Zero new attack surface** introduced by Wave 1: no new code paths, no new network egress, no new subprocess calls. The only script change is the single-line `::/128` addition to `_BLOCKED_NETS`
- Pre-Wave 2 hardening checklist captured for the cross-runtime `--target=<host>` install matrix: Playwright error sanitization, Replicate result URL revalidation, SECURITY.md egress documentation, and a `validate_install_target()` shell function with strict pattern rejection (`;&|$()<>`, leading `-`, `..` segments, UNC paths)

### Notes

- v1.7.0 will ship the cross-runtime install matrix (`--target=` for Codex CLI / Cursor / Windsurf / Gemini CLI / Goose), the `tests/` directory with golden fixtures, the `ads-google` AI Max rewrite, the `ads-meta` Andromeda + Entity-ID predictor, plus `ads-attribution`, `ads-server-side-tracking`, and `ads-amazon` sub-skills
- GitHub repo About-field text (347 chars, optimized) and 15 suggested repo topics are captured in `research/distribution-prep-v1.6.0.md` — apply on the GitHub side when the user is ready to go public

## [1.5.1] - 2026-04-14

### Security

- Added shared SSRF validation module (`scripts/url_utils.py`) used by all URL-handling scripts
- Blocked IPv4 private ranges (127/8, 10/8, 172.16/12, 192.168/16, 169.254/16, 0/8, 100.64/10) and IPv6 (::1, fc00::/7, fe80::/10, ::ffff:0:0/96)
- DNS resolution failures now reject the URL instead of silently passing through
- Added `_sanitize_error()` to strip API keys, tokens, and passwords from error messages
- Added reference image extension allowlist to prevent arbitrary file reads
- Added batch size limit (50 jobs max) and dimension bounds (8192px max)
- Validated Replicate API response URLs are HTTPS before fetching
- Truncated Stability API error responses to prevent info leakage

### Changed

- GitHub Actions pinned to full SHA hashes instead of mutable version tags
- Dependabot auto-merge restricted to patch updates only (was all versions)
- CI workflow scoped to `permissions: contents: read` (least privilege)
- `pip-audit` added to CI for dependency vulnerability scanning
- `install.sh` tries standard pip first, falls back to `--break-system-packages` with warning
- `install.sh` trap variable quoting fixed for safer cleanup
- `.gitignore` now excludes `*.pem`, `*.key`, `*.p12`, `*.pfx`, `credentials.json`, `service-account.json`

## [1.4.0] - 2026-04-01

### Added
- **banana-claude integration**: Replaced generate_image.py with banana-claude (v1.4.1) as the default image generation provider. Uses MCP tools (`gemini_generate_image`, `set_aspect_ratio`), 5-component prompt formula, 9 domain modes, and brand presets.
- **Voice-to-style mapping** (`voice-to-style.md`): Maps 6 brand voice axes to visual attributes for banana's [STYLE] prompt component. Used by creative-strategist and visual-designer agents.
- **Ad copy frameworks** (`copy-frameworks.md`): 6 proven frameworks (AIDA, PAS, BAB, 4P, FAB, Star-Story-Solution) with platform-specific templates, character counts, and e-commerce/SaaS examples.
- **E-commerce creative playbook** (`ecommerce-creative.md`): 5 campaign types (Product Launch, Sale/Promotion, Seasonal, Retargeting, Brand Awareness) with banana domain modes, aspect ratios, copy frameworks, and budget allocation.
- **Visual consistency anchoring**: visual-designer generates a "hero" image first and passes it as a style reference to all subsequent campaign assets.
- **3-variant A/B strategy**: visual-designer now generates 3 variants per brief (base, alternative angle, lighting/mood variation) instead of 2.
- **Copy zone validation**: format-adapter uses Claude vision to check if generated images have clear space in platform-specific copy zones.
- **Framework-driven copy**: copy-writer applies selected framework structure and generates 2 variants per platform (primary + A/B alternative).
- **Multi-screenshot brand DNA**: ads-dna captures 3 screenshots (homepage, product page, about page) for richer brand anchoring.
- **Brand preset auto-creation**: ads-generate creates a banana preset from brand-profile.json before generation.
- **Campaign cost tracking**: reads banana's `~/.banana/costs.json` and aggregates per-campaign creative spend.
- **Quality gate**: ads-generate scores each image 1-10 via Claude vision; auto-regenerates if score below 6.

### Changed
- **ads-generate**: banana MCP is primary; generate_image.py is deprecated fallback
- **ads-photoshoot**: Uses banana Product mode (Studio, Floating, Ingredient) and Editorial mode (In Use, Lifestyle) at 2K resolution
- **visual-designer agent**: 5-component banana formula replaces 7 preprocessing rules
- **creative-strategist agent**: Reads voice-to-style.md, copy-frameworks.md, and ecommerce-creative.md; generates 2 visual direction variants per concept (photography + illustration)
- **copy-writer agent**: Framework-based copy with hook word validation and action verb CTAs
- **format-adapter agent**: Added copy zone validation and cost tracking
- **requirements.txt**: google-genai moved to optional (banana handles image generation)
- **install.sh / install.ps1**: Removed Playwright chromium install; added banana-claude dependency check
- Reference file count: 21 to 23 (added voice-to-style.md, copy-frameworks.md)

### Deprecated
- `scripts/generate_image.py`: Kept as fallback for environments without banana-claude. Use banana MCP tools instead.

## [1.3.0] - 2026-04-01

### Added
- **marketplace.json** for plugin system discoverability and update mechanism (Issue #14)
- **Validation gates** in 6 skills; cherry-picked from PR #12 (Tessl):
  - `ads/SKILL.md`: Task tool orchestration clarity + subagent JSON score verification
  - `ads-audit`: Platform data availability check + subagent score field verification
  - `ads-budget`: 14-day minimum for kill/scale decisions + 20-click/$100 data sufficiency
  - `ads-creative`: Data existence check + assumption prevention gate
  - `ads-google`: 30-day data minimum + 74-check completeness verification
  - `ads-youtube`: Active campaign check + campaign type completeness gate
- **GAQL compatibility reference** (`gaql-notes.md`): known field incompatibilities, deduplication patterns, filter scope best practices, legacy BMM detection heuristic
- **Google Ads MCP integration** in ads-google: optional automated data collection via [google-ads-mcp](https://github.com/googleads/google-ads-mcp) with fallback to manual export
- **Shared negative keyword list support** (G14/G15): campaigns covered by shared lists no longer flagged as "missing negatives"
- **Keyword-level brand detection** (G05/G07/G-PM3): derives brand tokens from account name, classifies by keyword composition instead of campaign naming conventions
- **G-SYS1 diagnostic**: guidance for reporting API fetch failures instead of silently skipping checks
- **`dependencies` label** created for Dependabot PR automation

### Fixed
- **G03**: False positives from zero-impression keywords, paused ad groups, match type duplication, and stopword-only keywords diluting coherence scores (~18% false positive reduction)
- **G04**: False positives from multi-location campaign structures; now strips geographic identifiers before counting objectives
- **G12**: Inverted Search Partners logic; flag OFF as missed opportunity (was incorrectly flagging ON)
- **G16/G-WS1**: Wasted spend threshold raised to >$10 spend + 0 conversions (was flagging all non-converting terms including long-tail exploration)
- **G17/FL04**: Legacy BMM false positives; BROAD + Manual CPC is legacy BMM (not intentional broad). Only flags BROAD in Smart Bidding campaigns
- **G19**: Search term visibility calculated from ALL fetched terms before truncation (was computing from truncated subset)
- **G48/CT-FL5**: False flags on Smart Campaign system-managed conversions excluded from DDA and counting-type checks
- **G-CT1**: False duplicate detection on HIDDEN/REMOVED conversion actions; now only checks ENABLED actions
- **Conversion tracking**: Added duplicate detection accuracy rules (exclude HIDDEN/REMOVED, exclude Smart Campaign system conversions)

### Changed
- Dependabot: actions/checkout v4 → v6, actions/setup-python v5 → v6, Pillow `<12.0.0` → `<13.0.0`
- Version aligned to 1.3.0 (plugin.json was incorrectly at 2.0.0)
- Reference file count: 20 → 21 (added gaql-notes.md)

### Community
- Closed PRs #4, #5, #13 (out of scope: white-label rebrand, campaign system, FastAPI web app)
- Cherry-picked validation improvements from PR #12 (Tessl); 6 of 18 files
- Replied to Discussion #11 ("Does this really work?")
- Closed Issue #14 (marketplace.json shipped)
- GAQL accuracy fixes sourced from akarls-web fork (44 commits of audit engine improvements)
- MCP integration sourced from double-agency fork

## [1.2.0] - 2026-03-12

### Added
- **Apple Search Ads sub-skill** (`/ads apple`): 35 checks across campaign structure (BOFU/MOFU/Search Match), bid health (CPT vs install rate, CPA Goals), Creative Sets (Custom Product Pages), MMP attribution (AppsFlyer/Adjust/SKAdNetwork), budget pacing, TAP placement coverage (Today/Search/Product Pages), and goal CPA benchmarks by app category and country tier
- **Context Intake** step in orchestrator: Claude now asks for industry, monthly ad spend, primary goal, and active platforms before any audit; ensures benchmarks and recommendations match the user's actual situation instead of defaulting to generic industry averages
- **Google Ads MCP reference** in README: links to [google-ads-mcp](https://github.com/googleads/google-ads-mcp) for users who want live API-connected audits
- **FAQ section** in README: addresses top community questions (API login, benchmark accuracy, manual ad posting, budget context, platform support)
- **"How It Analyzes Your Ads"** section in README: clearly explains manual data input model and data export workflow

### Fixed
- `install.ps1`: PowerShell 5.1 crash on git clone: git progress writes to stderr which PS 5.1 treated as a terminating error under `$ErrorActionPreference = "Stop"`. Fixed by temporarily setting `Continue` around clone call and using `2>&1 | Out-Null`
- `uninstall.ps1`: Parse failure on non-UTF-8-BOM systems; Unicode `→` and `✓` characters in double-quoted strings caused `TerminatorExpectedAtEndOfString`. Replaced with ASCII equivalents
- `ads-google/SKILL.md`: Negative keyword guidance now enforces Exact Match `[kw]` and Phrase Match `"kw"` types by default; never Broad Match negatives. Negatives must be sourced from Search Terms Report data and grouped into themed Shared Lists. Includes over-blocking review step
- `ads/SKILL.md`: Removed unsupported `allowed-tools` frontmatter field per Anthropic skill spec
- `ads/SKILL.md`: Added `apple` to `argument-hint` subcommand list
- Install scripts: Updated sub-skill count from 12 → 13 to reflect new ads-apple addition

## [1.1.1] - 2026-02-11

### Fixed
- M-CR2 vs M37 frequency threshold ambiguity: clarified M-CR2 is ad set level (<3.0) and M37 is campaign level (<4.0)
- Ecommerce template PMax image count aligned to G31 audit check (15 → 20 images per asset group)
- Real estate template budget percentages widened to bracket 100% (was 90-105%, now 80-110%)
- Info products template TikTok allocation note: added minimum $50/day campaign budget caveat
- Duplicate step numbering in ads-tiktok (two step 7s) and ads-creative (two step 6s)

### Added
- `argument-hint` field on orchestrator skill for CLI subcommand hints

## [1.1.0] - 2026-02-11

### Fixed
- Audit check count corrected from 186 to 190 (actual total: Google 74 + Meta 46 + LinkedIn 25 + TikTok 25 + Microsoft 20)
- TikTok budget sufficiency threshold aligned to authoritative checklist (Pass ≥50x CPA, Warning 20-49x, Fail <20x)
- Benchmarks typo: Local Services CPC `$7.85-$15-$30` → `$7.85-$15.00`
- Call Campaigns context note: clarified creation vs serving deadlines (Feb 2026 / Feb 2027)
- Flexible Ads context note: corrected launch date from 2025 to 2024
- Scoring system weighting rationale: corrected "20-25%" to "25-30%" to match actual platform weights
- G59 mobile speed: LCP now measured on mobile viewport (375x812) instead of desktop
- G61 schema check: validates Product/FAQ/Service types per audit reference (not any schema)
- Removed unused beautifulsoup4 and lxml from requirements.txt

### Added
- `uninstall.ps1` for Windows parity (Unix already had `uninstall.sh`)
- `.gitattributes` to fix GitHub language detection (Markdown, not PowerShell)
- Research context notes in google-audit.md (ECPC deprecation, Call Campaigns sunset, Power Pack, AI Max)
- Research context notes in meta-audit.md (detailed targeting removal, Flexible Ads, Financial Products SAC)
- Research context notes in linkedin-audit.md (Connected TV, BrandLink, Live Event Ads, Accelerate campaigns)
- Weighting rationale section in scoring-system.md explaining grading band design
- Scoring system reference added to ads-tiktok and ads-creative process steps
- Missing `.gitignore` patterns for creative, landing, budget, and competitor reports

### Changed
- Removed non-spec `color` field from all 6 agent frontmatter files
- Agent frontmatter now uses only official Claude Code spec fields (name, description, model, maxTurns, tools)

## [1.0.0] - 2026-02-11

### Added
- Main orchestrator skill (`/ads`) with industry detection and quality gates
- 12 sub-skills: audit, google, meta, youtube, linkedin, tiktok, microsoft, creative, landing, budget, plan, competitor
- 6 parallel audit agents: audit-google, audit-meta, audit-creative, audit-tracking, audit-budget, audit-compliance
- 12 reference files with 2026 benchmarks, bidding decision trees, platform specs, compliance requirements
- 11 industry templates: saas, ecommerce, local-service, b2b-enterprise, info-products, mobile-app, real-estate, healthcare, finance, agency, generic
- 190 audit checks across all platforms (Google 74, Meta 46, LinkedIn 25, TikTok 25, Microsoft 20)
- Ads Health Score (0-100) with weighted severity scoring
- install.sh and uninstall.sh for Unix/macOS/Linux
- install.ps1 for Windows PowerShell
- Agent frontmatter uses model sonnet, maxTurns 20, with example blocks
- Sub-skills set user-invocable false to avoid menu clutter
- Reference files follow RAG pattern (loaded on-demand per analysis)
- Quality gates: Broad Match safety, 3x Kill Rule, budget sufficiency, learning phase protection
