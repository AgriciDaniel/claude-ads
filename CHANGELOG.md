# Changelog

All notable changes to claude-ads are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

* **Evidence and ecosystem review**: reconciled the load-bearing claim set
  against current primary sources, corrected an unreachable repository evidence
  SHA, qualified Google conversion-goal bidding exceptions, and refreshed the
  supported Meta architecture claims through August 2026. An unsupported numeric
  consent-mode threshold was removed after a fresh official-source check. Frozen
  review ledgers now have a remote gate that reconciles current tracker state
  and excludes only the exact review candidate.
* **Control contract migration**: versioned the ecosystem-disposition and
  release-gate report contracts at 2.0.0, retained the 1.0.0 schemas for stored
  evidence compatibility, and documented the migration boundary.
* **CI supply chain**: pinned current major releases of checkout, Python setup,
  and Dependabot metadata actions by verified commit SHA, and added the
  aggregate `validate` job required by branch protection. The Dependabot
  workflow is now read-only, leaving approval and merge to a human.

### Fixed

* **Landing-page audit integrity**: `analyze_landing.py` now exits nonzero and
  withholds audit grades when browser validation, navigation, or page analysis
  fails. JSON failures remain machine-readable without presenting missing
  observations as failed landing-page controls.
* **Cross-installer safety**: the Bash and PowerShell installers now reject each
  other's ownership manifests before any mutation. Bash also redirects Windows
  dependency installs to PowerShell, with focused recovery guidance and
  regression coverage.
* **Release verification**: load-bearing source dates now fail closed alongside
  claim dates, public tracker coverage must exactly match the reviewed snapshot,
  the remote CI gate reconciles current issue and pull-request metadata and
  exact heads, and target-lock tests no longer replace unrelated subprocess calls.
* **Image provider validation**: generated images must be complete, bounded PNG
  responses with matching output extensions before any provider result can be
  written or reported as successful.
* **Platform edge cases**: Meta planning now classifies account, Pixel, and
  conversion cold starts independently. Google and Microsoft recommendations
  now require verified operation capability before suggesting a setting change,
  and the public marketplace command uses the normalized lowercase repository
  identifier.
* **Product metadata**: generated PDF reports use the 2.0.1 product version
  while the Python core correctly retains its independent 2.0.0 version.
* **Legacy report markup boundary**: user-controlled Markdown, section titles,
  and brand names are escaped before the constrained ReportLab formatting tags
  are introduced, preventing raw ReportLab markup from reaching the renderer.

### Security

* **Dependency VEX gate**: added 16 expiring `not_affected` dispositions for
  current cryptography and Pillow advisories. Each is bound to exact lock
  versions, upstream advisory IDs, evidence paths, and prohibited imports;
  any new advisory, execution-path drift, accepted risk, or expiry fails CI.
  The release retains every referenced evidence path. CI installs the current
  pinned `pip-audit` 2.10.1 patch release and its full dependency closure from
  a CPython 3.12 Linux hash lock in an isolated environment.
* **Code scanning**: added a least-privilege Python CodeQL workflow using the
  `security-extended` query suite and exact action commit pins.
* **Sensitive artifact defense**: expanded ignore and release-audit coverage for
  logs, local databases, credential catch-alls, local configuration, and token
  patterns embedded in binary files.

## [2.0.1] - 2026-07-13

Documentation and metadata patch on top of v2.0.0 for the public mirror
release. No code-contract, scoring, catalog, or behavior changes.

### Changed

* **Public release surface**: user-facing repository links in the README
  install paths, `SUPPORT.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`,
  `CONTRIBUTING.md`, the issue templates, `CITATION.cff`, and the plugin and
  marketplace manifests now point to the public `AgriciDaniel/claude-ads`
  repository, so installation, issues, discussions, and private vulnerability
  reporting work without AI-Marketing-Hub org access. The community mirror
  stays documented for AI Marketing Hub Pro members.
* **Installer default clone source** (`install.sh`, `install.ps1`) retargeted
  from the private org repository to the public repository so remote-source
  installs can clone it without org credentials.
* **Runtime attribution URLs**: the PDF report footer (`generate_report.py`)
  and the page-fetch User-Agent contact URL (`fetch_page.py`) now reference
  the public repository. Signed review-evidence provenance
  (`review_evidence.py`, review templates) intentionally keeps the canonical
  org subject.
