# Meta Ads Ranking Architecture

**Verified:** 2026-08-26
**Refresh due:** 2026-09-25
**Evidence status:** first-party architecture awareness; not an optimization threshold

This reference retains only architecture that Meta has described in current
first-party material. It does not infer hidden auction behavior or turn
vendor-reported uplifts into expected account results.

## Current sources

- `meta-andromeda-engineering-official` — [Meta Andromeda engineering article](https://engineering.fb.com/2024/12/02/production-engineering/meta-andromeda-advantage-automation-next-gen-personalized-ads-retrieval-engine/), published 2024-12-02.
- `meta-ai-ads-ranking-official` — [Meta: 2026 AI Drives Performance](https://about.fb.com/news/2026/01/2026-ai-drives-performance/), published 2026-01-28.
- `meta-gem-training-official`: [Meta GEM training and architecture](https://engineering.fb.com/2026/08/03/ml-applications/training-gem-at-llm-scale-meta-ads-recommendation-foundation-model/), published 2026-08-03.
- `meta-sequence-ranking-official`: [Meta multi-stage sequence architecture](https://engineering.fb.com/2026/08/05/ml-applications/from-user-sequences-to-scaling-laws-a-multi-stage-architecture-for-metas-ads-ranking/), published 2026-08-05.

All are Meta-authored sources. Architecture descriptions are high-confidence
evidence of what Meta publicly states. Performance lifts are vendor-supplied and
not independently verified by Claude Ads.

## What is supported

Meta describes ad selection as a multi-stage recommendation system. Its
engineering article identifies Andromeda as the retrieval stage that selects a
smaller candidate set from a much larger eligible pool before later ranking.
The article discusses co-design across models, systems, and hardware.

Meta's January 2026 company post describes GEM as an ads ranking model, a
sequence-learning architecture using longer behavior sequences and additional
organic engagement data, and Meta Lattice as a model that consolidated ranking
across additional Facebook surfaces. These are distinct from creative-generation
features.

Meta's August 2026 engineering posts further describe GEM as the central ads
recommendation foundation model and document a two-stage sequence architecture
that separates offline user modeling from online ranking. They do not establish
an advertiser-facing campaign structure, creative quota, or optimization rule.

Meta also reports performance changes from its deployments. Preserve those
numbers only as labeled vendor evidence when a user explicitly needs product
research; do not use them as forecasts, pass criteria, or reasons to restructure
an account.

## Audit implications

Architecture awareness supports questions, not automatic findings:

- Are optimization events valid, timely, deduplicated, and aligned to accepted
  business value?
- Does the account provide creative variants that are meaningfully different for
  its strategy and placements, based on observed asset-level results?
- Are placement, audience, and destination controls intentional and policy-safe?
- Is campaign structure solving a real constraint, or merely following an
  architecture narrative?
- Did an automation or creative change improve marginal accepted outcomes in a
  comparable, lag-mature window?

Do not prescribe a fixed number of creative angles, campaign count, campaign
age, audience width, or conversion threshold from these sources. Meta's system
architecture does not prove a universal account configuration.

## Unsupported or demoted concepts

The prior reference described an “ARM” layer, an exact four-layer linear pipeline,
fixed candidate counts, and numerous 2026 performance thresholds using
practitioner recaps. Those claims are omitted because current first-party support
was not established for this source pack. Reintroduce one only with a direct,
dated first-party source, clear scope, and a non-prescriptive audit use.

Likewise, terms such as “creative-similarity suppression,” guaranteed rewards for
broad targeting, or a minimum creative count are hypotheses until demonstrated
by account evidence or current official documentation.

The April 2026 issue proposal cited practitioner articles, not a current Meta
source. Its fixed one-to-two campaign maximum, fixed ad-set counts, mandatory
Advantage+ adoption, four-by-four creative framework, and CPMr prescription are
therefore not product rules in Claude Ads. Reconsider any one of them only when
current first-party evidence and the account's own results support the specific
decision.

## Finding contract

When architecture is relevant, cite the source ID and distinguish:

- `observed`: account configuration or performance evidence.
- `platform-stated`: Meta's documented architecture or reported result.
- `inference`: a testable account-specific hypothesis.
- `unknown`: hidden system behavior or missing evidence.

Only observed account problems become health findings. Product awareness and
vendor-reported uplifts remain unscored context.
