# GAQL compatibility and accuracy notes

GAQL fields, compatibility rules, date constants, and API versions change. Treat
this file as query-design guidance, not a current field catalog. Field names below
were checked against the Google Ads API v25 resource definitions
(`google-ads-api-criteria-v25`) and shared-set guide
(`google-ads-api-shared-sets-official`). Before executing
a query, record the customer ID, API version, query resource, selected fields,
date window, and the current Google Ads API field/reference source ID. A runtime
`INVALID_ARGUMENT` or `UNRECOGNIZED_FIELD` is `needs_input` for query repair; it
must not be silently converted into an empty dataset.

## Compatibility discovery

Use the current official Google Ads API documentation and field metadata for the
selected version to validate:

- whether each selected and filtered field is selectable with the primary resource;
- whether segments change row grain or conflict with metrics;
- whether the chosen date constant exists, otherwise use explicit dates;
- whether resource status is available in-query or must be joined or filtered
  after retrieval;
- pagination, partial-failure, quota, currency-unit, timezone, and manager-account
  behavior.

Do not carry a query forward solely because it worked with a prior API version.

## Keyword Deduplication

**Problem:** `keyword_view + segments.date DURING LAST_30_DAYS` returns one row per keyword per day. A keyword active 5 days = 5 rows. Same keyword with BROAD + PHRASE = 2 rows per day = 10 total.

**Fix:** Deduplicate by `(ad_group_id + keyword_text + match_type)` at fetch time. Aggregate metrics (impressions, clicks, cost, conversions) across duplicate rows.

**Alternative:** Remove `segments.date` from GAQL queries entirely to eliminate date-level duplication at source.

Record the resulting row grain in the run manifest. Downstream checks may consume
the normalized keyword grain only after fixture or account-level reconciliation.

## Keyword inventory and negative keywords

`ad_group_criterion` and `campaign_criterion` store positive and negative
keywords in the same resource, separated only by the immutable `negative` field
(CLM-0214). A status filter alone returns both. Counting negatives as keywords
produces false zero-impression, keyword-volume, and self-blocking findings, and a
"remove the inert positives" recommendation that would actually delete the
account's negatives.

Build two inventories before any keyword control runs, and record both counts and
the exact queries or export files in the run manifest.

1. **Positive inventory.** Only positive keyword criteria:

   ```sql
   SELECT campaign.id, campaign.status, ad_group.id, ad_group.status,
          ad_group_criterion.criterion_id, ad_group_criterion.status,
          ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type
   FROM ad_group_criterion
   WHERE ad_group_criterion.type = 'KEYWORD'
     AND ad_group_criterion.negative = FALSE
     AND ad_group_criterion.status != 'REMOVED'
   ```

   Scope campaign, ad group, and criterion status to the question (see Filter
   Scope Best Practices).
2. **Negative inventory.** One row per negative, tagged with the scope it applies to:
   - ad-group negatives: the same resource with `ad_group_criterion.negative = TRUE`;
     scope is that ad group only;
   - campaign negatives: `campaign_criterion` with `campaign_criterion.type =
     'KEYWORD'` and `campaign_criterion.negative = TRUE`; scope is every ad group
     in that campaign;
   - negative keyword lists: `shared_criterion` keywords in a `shared_set` of type
     `NEGATIVE_KEYWORDS`, joined to campaigns through `campaign_shared_set` rows
     with status `ENABLED`; scope is every ad group in each attached campaign. An
     unattached list blocks nothing;
   - account-level negatives: the `ACCOUNT_LEVEL_NEGATIVE_KEYWORDS` shared set,
     attached through `customer_negative_criterion`; scope is eligible Search and
     Shopping inventory in the relevant campaign types (CLM-0213).

For exports, the Google Ads UI keyword report lists positive keywords; negatives
come from the negative-keyword views and list exports. A bulk or Editor sheet that
mixes both must be split on its criterion or match-type column before counting. If
an export cannot distinguish positives from negatives, the keyword inventory is
`unknown`, not complete.

Join impression, click, cost, and conversion evidence to the positive inventory by
ad group ID and criterion ID. Negatives never accrue impressions, so they never
enter a zero-impression count (G-KW1), a keyword-volume finding, or an ad-group
keyword total.

### Self-blocking conflicts

A positive keyword is blocked by its own account only when an in-scope negative
matches the positive's text under the negative's match type (CLM-0213):

- negative exact: the same terms, in the same order, with no extra words;
- negative phrase: the negative's terms appear contiguously and in order inside
  the positive, with any words before or after;
- negative broad: every term of the negative appears in the positive, in any order.

Compare case-insensitively after removing match-type punctuation (`[ ]`, `" "`).
Negatives do not expand to close variants, synonyms, or singular and plural forms,
so a negative `tyre` does not block `tyres`. Google states that casing and
misspellings are handled automatically, so report a near-identical spelling as a
possible conflict for review, not as a confirmed block.

In scope means an ad-group negative in the same ad group, a campaign negative in
the same campaign, a negative in a list attached to that campaign, or the
account-level list for an eligible campaign type. A negative in a sibling ad
group, another campaign, or an unattached list never blocks the positive.

A negative that removes only some of the searches a phrase or broad positive could
match is query routing, not self-blocking: the positive still serves every search
that lacks the negative's terms. Report it, at most, as routing intent to confirm
with the owner.

Worked example (anonymized mobile tyre fitting account). A general ad group holds
the positives `[mobile tyre fitting]`, `"mobile tyre fitting near me"`, and
`"24 hour mobile tyre fitting"`, plus the ad-group phrase negatives `york`,
`leeds`, `harrogate`, and `selby`, so town searches route to the town ad groups.

- Correct result: 3 positives, 4 negatives, 0 conflicts, and 0 negatives in any
  zero-impression count.
- Defect pattern: 7 "enabled keywords", 4 of them "self-blocked" with zero
  impressions, and a recommendation to remove them, which would delete the
  routing negatives and send town searches to the general ad group.
- A genuine conflict: a positive `[mobile tyre fitting york]` added to that same
  general ad group. The phrase negative `york` matches its text, so it cannot serve
  there; the fix is to move the keyword or narrow the negative, with owner approval.

### Plausibility guards

Return a self-blocking or zero-impression finding as `unknown`, and rebuild the
inventory, when any of these holds:

- a "conflict" pairs a criterion with itself or with a negative of identical text
  and scope;
- the number of self-blocked keywords equals the number of in-scope negatives;
- negatives exist in scope and the reported keyword total equals positives plus
  negatives;
- the inventory query, file, or export column that distinguishes negatives is not
  recorded in the run manifest.

## Filter Scope Best Practices

Scope status to the question being answered. A current-serving health view normally
separates enabled, paused, and removed entities. A historical change, overlap, or
rollback investigation may require paused entities. Never describe the account as
complete when the query intentionally excludes a status, and never assume a fixed
lookback is suitable for every conversion lag or business cycle.

## Error Handling

Track which data fetches failed and why. Report as a G-SYS1 diagnostic:
- List all failed data sources with error messages
- Provide per-check context on which checks were skipped due to missing data
- Never silently skip checks; always explain why data is unavailable

## Historical match-type interpretation

Do not infer legacy Broad Match Modified behavior or advertiser intent from the
current `BROAD` enum, bidding strategy, or absence of a `+` prefix. Inspect dated
change history, search terms, current matching behavior, campaign controls, and
owner intent. If that evidence is unavailable, report the historical classification
as `unknown`; do not turn it into a failure or an automated negative-keyword action.
