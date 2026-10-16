# Third-Party Notices

Claude Ads is MIT-licensed. Product names, APIs, documentation, public issues,
pull requests, and referenced repositories remain the property of their respective
owners and are not relicensed by this repository.

## Design and research provenance

- Brainstein is Apache-2.0. Claude Ads v2 uses an original domain-specific
  implementation of source, capability, maturity, orchestration, and release-gate
  ideas; no Brainstein source code is copied by the v2 control plane.
- Anthropic's public skill-creator material is Apache-2.0 at the skill level. It
  informed progressive disclosure, trigger evaluation, and deterministic helper
  guidance; Claude Ads prompts and implementation are original.
- Private Fable research is used only as non-redistributed design input. No raw or
  captured prompt, private corpus, close paraphrase, or restricted artifact is
  included.
- GitHub issues and pull requests are summarized and linked in the ecosystem
  disposition ledger. Text and patches are not copied without repository-license
  and contributor-attribution review.

## Runtime and development dependencies

Dependencies are installed from their publishers and retain their own licenses:

The dependency set resolved on 2026-10-07 selects Pillow 12.3.0, urllib3 2.8.0, and WeasyPrint 70.0. The dependency inventory binds the publisher source URLs, selected-wheel SHA-256 hashes, and embedded license/notice documents for these versions.

- Requests: Apache-2.0.
- urllib3: MIT.
- Playwright for Python: Apache-2.0.
- Cryptography: Apache-2.0 or BSD-3-Clause.
- Pillow: MIT-CMU.
- ReportLab and WeasyPrint code: BSD-3-Clause. ReportLab wheels also include
  DarkGarden under GPL-2.0-or-later with a document-embedding exception and
  Bitstream Vera font terms.
- Matplotlib: the Matplotlib 1.3+ license (`LicenseRef-Matplotlib-1.3`), plus
  bundled font/style/colormap notices including OFL-1.1, Apache-2.0, MIT, and
  BSD-style terms.
- PyYAML and pytest: MIT.

The transitive closure is part of the release inventory, not exhausted by this
summary. In particular, Pyphen code offers GPL-2.0-or-later OR
LGPL-2.1-or-later OR MPL-1.1 alternatives and its dictionaries have
language-specific terms. The dependency inventory preserves the exact path,
SHA-256, text, and artifact assignment for every license/notice-like file found
across all 119 selected wheels. The webencodings 0.5.1 wheel contains no matching
embedded path and is explicitly recorded as documentless rather than assigned
invented notice text.

The release SBOM is generated from the checked-in, publisher-metadata-backed
dependency inventory and validates every declared direct requirement and locked
transitive edge. This notice is not a substitute for that machine-generated
inventory.

## Platform interfaces

Google, Meta, YouTube, LinkedIn, TikTok, Microsoft, Apple, Amazon, Reddit,
Pinterest, Snapchat, and X names and APIs are third-party products. Capability
references document interoperability and do not imply affiliation, endorsement,
or permission to bypass platform terms, access controls, policies, or review.
