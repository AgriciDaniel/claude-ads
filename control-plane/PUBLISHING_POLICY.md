# Publishing Policy

Claude Ads has an existing MIT public distribution at
`AgriciDaniel/claude-ads` and a private development/community repository at
`AI-Marketing-Hub/claude-ads`. Public distribution does not make private
development inputs, review evidence, or future release candidates public.
Repository visibility and any Pages or release-asset visibility must be checked
independently. Each new release, publication, or visibility change still requires
the owner's explicit approval and the public-release gates below.

## Classification

### Public-safe

- Original code, schemas, tests, templates, and synthesized operating doctrine.
- Dated citations and links to public sources.
- Sanitized fixtures that cannot identify a person, client, account, or local
  machine.
- High-level capability and maturity status that matches verification evidence.
- Short quotations within the source license and applicable quotation limits.

### Private

- Client and account exports, IDs, budgets, audiences, creatives, and reports.
- Internal roadmaps, unreleased product decisions, and private issue context.
- Evaluation transcripts or agent task/result packets that contain private
  inputs.
- Private research notes whose redistribution is not approved.

### Restricted: never package or publish

- Credentials, tokens, cookies, OAuth material, signing keys, and secrets.
- Raw captured prompts, leaked prompt corpora, or large third-party excerpts.
- Personal data not explicitly created as a sanitized fixture.
- Local absolute paths, machine state, browser profiles, or session artifacts.
- Third-party code or content without a compatible license and attribution.

## Clean-room rule

Private Fable research may inform abstract principles such as explicit
checklists, instruction precedence, effort calibration, examples, safety
repetition, and verification. It must not be copied, closely paraphrased, or
committed. Brainstein's Apache-2.0 patterns may inform original implementation;
reuse of code requires normal license and notice review.

## Public-release gate

Before changing visibility or publishing an artifact:

1. Obtain explicit owner approval for that specific repository or artifact.
2. Scan the complete Git history, working tree, generated archives, and release
   metadata for secrets, personal data, raw research, and local paths.
3. Verify the source and claim ledgers are current and redistribution fields
   permit publication.
4. Verify all dependencies and incorporated contributions have compatible
   licenses and notices.
5. Build from a clean checkout; verify the manifest, checksums, SBOM, and ZIP
   contents.
6. Run the full local and required remote CI matrix in a fresh context.
7. Confirm public documentation does not advertise disabled capabilities or
   expose private repository URLs in public installation paths.
