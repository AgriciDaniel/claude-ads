# Ecosystem Requirement Index

The ecosystem disposition ledger maps user reports and proposed changes to
these stable requirements. A disposition records intent; implementation still
requires executable verification.

| ID | Requirement |
|---|---|
| `REQ-INS-001` | Installation resolves the correct authorized public or private source without embedded private URLs in public instructions. |
| `REQ-PKG-001` | Release archives use portable paths and pass upload, extraction, manifest, and checksum tests. |
| `REQ-PLT-001` | Meta intake detects account, pixel, and conversion cold starts and adapts recommendations. |
| `REQ-PLT-002` | Recommendations are limited to actions supported by the current platform surface. |
| `REQ-INT-001` | Connectors declare and discover current API versions and capabilities; broken or sunset integrations stay disabled. |
| `REQ-SEC-001` | Network and browser access resist SSRF, redirects, rebinding, parser differentials, and hostile subresources. |
| `REQ-SEC-002` | Secret and sensitive-artifact ignores and scans cover common logs, databases, credentials, and local configuration. |
| `REQ-SEC-003` | Install and release flows avoid unverified remote execution and silent global environment mutation. |
| `REQ-SEC-004` | Every output and archive path is contained, normalized, symlink-safe, and traversal-safe. |
| `REQ-SUP-001` | Security reporting has a working private contact/advisory path. |
| `REQ-MKT-001` | Marketplace names and install identifiers are normalized and tested across supported filesystems. |
| `REQ-PLT-003` | Meta automation guidance is current, source-grounded, and does not freeze transient product behavior into timeless rules. |
| `REQ-PLT-004` | Apple Ads has a first-class platform contract. |
| `REQ-PLT-005` | Google audit and planning cover negative-keyword research with evidence and applicability rules. |
| `REQ-PLT-006` | Google audit distinguishes same-campaign Search plus DSA overlap and cross-campaign keyword duplication from Search plus PMax overlap, with evidence and applicability rules. |
| `REQ-EVL-001` | Skills contain observable validation checkpoints and pass failure-derived evaluations. |
| `REQ-CI-001` | CI produces security analysis, dependency evidence, an SBOM, and release attestations where supported. |
| `REQ-WIN-001` | Advertised Windows install/uninstall paths pass the supported PowerShell matrix. |
| `REQ-CRT-001` | Competitor and creative research may use lawful X organic signals with source and confidence labels. |
| `REQ-FIN-001` | Performance recommendations connect spend, margin, LTV, CAC, incrementality, and confidence without unsupported certainty. |
| `REQ-DOC-001` | Counts and capability documentation are generated from current manifests rather than maintained by hand. |
| `REQ-SCP-001` | Product scope excludes unrelated web apps, customer campaigns, white-label assets, and client data. |
| `REQ-DEP-001` | Dependency changes are reviewed after the v2 dependency model is fixed and must pass the full matrix. |