* **README**: added the dual-distribution note and the native Claude Code
  plugin install commands.

## [2.0.0] - 2026-07-12

Major architecture release for professional paid-media operations.

### Added

* First-class platform contracts for Reddit, Pinterest, Snapchat, and X, bringing
  the platform surface to twelve dedicated skills, references, audit workers, and
  catalog entries.
* Lifecycle skills for setup, launch, monitor, optimize, research refresh,
  validation/status, and JSON-first report rendering.
* Versioned account snapshot, run manifest, control, finding, and report contracts
  plus a dependency-light CLI.
* Deterministic category-first scoring with severity-weighted evidence coverage,
  provisional and insufficient-evidence states, and spend-aware portfolio scoring.
* Hybrid source, claim, capability, safety, maturity, orchestration, publishing,
  issue, and pull-request control plane.
* Capability-led adapter framework, sanitized export fixtures, portable interface
  metadata, research/source/skill/release verifier agents, and expanded routing
  evaluations.

### Changed

* Rebuilt the main and platform prompts around progressive disclosure, explicit
  precedence, untrusted-input boundaries, schema-valid worker results, partial
  failure semantics, and artifact-backed completion claims.
* Replaced fixed report filenames and prose-only aggregation with unique run
  manifests and versioned JSON as the system of record.
* Reclassified optional, beta, premium, unavailable, and ineligible features as
  unscored opportunities rather than account-health penalties.
* Removed universal CPA, budget, learning-phase, attribution, and feature-adoption
  rules from the runtime prompts.
* Installation now uses authenticated/local sources, a managed environment,
  generated counts, and an exact ownership manifest.
* Installed the intended animated cover banner and the four animated
  architecture, how-it-works, platform-coverage, and health-score diagrams from
  the canonical design source. Every SVG is self-contained, with no scripts,
  event handlers, external requests, or remote assets.
* Reworked the README around a concise quick start, twelve-platform coverage,
  canonical commands, safety defaults, and evidence-led scoring, with a
  no-empty-cell platform table and a user-facing privacy section.
* Retained `assets/demo.gif` and labeled its original command-discovery
  interface as historical.
* Consolidated public-safe research support in the dated source and claim
  ledgers. Raw research transcripts and private working notes now stay outside
  the product repository.
* Replaced dead HTTP JSON Schema identifiers with stable URNs and documented
  the tracked canonical schema locations.
* Extended repository auditing to reject personal tilde-home folders used for
  documents and downloads while retaining portable install examples.
* Added explicit progressive-disclosure routes for the adjacent-platform
  reference and the bounded research and fresh-context review workers.

### Removed

* Removed orphaned legacy banners, static placeholder diagrams, and the obsolete
  reusable branding prompt. Several old diagrams carried stale counts or
  instructions that conflicted with v2 installation, scoring, privacy, and
  capability policy.
* Removed tracked raw research corpora that contained local-machine paths or
  duplicated material already represented by the public-safe control plane.
* Removed the orphaned brand DNA prose template, which contradicted the strict
  v1 brand-profile schema and had no runtime route.

### Security

* Added pre-dispatch SSRF controls for HTTP and Playwright navigation, redirects,
  frames, and subresources; service workers and downloads are disabled.
* Added safe output-root and symlink containment, credential redaction, private
  corpus boundaries, prompt-injection rules, and fail-closed mutation gates.
* Uninstall refuses namespace globs, tampered manifests, unowned files, and
  canonical-path escapes.

### Breaking

* v2 JSON contracts and run-directory outputs replace v1 fixed report files.
* Permanent account-object deletion is unsupported; live writes remain disabled
  until each exact platform operation passes capability-specific release gates.

## [1.8.1] - 2026-05-27

Documentation and metadata patch on top of v1.8.0. No code, check-catalog, or
behavior changes; 59/59 pytest still green. (Caught by a post-ship review.)

### Fixed

* **README "What's new" section** updated from v1.7.0 (Wave 2) to v1.8.0 (Wave 3): the +91 checks (catalog 300), the new `audit-regulatory-compliance` agent, and the agentic-era reference docs. It had been left headlining the prior release.
* **Stale test count corrected: 41 to 59** (actual pytest collected and passing) in README, `CITATION.cff`, `plugin.json`, and `marketplace.json`. The v1.7.0 CHANGELOG entry retains 41 (accurate for that release).
* **Roadmap framing** refreshed: v1.8.0 is shipped / current, not "in active development"; removed the inaccurate "v1.8.0 visual system" diagram alt-text.

