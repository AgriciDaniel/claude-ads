# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Claude Ads** is a Tier 4 Claude Code skill (also packaged as a plugin, `.claude-plugin/plugin.json`) for paid advertising audit and optimization across Google, Meta, YouTube, LinkedIn, TikTok, Microsoft, Apple, and Amazon Ads. It follows the Agent Skills open standard and a 3-layer architecture: **directive** (`ads/SKILL.md` orchestrator) → **orchestration** (22 sub-skills in `skills/`, 10 agents in `agents/`) → **execution** (Python scripts in `scripts/`). 250+ weighted audit checks, 12 industry templates, attribution and server-side tracking deep dives, AI creative generation.

There is no application to run — the deliverable is the skill itself (Markdown skills + agents + Python CLI scripts) plus its eval harness.

## Development Commands

```bash
# One-time dev setup
pip install -r requirements.txt -r requirements-dev.txt

# Run the full eval harness (41 pytest tests)
pytest tests/ -v --tb=short

# Run one test file / one test
pytest tests/audit/test_scoring_math.py -v
pytest tests/routing/test_creative_routing.py::test_name -v

# CI parity checks (what .github/workflows/ci.yml runs besides pytest)
find . -name "*.py" -not -path "./.git/*" -exec python3 -m py_compile {} \;
python3 -m json.tool .claude-plugin/plugin.json > /dev/null
bash -n install.sh && bash -n uninstall.sh
```

Scripts run standalone with a CLI and JSON output, e.g. `python3 scripts/analyze_landing.py --help`. Local skill install for manual testing: `bash install.sh` (default target Claude Code; `--target=codex|cursor|windsurf|gemini|goose` are experimental cross-host installs — target keys are whitelist-validated).

## Architecture

```
ads/SKILL.md          # Orchestrator: routing table, context intake, core rules
ads/references/       # 26 on-demand knowledge files (progressive disclosure)
skills/ads-*/SKILL.md # 22 sub-skills, one directory per domain
agents/*.md           # 10 agents (6 audit + 4 creative), invoked via Task tool
scripts/*.py          # Execution layer: landing analysis, screenshots, PDF reports
tests/                # Eval harness (routing, audit coverage, scoring math, script security)
```

### How routing works (the part that spans multiple files)

- `ads/SKILL.md` is the only user-facing entry point (`/ads <command>`). Its routing table maps commands/trigger phrases to sub-skills.
- Sub-skills carry `user-invokable: false` frontmatter — they are dispatched by the orchestrator, not invoked directly. **Routing happens via the `description:` frontmatter field**: it must contain 6–12 trigger synonyms (platform names, abbreviations, colloquial phrasings). Adding a sub-skill without updating the orchestrator's routing table breaks dispatch.
- Sub-skills load `ads/references/*.md` on demand (audit checklists, benchmarks, creative specs) instead of inlining knowledge.
- `/ads audit` fans out the 6 audit agents in parallel via the Task tool with `context: fork` — never via Bash.
- The creative pipeline chains agents through files: `ads dna` → `brand-profile.json` → `creative-strategist` → `campaign-brief.md` → `copy-writer` / `visual-designer` → `generation-manifest.json` → `format-adapter` → `format-report.md`.

### Eval harness structure

- `tests/fixtures/check-catalog.yaml` — canonical catalog of 209 audit checks; coverage tests assert reference files stay in sync with it.
- `tests/routing/` — snapshot tests that trigger phrases route to the right sub-skill (fixtures in `evals/creative-evals.json`).
- `tests/audit/` — check-catalog coverage + Health Score scoring math.
- `tests/scripts/` — security regressions (SSRF redirect bypass, credential redaction in `scripts/url_utils.py`). Treat these as load-bearing: `url_utils.py` guards every outbound fetch.
- Shared session-scoped fixtures live in `tests/conftest.py` (`repo_root`, `check_catalog`, `creative_evals`, `skill_descriptions`).

## Conventions

- SKILL.md files: under 500 lines / 5000 tokens. Sub-skill frontmatter requires `name`, `description` (with triggers), `user-invokable: false`, `tested_date`, `tested_with`.
- Reference files: focused, aim under 350 lines; split when one file mixes concerns. Add a dated header (`<!-- Updated: YYYY-MM-DD | v<x.y> -->`) and cite sources inline. Audit check IDs follow platform-letter + number (G01, M01, L01, T01, B01, A01).
- New audit checks need deterministic pass/warn/fail conditions and a corresponding entry in `tests/fixtures/check-catalog.yaml`.
- Scripts: docstring, CLI interface, JSON output; prefer stdlib over third-party. Shell scripts use `set -euo pipefail`.
- Kebab-case for all skill directories and files; sub-skill dirs are prefixed `ads-`.
- No hardcoded credentials; external API access goes through MCP servers.
- To add a sub-skill, mirror an existing one (`skills/ads-microsoft/` is the cleanest template, `skills/ads-google/` the densest) and follow CONTRIBUTING.md.

## Release Blog Post

After cutting a new release (git tag + `gh release create`), run:

```
/release-blog
```

This generates a blog post on https://agricidaniel.com/blog/, handles cover image generation, SEO metadata, FAQ schema, internal linking, sitemap/llms.txt updates, Vercel deployment, and Google indexing.
