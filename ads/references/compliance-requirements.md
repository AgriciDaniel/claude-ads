# Regulatory Compliance Requirements

**Verified:** 2026-08-25
**Refresh:** event-driven; re-check within 30 days of an applicable effective date
**Scope:** issue spotting and evidence collection, not legal advice

Do not apply a global checklist before establishing jurisdiction, role, data
flow, audience, product, and creative provenance. Laws and regulator guidance
change; a stale state-count table is not a compliance system.

## Intake

Capture:

- Advertiser, controller/business, processor/service-provider, agency, platform,
  and AI provider/deployer roles.
- Audience and operational geographies, including excluded locations.
- Product category, claims, endorsements, political content, and age exposure.
- Data collected, inferred, uploaded, disclosed, sold/shared, retained, and deleted.
- Consent, opt-out, preference-signal, access/deletion, and vendor-contract flows.
- AI-generated or manipulated text, image, audio, and video provenance.
- Applicable counsel decisions, regulator correspondence, and platform approvals.

Missing jurisdiction or data-flow evidence produces `needs_input`, not a pass.

## Current primary sources

| Area | Source | Retained fact |
| --- | --- | --- |
| EU AI Act | `eu-ai-act-article-50-official` — [European Commission transparency code](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content) and [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) | Article 50 transparency obligations apply from 2 August 2026; scope differs for providers and deployers |
| Digital Services Act | `eu-dsa-official` — [European Commission DSA overview](https://digital-strategy.ec.europa.eu/en/policies/digital-services-act) | Ads must be identifiable and include information about who placed them and why they are shown; platform duties differ by service type |
| California privacy | `cppa-regulations-official` — [CPPA laws and regulations](https://cppa.ca.gov/regulations/) | Adopted and proposed packages are distinct; consult the effective text rather than commentary |
| Health information | `hhs-tracking-guidance-official`: [HHS tracking guidance](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/hipaa-online-tracking/index.html) | HIPAA-regulated entities must assess tracking technologies when collected or disclosed information includes PHI; the page records a court-vacated portion of earlier guidance |
| US endorsements | `ftc-endorsement-guides-official`: [FTC Endorsement Guides FAQ](https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking) | Material connections and non-typical result claims require context-appropriate, clear disclosure/substantiation analysis |

The cited Article 50 transparency date is in effect as of the verification date. Do not convert it
into a claim that every AI-assisted advertisement requires the same label. Check
the actor, output type, use, exceptions, final Commission guidance, and platform
implementation. Proposed transition rules remain proposals until adopted.

## Data and privacy review

Map each event and audience field from collection to destination. For each step,
record purpose, legal basis or permission relied upon, consent state, sensitive
status, recipient, retention, deletion, security, and user-control mechanism.

Verify the actual applicable law and effective regulation for each jurisdiction.
Do not use a remembered count of US state privacy laws or a generic “GDPR/CCPA
compliant” label as evidence. Test preference signals and opt-outs end to end,
including downstream suppression and proof visible to the operator.

## Sensitive and regulated contexts

Escalate to counsel or the accountable compliance owner when the flow can include
health, financial, precise location, biometric, neural, child/teen, political,
employment, housing, credit, immigration, or other legally sensitive data.

For HIPAA-regulated entities and business associates, inspect HHS's current
tracking guidance and the court-order note on that page. Do not claim that every
visit to a public health-information page is PHI, and do not assume a privacy
notice alone authorizes disclosure.

## Claims, endorsements, and AI media

- Keep substantiation for express and implied objective claims.
- Disclose material connections in a way ordinary viewers can notice and understand.
- Compare testimonial results with generally expected results; a vague disclaimer
  does not repair an otherwise misleading impression.
- Preserve AI provenance and platform labels; assess Article 50 and local rules
  against the exact output and role.
- Review political and public-interest content under current election, platform,
  and jurisdiction rules before launch.

## Finding and escalation contract

Each finding states jurisdiction, actor, data/creative flow, current primary
source, observed evidence, applicability rationale, result, confidence, exposure,
owner, remediation, and re-check date. Keep legal exposure separate from account
health scoring.

Block a mutation when required consent/authorization, counsel decision,
certification, disclosure, data minimization, or jurisdiction evidence is absent.
Use `unknown` for unresolved applicability. Claude Ads may identify and document
the issue; the accountable owner or qualified counsel makes the legal decision.