### Added

* **Limitations section** in the README (manual data input, catalog scope, point-in-time 2026 benchmarks, experimental non-Claude hosts) with a table-of-contents entry.

## [1.8.0] - 2026-05-26

Substantive Wave 3 release. Adds 91 net-new catalog-tracked platform checks across the five
catalog platforms (Google, Meta, TikTok, LinkedIn, Microsoft), a new regulatory-compliance
audit agent (C01-C29 + C-MCP-1..6 + C-iOS-1), three new reference docs rewritten for the
agentic / MCP / regulatory era, seven per-platform research notes, and a regulatory-exposure
scoring band. Sourced from `research/RESEARCH-NOTES-MAY-2026.md` (primary-source cited).

### Added

#### `/ads google` — Google Marketing Live 2026 (May 20, 2026) addendum (G81-G95, +15 checks)

* Ask Advisor governance, Business Agent for Leads, Direct Offers, AI Mode ad formats (G81-G84)
* Journey-aware bidding, Smart Bidding Exploration on PMax + Shopping, total budgets, demand-led pacing (G85-G88)
* Meridian in GA360, Qualified Future Conversions, Attributed Branded Searches, Asset Studio Gemini Omni, Demand Gen stack, Ads Advisor 3 (G89-G94)
* **G95: DSA → AI Max forced migration P0 gate (September 2026)** — no opt-out; pre-migration AI Brief / FUE / brand-exclusion readiness check

#### `/ads meta` — MCP + March 3 attribution rebuild + Q1 2026 AI-stack refresh (M51-M72, +22 checks)

* Meta Ads MCP (`mcp.facebook.com/ads`, 29 tools), paused-by-default, **MCP write-action governance** with the SurfaceLabs cautionary tale (M51-M53)
* March 3, 2026 attribution rebuild: link-clicks-only click-through, engage-through column, 10s→5s engaged-view, new default windows, YoY-not-comparable warning (M54-M59)
* Q1 2026 AI-stack metrics + **ARM (Adaptive Ranking Model)** + Incremental Attribution Q4 2025 model (M60-M64)
* Ad-level placement control, AI Instant Forms, **730-day audience + Pixel auto-include governance flags**, Advantage+ Creative Categories (M65-M69)
* **M70: Comscore Markets P0 gate — June 22, 2026 automotive cutoff** (`dma_code` → `comscore_market_codes`); DST fees; CAPI one-click + EMQ ≥ 7 (M70-M72)

#### `/ads tiktok` — TikTok World 2026 (May 13-15, 2026) (T29-T46, +18 checks)

* TikTok Ads MCP + Ads Skills; **Smart+ One Buying Experience module-level automation classifier** (T29-T31)
* Music Autofix, creative reporting, TopReach + Creative Sequencing, Branded Buzz, Search Hubs, Symphony / Dreamina, TikTok GO, Mini Series, Collage Carousel, One Asset Manager, View+, Market Scope, TikTok Real, GMV Max (T32-T46)

#### `/ads linkedin` — Off-Platform Event Ads + Campaign Manager rename (L28-L46, +19 checks)

* **L28: Off-Platform Event Ads** (no LinkedIn Event Page; Cvent / ON24 / Integrate)
* **L29: Campaign Manager terminology rename trap** (UI "Campaign Group"→"Campaign" vs unchanged API; UTM mismatch warning)
* Career Journey, Reserved / First Impression Ads, BrandLink, Wire, Thought Leader, CTV, Company Attribution, Company Intelligence API, Agency Certification, Depth Score organic algorithm (L30-L46)

#### `/ads microsoft` — AI Max for Search + Activate 2026 (MS25-MS41, +17 checks)

* **MS25: Microsoft AI Max for Search** (Copilot Search / Answers / Bing; distinct from Google)
* Offer Highlights, Audience Generation, PMax transparency, Clarity AI Visibility, Brand Agents, UCP in Merchant Center, Copilot Checkout, Rewarded Portals, Import Center, diagnostics, DDA, CAPI, Brand Kit, **SOAP API deprecation** (MS26-MS41)

#### `/ads compliance` — NEW `audit-regulatory-compliance` agent (C01-C29 + C-MCP-1..6 + C-iOS-1, +36 checks)

