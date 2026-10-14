## Summary

Briefly describe what this PR does and why.

## Problem and Evidence

State the problem and the evidence for it (failing test, source, or reproduction).

## Type of Change

- [ ] Bug fix
- [ ] New sub-skill or feature
- [ ] Reference file update (benchmarks, specs, audit checks)
- [ ] Documentation
- [ ] Other (describe):

## Public Contract Changes and Risks

Note any change to schemas, commands, outputs, or capability status, and the risks.
Write "None" if there are none.

## Checklist

- [ ] The change is focused and keeps unrelated edits out
- [ ] Regression tests derived from the failure or intended capability are added
- [ ] Tested against sanitized fixtures (never a real client account export)
- [ ] `SKILL.md` files stay under approximately 500 lines/5,000 tokens
- [ ] Reference files stay focused, with detailed facts behind progressive disclosure
- [ ] Platform, policy, or API claims have dated sources and claim coverage
- [ ] The capability manifest changes only where implementation, fixtures, tests, and evidence justify it
- [ ] Python scripts output valid JSON
- [ ] Shell scripts use `set -euo pipefail`
- [ ] `python scripts/release.py audit` passes
- [ ] `python -m pytest -q` passes
- [ ] No credentials, client data, private research, local absolute paths, or agent transcripts in the diff

## Related Issues

Closes #
