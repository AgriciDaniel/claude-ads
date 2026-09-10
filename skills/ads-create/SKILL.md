---
name: ads-create
description: "Create source-grounded paid-ad campaign concepts, messaging, copy, creative briefs, and production plans from a validated brand profile, campaign objective, platform requirements, and optional audit evidence. Triggers on: campaign brief, campaign concepts, create a campaign, ad concepts, ad copy, ad messaging, creative brief, headlines, descriptions."
---

# Campaign Concepts and Copy

1. Load the validated setup/brand profile, objective, audience, offer, proof,
   platform/placement requirements, policy context, and optional audit findings.
2. Separate factual claims, operator-approved claims, and creative hypotheses.
3. For Meta work, collect the account, Pixel, and conversion cold-start
   dimensions per the contract in `skills/ads-meta/SKILL.md`. When any
   dimension is cold or `unknown`, state that in the brief, do not reuse
   mature-account creative benchmarks or performance claims, and never label
   existing creative bad merely because the Pixel is new.
4. Generate materially distinct strategic concepts, not cosmetic rewrites.
5. For each concept, define insight, promise, proof, hook, narrative, CTA, objections,
   platform adaptations, destination, and experiment hypothesis.
6. Validate copy limits and policy against current platform references. Load only
   the active files among `ads/references/google-creative-specs.md`,
   `meta-creative-specs.md`, `youtube-creative-specs.md`,
   `linkedin-creative-specs.md`, `tiktok-creative-specs.md`, and
   `microsoft-creative-specs.md`; use the dated source ledger for every current
   specification claim.
7. Return a versioned creative brief and copy deck inside the run directory.

Do not invent testimonials, certifications, scarcity, prices, outcomes, or regulated
claims. Human review remains required before production or launch.