A new parallel audit agent dedicated to the regulatory surface, dispatched by `/ads audit`
alongside the existing agents.

* **C01-C05**: EU AI Act Article 50 — Aug 2, 2026 baseline; Dec 2, 2026 watermarking grandfathered; €15M / 3% penalties; multi-layered watermarking; provider vs deployer obligations
* **C06-C17**: US state privacy — 22 states; 12-state GPC list; CCPA §7025(c)(6) visible confirmation; Connecticut neural data (July 1, 2026); Maryland MODPA; CA Delete Act DROP
* **C18-C21**: Privacy Sandbox October 17, 2025 retirement; remaining CHIPS / FedCM / Private State Tokens; UK CMA 85% inaccuracy / 30% revenue-decline citation
* **C-iOS-1**: iOS 26 ATFP / Link Tracking Protection — server-side tracking mandatory for >5% iOS Safari traffic
* **C22-C29**: DSA enforcement / HIPAA / LegitScript / Special Ad Categories / PIPL / LGPD / DPDPA / TCF v2.3 + GPP
* **C-MCP-1..6**: MCP write-action governance — read-only-first, human approval gate, paused-by-default, rate-limit, no autonomous budget loops, ≥90-day audit-log retention

#### Cross-platform 2026 landscape (X01-X25, research notes)

* Reddit Max / Dual Attribution / App Event Optimization; Pinterest tvScientific + CTV Audiences; Snap Smart Solutions / AI Sponsored Snaps; CTV/OTT shifts; Universal Commerce Protocol (NRF + AP2 → FIDO); IAB Tech Lab AAMP + Agent Registry. Documented in `research/RESEARCH-NOTES-MAY-2026.md`; surfaced via `/ads attribution`, `/ads server-side-tracking`, and the orchestrator (narrative/awareness, not yet catalog-tracked).

#### `/ads amazon` + `/ads apple` deltas (inline)

* Amazon: Unified Campaign Manager, Ads/Creative Agents, Full-Funnel Campaigns, MTA, Sponsored Brands Collections (Jan 28, 2026), SP/SB Prompts GA (March 25, 2026), Brand+ / Performance+, Prime Video expansion, Complete TV (AMZ-new-1..17, inline in `skills/ads-amazon/SKILL.md`)
* Apple: Multiple Search Ad Placements (no position-level reporting), AdAttributionKit refresh, Custom Product Pages, iOS 26 ATFP/LTP, WWDC 2026 watch list (A36-A42, inline in `skills/ads-apple/SKILL.md`)

#### New reference + research docs

* `references/mcp-integration.md` — full rewrite for the agentic era (Google / Amazon / Meta / Microsoft / TikTok MCPs, IAB AAMP + Agent Registry, write-action governance policy + SurfaceLabs precedent)
* `references/compliance-requirements.md` — EU AI Act + 22-state US privacy + Privacy Sandbox + iOS 26 + DSA + HIPAA / LegitScript + global frameworks
* `references/meta-ai-stack.md` — consolidated Andromeda + GEM + Lattice + ARM with Q1 2026 metrics + the four operational principles
* `research/RESEARCH-NOTES-MAY-2026.md` + `research/notes-{google,meta,tiktok,linkedin,microsoft,apple,amazon}.md` — per-platform research notes with primary-source citations
* `references/automation-tier-classifier.md` — module-level automation classification (Smart+ One Buying Experience, Advantage+, AI Max, Accelerate, Microsoft AI Max)

### Changed

* **Compliance agent split** — `audit-compliance` renamed to `audit-policy-compliance` (platform ad policy, Special Ad Categories, deprecated features, performance benchmarks); new `audit-regulatory-compliance` added for the regulatory surface. Agents 10 → **11** (7 audit + 4 creative). Sub-skill count is **unchanged at 22** (the new compliance unit is an audit agent, not a sub-skill).
* **`tests/fixtures/check-catalog.yaml`** — 5-platform catalog extended from 209 to **300** verified checks (Google 95, Meta 72, LinkedIn 46, TikTok 46, Microsoft 41), bidirectionally enforced by the eval harness. Apple, Amazon, the X01-X25 landscape, and attribution + server-side remain inline pending Wave 3.x catalog extraction.
* **`scoring-system.md`** — adds the **regulatory-exposure band** (P0/P1/P2 → severity multipliers, scored at 100% aggregate weight) and the five hard regulatory clocks; refreshed Total Check Counts table to v1.8.0.
* **README.md** — "250+ checks" → "300+ checks"; "10 agents" → "11 agents (7 audit + 4 creative)"; `/ads audit` now spawns 7 parallel subagents incl. `audit-regulatory-compliance`.
* **Version metadata** — `plugin.json`, `marketplace.json`, `CITATION.cff`, and `scripts/generate_report.py` bumped to 1.8.0.

