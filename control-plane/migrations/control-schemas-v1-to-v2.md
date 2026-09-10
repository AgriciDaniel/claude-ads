# Control schema migration: v1 to v2

## Ecosystem disposition ledger

Version 2.0.0 adds required public and canonical tracker snapshots, restricts
repository identifiers, removes unresolved decision and license states, and
requires at least one requirement ID per entry. Version 1 documents remain
valid only against `ecosystem-dispositions.v1.schema.json`.

The 2.0.1 checkout already emitted snapshot fields while still labeling the
ledger as 1.0.0, so that instance did not conform to the published v1 schema.
Version 2 makes the existing breaking shape explicit instead of rewriting v1.

To migrate, add both snapshot objects, replace `dependency-review` with a final
review disposition, replace `pending` license reviews with completed evidence,
and set `schema_version` to `2.0.0`.

## Release gate assessment

Version 2.0.0 adds the vulnerability-exception integrity check and renames the
stored ecosystem check to `ecosystem-ledger-integrity`. A v2 report contains
exactly eight checks. Version 1 reports remain valid only against
`release-gate-report.v1.schema.json`.

The 2.0.1 generator already emitted eight checks while labeling its report as
1.0.0, so those generated reports did not conform to the published v1 schema.
Consumers should regenerate candidate evidence under v2 rather than relabeling
old reports.

The ecosystem ledger check proves internal consistency of the frozen review
ledger. Current GitHub completeness is a remote CI responsibility and must not
be inferred from the stored ledger alone.
