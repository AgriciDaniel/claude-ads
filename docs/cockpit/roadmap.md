# Cockpit roadmap

The first companion is an optional daily workbench over local Claude Ads run
artifacts, with a synthetic guided demo. It exposes recorded workflow state,
evidence and source freshness, indexed input validation, comparable run changes,
and local report receipts. It grants no advertising account permissions.

The following are proposals outside v1. They are not installed capabilities,
commitments, enabled scoring profiles, or evidence of market readiness.

| Proposal | Useful decision | Evidence needed before implementation |
| --- | --- | --- |
| Measurement comparisons | Which conversion definitions can be compared? | Explicit attribution windows, definitions, currency, identity and overlap rules; side-by-side output when totals are incompatible. |
| Experiment workbench | Is an experiment ready to run or read out? | Canonical experiment setup/readout artifacts, sample assumptions, stopping rules and uncertainty. No automatic campaign changes. |
| Freshness queue | Which load-bearing claims need reverification first? | Source/claim dependency links, effective dates and an explicit research workflow. A queue must not convert an expired claim to current. |
| Draft change rehearsal | What would an approved change affect? | Versioned mutation plan, before/after diff, ceilings, learning/policy impact and rollback. Simulation must remain distinct from execution. |
| Campaign learning log | What was learned across successive runs? | Immutable run references, owner decisions, measurement windows and a correction/supersession chain. Missing retests cannot mean resolved. |
| Budget sandbox | How do alternative assumptions affect a plan? | Transparent inputs, margin/lag constraints, sensitivity ranges and labeled assumptions. No uplift guarantees or live budget writes. |
| Synthetic proof cards | Can a buyer inspect a reproducible example? | Sanitized fixtures, explicit synthetic labeling, artifact hashes and recorded checks. Fixture behavior must not impersonate a real client result. |

Each proposal needs a separate scoped contract and acceptance evidence. Native
host rendering and compatibility checks for the v1 companion remain separate
from these proposals. The product release gates continue to apply.