### Deprecated

* References to Privacy Sandbox APIs as a future tracking direction (October 17, 2025 retirement)
* Pre-March-3-2026 Meta YoY comparison framing in `audit-meta` reporting

### Fixed

* Citation accuracy captured in `research/notes-amazon.md`: the "+143% click-attributed sales" figure is re-attributed from Sponsored Brands Collections to Sponsored Brands Reserve Share of Voice (per Amazon's official Reserve Share of Voice page); Google AI Max case studies flagged as vendor-supplied (JumpFly April 2026 independent analysis shows neutral-to-negative)

### Security

* MCP write-action governance defaults documented in `references/mcp-integration.md` and enforced by `audit-regulatory-compliance` (C-MCP-1..6): paused-by-default, ≤200 calls/hour, ≥90-day audit-log retention, human approval gate for budget changes above a configurable threshold. Encodes the SurfaceLabs April 2026 permanent-account-ban precedent.

---

## [1.7.1] - 2026-05-18

Patch release covering the post-v1.7.0 polish wave: a comprehensive README
rewrite to SSS+ tier (graded 64 → 81 → 94 → 96+ across three independent
review passes), a brand-new animated SVG banner (~25× smaller than the
previous PNG with 22 live SMIL animations), the relocation of the canonical
repo to the AI-Marketing-Hub private org (with the prior `AgriciDaniel/claude-ads`
location preserved as the public mirror), and deep verification of every
quantified factual claim across the platform sub-skills.

No new sub-skills, no new agents, no script behavior changes; this is
docs + assets + branding + housekeeping.

### Added

- **Animated SVG banner** (`assets/banner.svg`) replacing the static PNG.
  13.9 KB optimized, 22 SMIL animations (logo gradient breathing, drift
  scanline, divider pulse, 7-command scanning highlight with cursor blinks,
  status-bar pulse dots). Vector-crisp at any zoom; text-searchable and
  screen-reader friendly via `role="img"` + descriptive aria-label and
  `<title>`/`<desc>`. The previous static PNG remains at `assets/banner.png`
  as a fallback for viewers that strip SVG.
- **Branding kit** (`branding/banner-template.html`, `branding/AGENT-PROMPT.md`)
  parameterized HTML template for cloning the terminal-style banner across
  other repos in the same brand family (claude-seo, claude-blog, etc.).
  AGENT-PROMPT ships five pre-built palette presets (warm orange / teal /
  purple / cobalt / crimson), the figlet ANSI-Shadow generation steps, and
  a reproducible Playwright render snippet.
- **`assets/banner-pre-v1.7.0.png`** preserved backup of the prior flat
  banner for anyone referencing the older design.
- **README sections** for the SSS+ rewrite:
  - **Pain-point hero** ("manual audit takes 4-6 hours of senior PPC time;
    Claude Ads runs it in 10-15 minutes") replacing the previous 80-word
    opening paragraph.
  - **"Who this is for"** block with three concrete personas (PPC agency
    lead, in-house marketer, freelance consultant).
  - **"What's new in v1.7.0"** highlights box above the fold.
  - **Sample output** preview, a realistic `/ads audit` JSON excerpt
    showing health score, per-platform breakdown, top findings with
    severity / impact / action / ETA, and quick wins.
  - **Comparison table** (Claude Ads vs manual audit vs agency engagement
    vs commercial PPC audit tool) covering time, cost, repeatability,
    output format, data residency, lock-in, and platform-feature awareness.
  - **Use cases** with three specific workflow patterns.
  - **Financial-KPI FAQ entry** mapping ROAS / CPA / ACOS / TACOS / LTV:CAC
    / MER to the commands that handle each.
  - **Maintenance & support FAQ entry** disclosing the single-maintainer
    model with a 48-hour bug-response commitment.
  - **"Two versions of this skill"** callout explaining the public vs
    community-private dual-repo structure.
  - **Project info** section linking CHANGELOG, CONTRIBUTING, CODE OF
    CONDUCT, SECURITY, SUPPORT inline from README.

### Changed

- **Canonical repo location** moved to `AI-Marketing-Hub/claude-ads` (private
  org repo). The prior `AgriciDaniel/claude-ads` location is preserved as
  the public mirror and is referenced from the new README as the "stable
  open-source" lane. All install commands, badges, citation fields, and
  documentation paths swept across 15 files.
- **README rewritten** from "competent documentation" to a conversion-grade
  artifact, graded by independent reviewers at 64 → 81 → 94 → 96+ across
  three passes. Major rewrites to hero, features section, FAQ structure
  (now `<details>` blocks for 8 questions), and all H2 headings for
  keyword + clarity.
- **Em dashes removed throughout README** (54 occurrences) per house style.
  Replaced contextually with colons (definition / label), semicolons
  (independent clauses), commas (mid-sentence flow), parentheses
  (parenthetical clauses), or middle dots (table footnotes).
- **Comparison-table platform-features cell** sharpened from "2026-current"
  to specific feature names + dates ("Andromeda (Oct 2025), AI Max
  (May 2025), AdAttributionKit + WWDC25 configurable windows, Consent
  Mode V2").
- **Public-repo cross-references** added; README now leads with a Pro
  community badge and a dual-version callout pointing non-members at the
  public open-source repo.
- **Badges retargeted** to the public repo (`AgriciDaniel/claude-ads`) for
  Version + CI, since shields.io cannot read private repos. New "AI
  Marketing Hub Pro community" badge added.
- **Repo references** updated across `.github/ISSUE_TEMPLATE/`,
  `CITATION.cff`, `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`,
  `CONTRIBUTING.md`, `install.sh`, `install.ps1`, plugin / marketplace
  manifests, and the two scripts that include UA strings or version refs.
- **Script file modes** normalized: 5 CLI scripts at 755 (was 775
  group-writable on author's umask), `url_utils.py` correctly stays 644
  as a library.

### Fixed

- **Factual claims cited against primary sources.** Ten quantified claims
  across `ads-meta`, `ads-apple`, `ads-budget`, `ads-google`,
  `ads-microsoft`, and `ads-creative` were verified or corrected against
  vendor / first-party documentation:
  - Andromeda 10,000× capacity (Meta Engineering, Dec 2024)
  - Confect 60% similarity threshold (confect.io)
  - WWDC25 AAK configurable windows (Apple Developer session 221)
  - AppTweak CPP +8% / +6.6% conversion lift (AppTweak benchmark)
  - SoundCloud 58% CR / 39% CPI case study (AppTweak case study)
  - 78% Personalized-Ads-off App Store search (Apple Q1 2022 data,
    via 9to5Mac)
  - Google AI Max 14% conversion lift (Google Ads blog, May 2025)
  - Microsoft Copilot 73% CTR lift (Microsoft Advertising blog, Aug 2025)
  - TikTok platform median ROAS 1.41–1.67 (reworded from a Smart+-specific
    framing the original wording falsely implied)
  - Demand Gen "20% more conversions" clarified to video+image vs
    video-only at same CPA
- **Stale `(latest: v1.5.1)` references** corrected after the public push
  brought the public repo to v1.7.0 content.
- **README badges** that were pointing at the private org repo and
  rendering "no releases or repo not found"; retargeted to the public
  mirror.
- **Stale URL references** in 15 files swept from `AgriciDaniel/claude-ads`
  to `AI-Marketing-Hub/claude-ads` and the corresponding plugin slug form
  (`agricidaniel-claude-ads` → `ai-marketing-hub-claude-ads`).

### Notes

- **`presentations/v1.7.0-release/`** intentionally untracked (release-
  marketing WIP, not shipped with the skill itself).
- **In-progress visual representations** (5 architecture diagrams × A/B/C
  variants = 15 new SVGs, plus a `branding/diagrams-preview.html` comparison
  tool and `branding/scripts/` render automation) currently live in the
  working tree and are NOT part of this release. They will land in a future
  visual-system release once the variant selection is finalized.
- **Repo location**: the canonical development location is now the private
  `AI-Marketing-Hub/claude-ads` repo; `AgriciDaniel/claude-ads` is preserved
  as the public mirror. Subsequent in-development work happens on the
  private repo first.

## [1.7.0] - 2026-05-17

Wave 2 of the 90-day "category leader" plan. Ships the cross-runtime install
matrix, the trust-moat eval harness, deep platform rewrites for the AI Max
and Andromeda eras, and three new sub-skills covering attribution, server-
side tracking, and Amazon retail media.

### Added

- **Cross-runtime install matrix** — `install.sh` / `install.ps1` now accept
  `--target={claude,codex,cursor,windsurf,gemini,goose}` with strict whitelist
  validation. Per-host path tables in a single source of truth; pip install
  gated to Claude Code + Codex CLI only. Optional `--skill-dir` / `--agent-dir`
  overrides validated against `; & | $ ( ) < >` backtick, leading dashes, `..`
  traversal, and UNC-style paths. `uninstall.sh` / `uninstall.ps1` match.
- **Pytest eval harness** in `tests/` — 41 tests covering:
  - **Routing snapshots** (3 tests): every documented trigger phrase routes to
    its expected sub-skill via `evals/creative-evals.json`.
  - **Check-catalog coverage** (4 tests): bidirectional verification between
    `tests/fixtures/check-catalog.yaml` (209 IDs across G/M/L/T/MS) and every
    audit reference file under `ads/references/`. No orphan IDs, no untracked
    rows, total count ≥ 209 baseline.
  - **Scoring math** (6 tests): re-implements the weighted-score algorithm
    from `scoring-system.md` and asserts determinism across 10 runs, correct
    severity weighting, NA exclusion.
  - **SSRF regression** (28 tests): 14 IPv4/IPv6 private/internal blocklist
    cases (including `::/128` from v1.6.0), 5 non-HTTP scheme blocks, DNS
    fail-closed, valid public URL passthrough, plus 6 credential-redaction
    sanitize_error cases and benign-message passthrough.
- **`tests/fixtures/check-catalog.yaml`** — canonical 209-check catalog with
  severity multipliers and result-points table, derived directly from the
  reference files via grep.
- **`requirements-dev.txt`** — pytest ^8 + pyyaml ^6 (test-only, production
  users never need these).
- **CI integration** (`.github/workflows/ci.yml`) — new "Run eval harness
  (pytest)" step between install and pip-audit. Tests fail the build on any
  regression.
- **Outbound Network Destinations table** in `SECURITY.md` — every endpoint
  reachable by every script is now documented with its gating mechanism.
- **3 new sub-skills**:
  - `ads-attribution`: cross-platform attribution audit covering iOS
    AdAttributionKit (view-through 24h post-impression, WWDC 2025 configurable
    windows, ATT opt-in monitoring), web (GA4 attribution model, Google Ads
    attribution, cross-channel auto-tagging), Consent Mode V2 Advanced
    enforcement, server-side stitching, MMP health, cross-device matching.
  - `ads-server-side-tracking`: server-side pipeline audit covering sGTM
    (custom domain, Conversion Linker), Meta CAPI / CAPI Gateway, event_id
    deduplication, ≥80% server / client hit ratio, 6-event pixel debug
    walkthrough, lowercased + trimmed SHA-256 PII hashing discipline.
  - `ads-amazon`: Amazon Ads audit covering Sponsored Products (auto vs
    manual + search-term harvesting), Sponsored Brands (HSA + SB Video),
    Sponsored Display (audience vs contextual), ACOS / TACOS targets per
    contribution margin, bid + budget management, Brand Analytics integration.
- **Multi-host README** — hero reframed for Agent Skills compatibility,
  cross-host install matrix table with per-host path mapping, experimental-
  target warning, host-support badge row (Claude verified, others
  experimental), new "Eval Harness" Features section.
- **Updated repo About-field text** and **Topics list** in
  `research/distribution-prep-v1.7.0.md` to reflect Wave 2 changes.
- **10-Principle Thinking Framework** (`ads/references/thinking-framework.md`)
  — load-on-demand thinking discipline (OBSERVE × 2 / LISTEN / THINK /
  CONNECT × 2 / FEEL / ACCEPT / CREATE / GROW) referenced by the
  orchestrator and four thinking-heavy sub-skills (`ads-audit`, `ads-plan`,
  `ads-create`, `ads-dna`). Maps each principle to concrete ad-work behavior
  + anti-pattern + example workflow trigger. Cross-links existing artifacts
  (3× Kill Rule, Context Intake gate, MER/LTV math, copy frameworks,
  voice-to-style mapping) so the discipline feels native rather than
  bolted-on.

### Changed

- **`ads-google` SKILL.md** — AI Max for Search section expanded with the
  `ai_max_setting.enable_ai_max` field (Google Ads API v21+), AI Brief audit
  (business name, value prop, audience, forbidden topics, disclaimers), text
  customization rules, Final URL Expansion (FUE) controls, brand exclusions,
  text disclaimers (rolling out May 2026+). New **DSA Migration Pre-Flight
  Checklist** section (11 items) for the September 2026 auto-migration of
  DSA / ACA / campaign-level broad-match into AI Max.
- **`ads-meta` SKILL.md** — Andromeda section expanded to **Andromeda + GEM +
  Lattice (2026)** covering all three stack components and why creative is
  now mechanical targeting. New **creative-as-targeting scoring rubric**
  (5 axes, 0-10 total). New **Entity-ID Clustering Predictor** section
  (promoted from Wave 3) with 5 predictor heuristics and a pre-launch
  `creative-cluster-risk.md` deliverable. New **MAPI v25 ASC/AAC
  Deprecation Detector** section. New **ASC defaults for Sales/Leads/App**
  section.
- **Orchestrator routing-table** in `ads/SKILL.md` — 3 new commands
  (`/ads amazon`, `/ads attribution`, `/ads tracking`), sub-skill count
  refreshed 19 → 22, Community Footer "When to show" extended with new
  commands, stale reference-file annotations fixed (google 74→80, meta
  46→50, linkedin 25→27, tiktok 25→28, microsoft 20→24 — now matches the
  catalog).
- **`scripts/url_utils.py`** — `sanitize_error()` canonicalized as the single
  source of truth for exception-message redaction. `analyze_landing.py`,
  `capture_screenshot.py`, and `fetch_page.py` all import and apply it at
  every broad-except site.
- **`scripts/generate_image.py`** — Replicate result URL is now revalidated
  against the SSRF blocklist before fetching, and `requests.get` runs with
  `allow_redirects=False` so a redirect to a private IP cannot bypass the
  gate.
- **`scripts/fetch_page.py`** — all `RequestException` / `SSLError` /
  `ConnectionError` interpolations now run through `sanitize_error`.
- **`uninstall.sh` / `uninstall.ps1`** — glob-based discovery
  (`${SKILL_BASE}/ads-*/`) instead of hardcoded sub-skill list. New
  sub-skills no longer require uninstaller updates.

### Security

- **v1.6.0 baseline (92/100) lifted to 94/100** in the Wave 2 cybersecurity
  re-audit. Zero new HIGH/CRITICAL findings.
- All 6 install-matrix injection attack inputs verified blocked by
  `validate_install_path()` / case-statement whitelist (semicolon command
  injection, shell metacharacters, parent-traversal `..`, leading dashes,
  UNC paths, unknown target keys).
- Glob-discovery in uninstaller cannot escape `${SKILL_BASE}` since
  `SKILL_BASE` is sourced only from the whitelisted target mapping; no
  `--skill-dir` override on the uninstall side.
- Defense-in-depth Replicate URL revalidation closes a hypothetical upstream-
  compromise vector even though Replicate is a trusted vendor.

### Notes

- **Wave 3 backlog**: `ads-walmart`, `ads-ctv` + `audit-ctv`,
  `ads-retail-media` orchestrator, `ads-pmax-feed`, `ads-mmm`,
  `ads-incrementality`, creative pipeline v2 (Veo 3.1, Runway Gen-4.5, Kling
  3.0 Omni, Seedance 2.0), 4 prioritized industry templates (DTC subscription,
  Marketplace seller, Auto dealer, EdTech), compliance attestation pack,
  routing-table two-tier refactor (triggered when sub-skill count exceeds ~25;
  we're at 22), pair `audit-amazon` / `audit-attribution` / `audit-server-side`
  agents so `/ads audit` can dispatch the Wave 2 sub-skills in parallel.
- **Carry-forward security backlog**: a 2-MED list and a 4-LOW list from the
  Wave 2 audit are captured in the plan file. Both will be addressed alongside
  the Wave 3 sub-skill agents and CTV creative pipeline.

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
