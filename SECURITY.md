# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly via the **private GitHub Security Advisory channel**:

1. **Do NOT open a public issue** (public issues expose the vulnerability before it can be patched).
2. Open a [GitHub Security Advisory](https://github.com/AgriciDaniel/claude-ads/security/advisories/new) on the public repo. This is the only supported private disclosure channel — do not email or DM.
3. Include: affected version (for example v2.0.0), reproduction steps, and impact assessment.

We aim to acknowledge reports within **48 hours** and provide an estimated resolution timeline within **7 days**.

## Supported Versions

Only the latest version receives security updates.

## Security Practices

- No credentials or API keys are stored in this repository
- Install scripts write only to configured host roots, canonicalize destinations,
  reject link escapes and unowned file collisions, and record an ownership manifest.
  The Windows installer preflights its complete plan and rejects reparse-point,
  managed-environment, and late-file collisions before its first destination write.
- Python dependencies install in isolated virtual environments
- Shared SSRF validation (`scripts/url_utils.py`) rejects non-public IPv4/IPv6,
  pins Requests to the validated numeric address while preserving Host/SNI/TLS
  verification, and re-enters the guard for every redirect. Playwright cannot pin
  Chromium's socket resolution, so browser dispatch is denied unless an external
  OS/container egress sandbox supplies a short-lived Ed25519-signed attestation
  bound to the current environment. Screenshot capture writes a digest-bound
  receipt naming the attestation, issuer, trust key, environment, and artifact.
- Error messages are scrubbed via `sanitize_error()` before reaching stdout, JSON output, or audit reports — strips `key=`, `token=`, `secret=`, `password=`, and bare `Bearer <token>` substrings
- GitHub Actions are pinned to full commit SHAs. The Dependabot workflow is
  read-only and cannot approve or merge its own pull request. A human owns the
  merge decision after required branch checks.
- Exact-version `pip-audit` runs on every CI build. New, unhandled, stale, or
  execution-path-relevant advisories fail closed. A reported advisory may pass
  only through an expiring, exact-version `not_affected` record with verified
  code-path evidence.

## Outbound Network Destinations

The following endpoints may be contacted at runtime. All user-supplied URLs pass through the SSRF blocklist before any fetch is attempted; trusted vendor endpoints are hardcoded and not user-influenceable.

| Endpoint | Purpose | Script | Gated by |
|----------|---------|--------|----------|
| `generativelanguage.googleapis.com` | Gemini image generation (fallback path) | `generate_image.py` | API key (env var) |
| `api.openai.com` | OpenAI image generation (fallback path) | `generate_image.py` | API key (env var) |
| `api.stability.ai` | Stability AI image generation (fallback path) | `generate_image.py` | API key (env var) |
| `api.replicate.com` | Replicate model invocation (fallback path) | `generate_image.py` | API key (env var) |
| Replicate-returned result URL | Fetch generated image bytes | `generate_image.py` | HTTPS check + SSRF revalidation via `url_utils.validate_url` (v1.7.0+) |
| User-supplied URLs | Landing page analysis, screenshot capture, page fetch | `analyze_landing.py`, `capture_screenshot.py`, `fetch_page.py` | DNS-pinned HTTP; browser default-deny unless external egress sandbox is attested, plus per-request validation |
| `github.com` (read-only, via git clone) | Skill installation | `install.sh`, `install.ps1` | Hardcoded repo URL |
| PyPI (`pypi.org`, `files.pythonhosted.org`) | Python dependency install | `install.sh`, `install.ps1` | Hardcoded; trusted by `pip` |

If you discover any other outbound destination not listed above, please report it via the disclosure channel above.

## Browser egress attestations

The Boolean `--egress-sandbox-attested` escape hatch is not supported. Browser
execution accepts only a JSON document conforming to
`control-plane/schemas/egress-sandbox-attestation.schema.json` and authenticated
with Ed25519. The signature covers the canonical JSON object with
`authentication.signature_b64url` omitted: UTF-8, lexicographically sorted keys,
no insignificant whitespace, and no ASCII escaping. Attestations must:

- name the `claude-ads-browser-egress` audience and the exact environment;
- expire within 24 hours of issuance;
- assert every required IPv4, IPv6, DNS-rebinding, redirect, subresource,
  metadata, private-address, and fail-closed control;
- include test or policy evidence references; and
- be signed by a key whose public half, key ID, and environment ID are supplied
  outside the document through `CLAUDE_ADS_EGRESS_ATTESTATION_PUBLIC_KEY_B64URL`,
  `CLAUDE_ADS_EGRESS_ATTESTATION_KEY_ID`, and
  `CLAUDE_ADS_EGRESS_ENVIRONMENT_ID`.

The runtime receives only the Ed25519 public key, so it cannot manufacture an
attestation. Missing dependencies, trust material, controls, evidence, signature,
environment binding, or freshness fail closed before Chromium launches. The
schema and signature authenticate the issuer's claim; operators must still
configure and test the named network boundary independently.

Screenshots and their receipts are confidential. They use same-directory atomic
replacement, receive mode `0600` where POSIX permissions are available, omit the
URL path and query from the receipt, and must not be committed, attached to public
issues, or included in release packages. Capture requires a validated confidential
`data-lifecycle` contract; receipts contain its lifecycle fields and only
repository/run-relative artifact locators.

## Data lifecycle

Every persisted run and workflow artifact declares the versioned contract in
`claude_ads_core/schemas/v1/data-lifecycle.schema.json`. The product policy is
`control-plane/manifests/data-lifecycle-policy.json`. It records classification,
an explicit zero-second product minimum plus an operator-defined purpose-bound
deadline or exception, verified encryption evidence for non-public data, least-
privilege roles, deletion and independent verification, and private incident
handling. These are operational safeguards, not legal retention requirements or
claims of compliance.

Creative-generation JSON stores prompt SHA-256 values and the canonical redacted
summary only. Screenshot and generation JSON store relative locators only. Raw
prompts, private provider payloads, and resolved local paths remain outside shipped
artifacts and should be handled through approved ephemeral/private evidence channels.
