# X Ads control reference

Catalog reviewed: 2026-10-07. Use the per-source and per-claim verification
dates in the control-plane ledgers. This date does not verify every control.

## Category model

This reference does not define an executable scoring profile. Bind a versioned
profile whose categories cover the applicable controls and whose weights total 100;
otherwise produce findings without a health score.

## Runtime evaluation contract

- Treat each row as an applicability-first evidence question. Missing evidence is
  `unknown`; unavailable or ineligible surfaces are `not_applicable`.
- Verify objective, placement, geography, measurement path, report definitions,
  policy, brand-safety controls, and account eligibility before evaluation.
- The registered source below grounds website conversion tracking only. Current
  CAPI, app/offline measurement, targeting, format, policy, API, and availability
  claims require additional dated official source IDs or account evidence.
- This reference is advisory and export-read only. It does not provide a live X API
  reader or mutation adapter.

## Controls

| ID | Category | Evidence question |
| --- | --- | --- |
| XA-M01 | Measurement | X Pixel, Conversions API, MMP, or offline source is declared and verified. |
| XA-M02 | Measurement | Conversion events avoid sensitive categories and comply with X data-use policy. |
| XA-M03 | Measurement | Identifiers, event values, and browser/server deduplication are documented. |
| XA-M04 | Measurement | App campaigns use a supported mobile measurement path. |
| XA-S01 | Structure | Campaign objective and optimization event match the business outcome. |
| XA-S02 | Structure | Campaign, line-item/ad-group, creative, and account eligibility are valid. |
| XA-A01 | Audience | Keyword, conversation, interest, follower-lookalike, geography, and first-party choices are evidence-based. |
| XA-A02 | Audience | Prospecting, retargeting, exclusions, and expansion avoid unintended overlap. |
| XA-C01 | Creative | Copy and media fit the selected format, placement, and landing-page promise. |
| XA-C02 | Creative | Creative diversity covers materially distinct hooks, concepts, and formats. |
| XA-C03 | Creative | Replies and conversation context are considered where the placement exposes them. |
| XA-B01 | Budget | Budget, bid, pacing, and optimization state are viable for available evidence. |
| XA-R01 | Reporting | Date window, attribution, currency, and metric definitions are consistent. |
| XA-R02 | Reporting | Organic signals remain separate from paid attribution and optimization claims. |
| XA-P01 | Policy | Brand-safety, adjacency, regulated-category, privacy, and account-status risks are reviewed. |
| XA-E01 | Experiment | Tests isolate one decision with a declared window and success measure. |

Results use `pass`, `fail`, `unknown`, or `not_applicable`. Unknown controls
reduce evidence coverage; unavailable, beta, premium, or ineligible features are
unscored opportunities.

## Registered official evidence

- `x-conversion-tracking`: [X website conversion tracking](https://help.x.com/en/business-and-advertising/about-conversion-tracking)

Official sources override this summary when they change. Unsupported controls stay
`unknown`; practitioner material may supplement but not replace official evidence.
