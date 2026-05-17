# Contributing to claude-ads

Thanks for your interest in contributing! Here's how to get involved.

## Reporting Bugs

Open a [GitHub Issue](https://github.com/AgriciDaniel/claude-ads/issues) with:

- Your OS and Python version
- The full error output (copy from terminal)
- The command or step that failed
- The ad platform and account context (if applicable)

## Suggesting Features

Use [GitHub Discussions](https://github.com/AgriciDaniel/claude-ads/discussions) for feature ideas and questions.

## Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test with a sample ad account before submitting
5. Submit a PR with a clear description of what changed and why

### Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/claude-ads.git
cd claude-ads
bash install.sh
```

### General Guidelines

- All Python scripts should output JSON for Claude Code to parse
- Shell scripts should use `set -euo pipefail` for safety
- SKILL.md files must stay under 500 lines / 5000 tokens
- Reference files (`ads/references/*.md`) should be focused and under 200 lines
- Follow kebab-case naming for all directories and files
- Keep dependencies minimal — prefer stdlib over third-party where possible

## Adding a New Sub-Skill

Sub-skills live under `skills/ads-<name>/` and follow a strict structure. To add one:

1. **Pick a name.** Kebab-case, prefixed with `ads-`. Example: `ads-amazon`, `ads-attribution`.
2. **Mirror an existing sub-skill** as a template — `skills/ads-microsoft/` is a clean, simple example; `skills/ads-google/` is the densest.
3. **Required frontmatter** in `skills/ads-<name>/SKILL.md`:
   ```yaml
   ---
   name: ads-<name>
   description: "<Functional summary of what the skill does>. Use when user says <trigger1>, <trigger2>, ..., or <triggerN>."
   user-invokable: false
   tested_date: YYYY-MM-DD
   tested_with: claude-code v2.x
   ---
   ```
   The `user-invokable: false` flag means the skill is dispatched by the `ads` orchestrator, not invoked directly via `/ads-<name>`.
4. **Trigger discipline.** The `description:` field is what the LLM uses to route. Include 6–12 trigger synonyms (platform name, colloquial phrasings, abbreviations, feature names).
5. **Update the orchestrator.** Add a row to the routing table in `ads/SKILL.md` and update the routing logic if needed.
6. **Add a reference file** if your skill needs domain knowledge — see "Adding a Reference File" below.
7. **Test it** by invoking the orchestrator with one of your trigger phrases — confirm your sub-skill loads.

## Adding a Reference File

Reference files in `ads/references/` are loaded on-demand by sub-skills (progressive disclosure). Use them for:

- Audit checklists (e.g., `google-audit.md`)
- Creative specs per platform (e.g., `meta-creative-specs.md`)
- Decision trees, benchmarks, compliance tables

Guidelines:

- Keep each file under 200 lines so it fits in the dispatching agent's context.
- Add a dated header comment: `<!-- Updated: YYYY-MM-DD | v<x.y> -->`.
- Cite sources inline where possible (`<!-- Sources: WordStream 2025 (annual report), Triple Whale 2025 e-commerce -->`).
- For audit checklists, follow the existing ID convention: platform-letter + number (G01, M01, L01, T01, B01, A01).

## Testing Audit Checks

Until the Wave 2 eval harness lands, regression testing is manual:

- The `evals/creative-evals.json` file contains routing snapshots (which trigger phrase loads which sub-skill).
- Validate your sub-skill loads correctly on its triggers by running the orchestrator and checking the dispatched skill name.
- For new audit checks, add a synthetic example account export (anonymized) to a fixture directory and verify the check fires correctly with `pass` / `warning` / `fail` outputs.
- When the `tests/` directory lands in Wave 2, all new checks will be expected to have a corresponding fixture + golden output. Plan ahead by structuring checks with deterministic pass/warn/fail conditions.

## Reporting Bugs

Open a [GitHub Issue](https://github.com/AgriciDaniel/claude-ads/issues) using the bug-report template. Include OS + Python version, the full error output, the command that failed, and the platform context.

## Suggesting Features

Use [GitHub Discussions](https://github.com/AgriciDaniel/claude-ads/discussions) for feature ideas. For larger proposals (new platforms, new sub-skills), open a feature-request issue first to align on scope.

## Security

For security issues, **do not open a public issue**. Use the [private GitHub Security Advisory channel](https://github.com/AgriciDaniel/claude-ads/security/advisories/new). See `SECURITY.md`.
