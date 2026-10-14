# Contributing to Claude Ads

Claude Ads accepts focused, source-grounded changes that preserve privacy,
capability honesty, deterministic verification, and read-only defaults.

## Before changing code or guidance

1. Read `AGENTS.md`, the control-plane boundaries, and the relevant skill,
   implementation, fixtures, and tests.
2. Search the ecosystem disposition ledger and current issues to avoid repeating
   reviewed work.
3. For platform, policy, API, regulation, benchmark, or specification changes,
   collect current official or primary evidence and update source/claim coverage.
4. For an external repository idea, record its license and provenance. Public does
   not mean reusable.

Never commit credentials, client/account exports, customer data, private prompts,
raw private research, local absolute paths, or agent transcripts.

## Development setup

```bash
git clone https://github.com/AgriciDaniel/claude-ads.git
cd claude-ads
python -m venv .venv
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements.lock
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-dev.lock
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r .github/requirements-schema-tests.lock
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
```

Install the current checkout into a host only when needed:

```bash
bash install.sh --source=local
```

Do not use curl-to-shell installation or silent global Python mutation.

## Pull requests

- Create a focused branch and keep unrelated changes out.
- State the problem, evidence, public contract changes, risks, and verification.
- Add regression tests derived from the failure or intended capability.
- Preserve JSON schema compatibility or declare a major contract change.
- Update the capability manifest only when implementation, fixtures, tests, and
  evidence justify the new status.
- Run the repository audit and full test suite.

```bash
python scripts/release.py audit
python -m pytest -q
```

Required remote CI must pass; local success does not substitute for skipped or
billing-blocked checks.

## Skills and agents

- Skill directories use lowercase kebab-case and `ads-` names.
- `SKILL.md` frontmatter contains only `name` and a comprehensive `description`.
- Put what the skill does and when it triggers in the description.
- Keep `SKILL.md` under approximately 500 lines/5,000 tokens.
- Move detailed facts, controls, examples, and schemas behind progressive
  disclosure.
- Use ordered checks, explicit precedence, operational reasons, untrusted-input
  boundaries, output contracts, and recovery behavior.
- Workers return schema-valid results; one conductor owns final artifacts.
- Agents receive least-privilege tools and no implicit mutation authority.

The plugin keeps the name `claude-ads`. Current `claude plugin validate .` reports
that names starting with `claude-` are reserved, and that one error is expected:
Claude Code 2.1.296 still installs and runs the plugin. Treat any other validation
error as a defect, and re-check this decision if a directory submission is planned.

Add positive, near-miss, ambiguous, and collision cases for new routing surfaces.
High-risk behavior also belongs in `evals/v2-behavior-evals.json`.

## Platform controls and sources

- Preserve stable control IDs once released.
- Model applicability, availability, geography, account maturity, required inputs,
  severity, source IDs, stability, and scoring behavior.
- Keep optional, beta, premium, unavailable, and ineligible features unscored.
- Do not duplicate penalties for one root problem.
- Do not add a precise threshold without source, scope, methodology, and expiry.
- Unknown and not-applicable are valid results, not failures to hide.

## Adapters and account changes

Every adapter implements capability discovery, read snapshot, draft, apply,
verify, and rollback interfaces. New adapters begin read-only.

A write capability requires sandbox fixtures, idempotency, exact object scope,
approval, ceilings, verification, audit, rollback, and adversarial tests. Permanent
deletion is unsupported in v2.

## Contributors and acknowledgments

Claude Ads benefits from community bug reports, feature requests, and proposed
fixes. Thank you to the following contributors whose work informed v2.0.2.
Some proposals were independently implemented or superseded; these credits
recognize the contribution without implying that every submitted patch was merged.

| Contributor | Contribution | Discussion |
| --- | --- | --- |
| [@principisimone-sys](https://github.com/principisimone-sys) | Search and DSA overlap request | [#65](https://github.com/AgriciDaniel/claude-ads/issues/65) |
| [@HarKro753](https://github.com/HarKro753) | Meta account, Pixel, and conversion cold-start request | [#53](https://github.com/AgriciDaniel/claude-ads/issues/53) |
| [@plcosta](https://github.com/plcosta) | Marketplace case-normalization report and proposed documentation fix | [#17](https://github.com/AgriciDaniel/claude-ads/issues/17), [#18](https://github.com/AgriciDaniel/claude-ads/pull/18) |
| [@ulises2k](https://github.com/ulises2k) | Stale marketplace-alias installation report | [#56](https://github.com/AgriciDaniel/claude-ads/issues/56) |
| [@kutzki](https://github.com/kutzki) | Windows dependency-lock and older-install update report | [#57](https://github.com/AgriciDaniel/claude-ads/issues/57) |
| [@SamaEducationalCo](https://github.com/SamaEducationalCo) | Misleading grades after failed landing-page analysis | [#61](https://github.com/AgriciDaniel/claude-ads/issues/61) |
| [@Bortlesboat](https://github.com/Bortlesboat) | Proposed landing-page analysis failure fix | [#66](https://github.com/AgriciDaniel/claude-ads/pull/66) |
| [@gabbyran2026-gif](https://github.com/gabbyran2026-gif) | Proposed target-lock test subprocess fix | [#58](https://github.com/AgriciDaniel/claude-ads/pull/58) |
| [@AbundantASG](https://github.com/AbundantASG) | Proposed scoped target-lock test subprocess fix | [#59](https://github.com/AgriciDaniel/claude-ads/pull/59) |
| [@hendrixfreire](https://github.com/hendrixfreire) | Sensitive-file ignore-pattern report | [#32](https://github.com/AgriciDaniel/claude-ads/issues/32) |
| [@josefresco](https://github.com/josefresco) | Non-actionable Smart Conversions removal advice report | [#50](https://github.com/AgriciDaniel/claude-ads/issues/50) |
| [@dead-simba](https://github.com/dead-simba) | Request to revisit Meta architecture guidance | [#15](https://github.com/AgriciDaniel/claude-ads/issues/15) |
| [@c6zks4gssn-droid](https://github.com/c6zks4gssn-droid) | Repository-tooling proposal, including CodeQL | [#29](https://github.com/AgriciDaniel/claude-ads/pull/29) |

## Security reports

Do not open a public issue for a vulnerability. Use the repository's private
[GitHub Security Advisory](https://github.com/AgriciDaniel/claude-ads/security/advisories/new)
channel and include the affected version, reproduction, and impact.

## Release work

Release candidates must pass source freshness, deterministic/model evaluations,
security/privacy/license scans, installation matrices, reproducible packaging,
SBOM/checksum generation, and fresh-context verification.

Claude Ads has an existing MIT public distribution at `AgriciDaniel/claude-ads`
and a private development/community repository at `AI-Marketing-Hub/claude-ads`.
Public distribution does not make private development inputs, review evidence,
or future release candidates public. Each new release, publication, or
visibility change still requires the owner's explicit approval and the
public-release gates in
[`control-plane/PUBLISHING_POLICY.md`](control-plane/PUBLISHING_POLICY.md).
Contributors do not publish releases or change repository visibility.
