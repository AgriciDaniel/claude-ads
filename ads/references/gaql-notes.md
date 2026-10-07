# GAQL compatibility and accuracy notes

GAQL fields, compatibility rules, date constants, and API versions change. Treat
this file as query-design guidance, not a current field catalog. Field names in
the keyword section must be verified against the active Google Ads API resource
definitions and `google-ads-api-shared-sets-official`. Before executing
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
keywords in the same resource, separated by the immutable `negative` field. A
status filter alone can return both. Counting negatives as positive keywords
creates false zero-impression, keyword-volume, and self-blocking findings and can
produce a recommendation that would delete the account's negative keywords.

Build two inventories before any keyword control runs. Record both counts and the
exact queries or export files in the run manifest.

1. **Positive inventory.** Select only positive keyword criteria:

   ```sql
   SELECT campaign.id, campaign.status, ad_group.id, ad_group.status,
          ad_group_criterion.criterion_id, ad_group_criterion.status,
          ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type
   FROM ad_group_criterion
   WHERE ad_group_criterion.type = 'KEYWORD'
     AND ad_group_criterion.negative = FALSE
     AND ad_group_criterion.status != 'REMOVED'
   ```

   Scope campaign, ad group, and criterion status to the question under review.
2. **Negative inventory.** Create one row per negative and tag its scope:
   - ad-group negatives use `ad_group_criterion.negative = TRUE` and apply only
     to that ad group;
   - campaign negatives use `campaign_criterion.type = 'KEYWORD'` with
     `campaign_criterion.negative = TRUE` and apply to that campaign;
   - negative keyword lists use `shared_criterion` rows in a `shared_set` of type
     `NEGATIVE_KEYWORDS`, joined through enabled `campaign_shared_set` rows. An
     unattached list blocks nothing;
   - account-level negatives use `customer_negative_criterion` and apply only to
     eligible campaign inventory.

For exports, the Google Ads UI keyword report lists positive keywords; negatives
come from negative-keyword views and list exports. Split any bulk or Editor sheet
that mixes both using its criterion or match-type column. If an export cannot
distinguish positives from negatives, return `unknown` for the keyword inventory.

Join impression, click, cost, and conversion evidence to the positive inventory
by ad group ID and criterion ID. Negatives never enter a zero-impression count,
keyword-volume finding, or ad-group keyword total.

### Self-blocking conflicts

A positive keyword is blocked by its own account only when an in-scope negative
matches the positive's text under the negative's match type:

- negative exact: the same terms, in the same order, with no extra words;
- negative phrase: the negative terms appear contiguously and in order inside
  the positive, with any words before or after;
- negative broad: every term of the negative appears in the positive, in any order.

Compare case-insensitively after removing match-type punctuation. Negative
keywords do not expand to close variants, synonyms, or singular and plural forms.
Treat near-identical spellings as possible conflicts for review, not confirmed
blocks, unless current official rules and the account evidence establish a match.

In scope means an ad-group negative in the same ad group, a campaign negative in
the same campaign, a negative in a list attached to that campaign, or an
account-level negative for eligible inventory. A negative in a sibling ad group,
another campaign, or an unattached list does not block the positive.

A negative that removes only some searches a phrase or broad positive could match
is query routing, not proof that the positive is fully blocked. At most, report
the routing intent for owner confirmation.

Worked example: a general local-service ad group has three positive keywords and
four town-name phrase negatives that route town searches to separate ad groups.
The correct inventory is three positives, four negatives, and zero conflicts. A
seven-keyword inventory with four self-blocked zero-impression rows is the defect
pattern because it counted each negative as a positive. A positive containing one
of those town names in the general ad group is a possible real conflict only after
the negative's scope and match type are confirmed.

### Plausibility guards

Return a self-blocking or zero-impression finding as `unknown` and rebuild the
inventory when any of these conditions holds:

- a conflict pairs a criterion with itself;
- the number of self-blocked keywords equals the number of in-scope negatives;
- negatives exist and the reported keyword total equals positives plus negatives;
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
