# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly via the **private GitHub Security Advisory channel**:

1. **Do NOT open a public issue** (public issues expose the vulnerability before it can be patched).
2. Open a [GitHub Security Advisory](https://github.com/AgriciDaniel/claude-ads/security/advisories/new) on this repo. This is the only supported private disclosure channel — do not email or DM.
3. Include: affected version (e.g. v1.5.1), reproduction steps, and impact assessment.

We aim to acknowledge reports within **48 hours** and provide an estimated resolution timeline within **7 days**.

## Supported Versions

Only the latest version receives security updates.

## Security Practices

- No credentials or API keys are stored in this repository
- Install scripts write only to user-level directories (`~/.claude/`)
- Python dependencies install in isolated virtual environments
