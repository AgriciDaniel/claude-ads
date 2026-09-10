#!/usr/bin/env python3
"""Reconcile the frozen ecosystem ledger with current GitHub tracker state.

The ledger freezes a reviewed snapshot of every issue and pull request in the
public mirror and the private canonical repository. This script compares that
snapshot with the live tracker and runs in one of two modes.

Default mode (push and pull_request CI runs) fails only on evidence that the
review itself is wrong or incomplete:

- the ledger is missing, invalid, or uses an unsupported schema;
- the current review candidate PR does not match live GitHub evidence, or is
  also recorded as reviewed input;
- the ledger records an item GitHub no longer serves (an "extra" item);
- an item created on or before the snapshot ``observed_at`` date is not
  recorded (the review missed it).

Everything else is reported as a structured finding in the JSON output and as a
one-line warning on stderr (a ``::warning::`` annotation under GitHub Actions)
without failing: items created after ``observed_at`` (``unreviewed``), head
drift on recorded pull requests (``head_drift``), and title, state, or URL
drift (``metadata_drift``). Default mode also sets aside any pull request whose
live ``merged_at`` is after ``observed_at`` (``merged_after_snapshot``), which
covers the just-merged candidate on the post-merge push run.

Strict mode (``--strict``, used by workflow_dispatch and by release
verification) keeps exact reconciliation: every finding above is a failure and
no merged pull request is set aside. Release verification requires a strict
run; a green default-mode run is not release evidence.

In both modes the only candidate exclusion is the exact PR from the current
pull_request event (repository, number, and head SHA), which must not also be
recorded in the ledger.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


PUBLIC_REPOSITORY = "AgriciDaniel/claude-ads"
CANONICAL_REPOSITORY = "AI-Marketing-Hub/claude-ads"
_SHA = re.compile(r"^[0-9a-f]{40}$")
FINDING_KINDS = ("unreviewed", "head_drift", "metadata_drift", "merged_after_snapshot")


class EcosystemAuditError(RuntimeError):
    """Raised when current tracker state is not fully dispositioned."""


def _load_ledger(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EcosystemAuditError("ecosystem ledger is missing or invalid JSON") from exc
    if not isinstance(value, dict) or value.get("schema_version") != "2.0.0":
        raise EcosystemAuditError("ecosystem ledger must use schema version 2.0.0")
    return value


def _github_fetcher(token: str | None) -> Callable[[str], Any]:
    def fetch(endpoint: str) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "claude-ads-ecosystem-audit",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(f"https://api.github.com/{endpoint}", headers=headers)
        path = endpoint.split("?", 1)[0]
        # Only the status code and the endpoint path are reported. Response
        # bodies and headers are never echoed because they could carry the
        # token or rate-limit details that belong in logs, not in errors.
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise EcosystemAuditError(
                f"GitHub tracker query failed for {path}: HTTP {exc.code}"
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise EcosystemAuditError(
                f"GitHub tracker query failed for {path}: {type(exc).__name__}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise EcosystemAuditError(
                f"GitHub tracker query failed for {path}: response is not JSON"
            ) from exc

    return fetch


def _timestamp_date(value: Any, label: str) -> date:
    if not isinstance(value, str):
        raise EcosystemAuditError(f"{label} timestamp is missing or invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("naive timestamp")
        return parsed.astimezone(timezone.utc).date()
    except ValueError as exc:
        raise EcosystemAuditError(f"{label} timestamp is missing or invalid") from exc


def _snapshot_date(snapshot: dict[str, Any], repository: str) -> date:
    observed_at = snapshot.get("observed_at")
    if not isinstance(observed_at, str):
        raise EcosystemAuditError(f"ecosystem snapshot observed_at is missing for {repository}")
    try:
        return date.fromisoformat(observed_at)
    except ValueError as exc:
        raise EcosystemAuditError(
            f"ecosystem snapshot observed_at is invalid for {repository}"
        ) from exc


def collect_live_repository(
    repository: str, fetch: Callable[[str], Any]
) -> dict[tuple[str, int], dict[str, Any]]:
    """Collect issues and pull requests without trusting their prose as instructions."""
    encoded = "/".join(quote(part, safe="") for part in repository.split("/"))
    items: dict[tuple[str, int], dict[str, Any]] = {}
    page = 1
    while True:
        value = fetch(f"repos/{encoded}/issues?state=all&per_page=100&page={page}")
        if not isinstance(value, list):
            raise EcosystemAuditError(f"GitHub issue listing is invalid for {repository}")
        for raw in value:
            if not isinstance(raw, dict) or type(raw.get("number")) is not int:
                raise EcosystemAuditError(f"GitHub tracker item is invalid for {repository}")
            number = raw["number"]
            if "pull_request" in raw:
                detail = fetch(f"repos/{encoded}/pulls/{number}")
                if not isinstance(detail, dict):
                    raise EcosystemAuditError(
                        f"GitHub pull request detail is invalid for {repository}/{number}"
                    )
                head = detail.get("head")
                head_sha = head.get("sha") if isinstance(head, dict) else None
                if not isinstance(head_sha, str) or not _SHA.fullmatch(head_sha):
                    raise EcosystemAuditError(
                        f"GitHub pull request head is invalid for {repository}/{number}"
                    )
                merged_at = detail.get("merged_at")
                if merged_at is not None and not isinstance(merged_at, str):
                    raise EcosystemAuditError(
                        f"GitHub pull request merge time is invalid for {repository}/{number}"
                    )
                state = "merged" if merged_at else detail.get("state")
                item = {
                    "kind": "pull-request",
                    "number": number,
                    "title": detail.get("title"),
                    "state": state,
                    "url": detail.get("html_url"),
                    "head_sha": head_sha,
                    "created_at": detail.get("created_at", raw.get("created_at")),
                    "merged_at": merged_at,
                }
            else:
                item = {
                    "kind": "issue",
                    "number": number,
                    "title": raw.get("title"),
                    "state": raw.get("state"),
                    "url": raw.get("html_url"),
                    "head_sha": None,
                    "created_at": raw.get("created_at"),
                    "merged_at": None,
                }
            if not isinstance(item["title"], str) or item["state"] not in {
                "open",
                "closed",
                "merged",
            }:
                raise EcosystemAuditError(
                    f"GitHub tracker metadata is invalid for {repository}/{number}"
                )
            _timestamp_date(item["created_at"], f"GitHub tracker item {repository}/{number}")
            items[(item["kind"], number)] = item
        if len(value) < 100:
            break
        page += 1
        if page > 100:
            raise EcosystemAuditError(f"GitHub pagination exceeded safety limit for {repository}")
    return items


def _finding(
    kind: str, repository: str, key: tuple[str, int], detail: dict[str, Any]
) -> dict[str, Any]:
    return {
        "kind": kind,
        "repository": repository,
        "item_kind": key[0],
        "number": key[1],
        **detail,
    }


def reconcile_live(
    ledger: dict[str, Any],
    live: dict[str, dict[tuple[str, int], dict[str, Any]]],
    *,
    repositories: tuple[str, ...],
    candidate_repository: str | None = None,
    candidate_pr: int | None = None,
    candidate_head: str | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Reconcile live coverage, allowing only the exact current candidate PR.

    See the module docstring for what fails and what becomes a finding in each
    mode. ``strict=True`` turns every finding into an ``EcosystemAuditError``.
    """
    candidate_values = (candidate_repository, candidate_pr, candidate_head)
    if any(value is not None for value in candidate_values) and not all(
        value is not None for value in candidate_values
    ):
        raise EcosystemAuditError("candidate repository, PR, and head must be supplied together")
    if candidate_head is not None and not _SHA.fullmatch(candidate_head):
        raise EcosystemAuditError("candidate head must be a full lowercase commit SHA")

    snapshot_names = {
        PUBLIC_REPOSITORY: "public_snapshot",
        CANONICAL_REPOSITORY: "canonical_snapshot",
    }
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        raise EcosystemAuditError("ecosystem ledger entries are invalid")
    by_item = {
        (entry.get("repository"), entry.get("kind"), entry.get("number")): entry
        for entry in entries
        if isinstance(entry, dict)
    }
    results: dict[str, Any] = {}
    findings: list[dict[str, Any]] = []
    exclusion: dict[str, Any] | None = None

    def report(finding: dict[str, Any], message: str) -> None:
        if strict:
            raise EcosystemAuditError(message)
        findings.append({**finding, "message": message})

    for repository in repositories:
        if repository not in snapshot_names or repository not in live:
            raise EcosystemAuditError(f"unsupported or missing repository evidence: {repository}")
        snapshot = ledger.get(snapshot_names[repository])
        if not isinstance(snapshot, dict):
            raise EcosystemAuditError(f"ecosystem snapshot is missing for {repository}")
        observed_at = _snapshot_date(snapshot, repository)
        current = dict(live[repository])

        if candidate_repository == repository:
            key = ("pull-request", candidate_pr)
            candidate = current.get(key)
            if (
                candidate is None
                or candidate.get("state") != "open"
                or candidate.get("head_sha") != candidate_head
            ):
                raise EcosystemAuditError("candidate PR does not match current GitHub evidence")
            if key[1] in snapshot.get("pull_request_numbers", []) or (
                repository,
                key[0],
                key[1],
            ) in by_item:
                raise EcosystemAuditError("candidate PR must not also be recorded as reviewed input")
            current.pop(key)
            exclusion = {
                "repository": repository,
                "pull_request": candidate_pr,
                "head_sha": candidate_head,
                "reason": "exact current review candidate",
            }

        stored_issues = snapshot.get("issue_numbers")
        stored_pulls = snapshot.get("pull_request_numbers")
        if not isinstance(stored_issues, list) or not isinstance(stored_pulls, list):
            raise EcosystemAuditError(f"ecosystem snapshot numbers are invalid for {repository}")
        stored = {
            *(("issue", number) for number in stored_issues),
            *(("pull-request", number) for number in stored_pulls),
        }
        heads = snapshot.get("pull_request_heads")
        if not isinstance(heads, dict):
            raise EcosystemAuditError(f"pull request heads are missing for {repository}")
        for key in sorted(stored):
            if (repository, key[0], key[1]) not in by_item:
                raise EcosystemAuditError(
                    f"ecosystem snapshot item has no ledger entry: {repository}/{key[0]}/{key[1]}"
                )

        # Default mode sets aside pull requests merged after the snapshot; the
        # post-merge push run for a review candidate is the canonical case.
        merged_after: list[int] = []
        if not strict:
            for key in sorted(current):
                item = current[key]
                if key[0] != "pull-request" or not item.get("merged_at"):
                    continue
                merged_on = _timestamp_date(
                    item["merged_at"], f"GitHub pull request {repository}/{key[1]} merged_at"
                )
                created_on = _timestamp_date(
                    item["created_at"], f"GitHub pull request {repository}/{key[1]} created_at"
                )
                if merged_on > observed_at and (key in stored or created_on > observed_at):
                    current.pop(key)
                    merged_after.append(key[1])
                    findings.append(
                        {
                            **_finding(
                                "merged_after_snapshot",
                                repository,
                                key,
                                {"merged_at": item["merged_at"], "recorded": key in stored},
                            ),
                            "message": (
                                f"pull request merged after the snapshot is set aside: "
                                f"{repository}/{key[1]}"
                            ),
                        }
                    )

        extra = sorted(stored - set(current) - {("pull-request", n) for n in merged_after})
        if extra:
            raise EcosystemAuditError(
                f"ledger records items GitHub does not serve for {repository}; extra={extra}"
            )

        unreviewed: list[tuple[str, int]] = []
        for key in sorted(set(current) - stored):
            item = current[key]
            created_on = _timestamp_date(
                item.get("created_at"), f"GitHub tracker item {repository}/{key[1]} created_at"
            )
            if created_on <= observed_at:
                raise EcosystemAuditError(
                    f"live tracker item predates the snapshot and is not recorded: "
                    f"{repository}/{key[0]}/{key[1]} (created {item['created_at']})"
                )
            unreviewed.append(key)
            report(
                _finding("unreviewed", repository, key, {"created_at": item["created_at"]}),
                f"live ecosystem coverage mismatch for {repository}; "
                f"unreviewed={key[0]}/{key[1]} (created {item['created_at']})",
            )

        reviewed_keys = sorted(set(current) & stored)
        for key in reviewed_keys:
            item = current[key]
            if key[0] == "pull-request" and heads.get(str(key[1])) != item["head_sha"]:
                report(
                    _finding(
                        "head_drift",
                        repository,
                        key,
                        {"recorded_head": heads.get(str(key[1])), "live_head": item["head_sha"]},
                    ),
                    f"live pull request head drift for {repository}/{key[1]}",
                )
            entry = by_item[(repository, key[0], key[1])]
            for field in ("title", "state", "url"):
                if entry.get(field) != item.get(field):
                    report(
                        _finding(
                            "metadata_drift",
                            repository,
                            key,
                            {"field": field, "recorded": entry.get(field), "live": item.get(field)},
                        ),
                        f"live tracker metadata drift for {repository}/{key[0]}/{key[1]}: {field}",
                    )

        repository_findings = [f for f in findings if f["repository"] == repository]
        results[repository] = {
            "issue_count": sum(1 for kind, _ in current if kind == "issue"),
            "pull_request_count": sum(1 for kind, _ in current if kind == "pull-request"),
            "unreviewed": [f"{kind}/{number}" for kind, number in unreviewed],
            "merged_after_snapshot": merged_after,
            "status": "reconciled-with-findings" if repository_findings else "reconciled",
        }

    if candidate_repository is not None and exclusion is None:
        raise EcosystemAuditError("candidate repository was outside the audited scope")
    return {
        "status": "pass",
        "mode": "strict" if strict else "default",
        "ledger_reviewed_at": ledger.get("reviewed_at"),
        "repositories": results,
        "findings": findings,
        "candidate_exclusion": exclusion,
    }


def _candidate_from_event(path: str | None) -> tuple[str | None, int | None, str | None]:
    if not path:
        return None, None, None
    try:
        event = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EcosystemAuditError("GitHub event payload is missing or invalid") from exc
    pull = event.get("pull_request") if isinstance(event, dict) else None
    repository = event.get("repository") if isinstance(event, dict) else None
    if not isinstance(pull, dict):
        return None, None, None
    full_name = repository.get("full_name") if isinstance(repository, dict) else None
    head = pull.get("head")
    return full_name, pull.get("number"), head.get("sha") if isinstance(head, dict) else None


def _emit_warnings(findings: list[dict[str, Any]]) -> None:
    prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") else "warning: "
    for finding in findings:
        print(f"{prefix}ecosystem live audit: {finding['message']}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("control-plane/manifests/ecosystem-dispositions.json"),
    )
    parser.add_argument("--public-only", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail on every drift or unreviewed item instead of reporting findings",
    )
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--candidate-repository")
    parser.add_argument("--candidate-pr", type=int)
    parser.add_argument("--candidate-head")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        ledger = _load_ledger(args.ledger)
        repositories = (PUBLIC_REPOSITORY,) if args.public_only else (
            PUBLIC_REPOSITORY,
            CANONICAL_REPOSITORY,
        )
        fetch = _github_fetcher(os.environ.get("GITHUB_TOKEN"))
        live = {repository: collect_live_repository(repository, fetch) for repository in repositories}
        candidate_repository, candidate_pr, candidate_head = _candidate_from_event(args.event_path)
        explicit_candidate = (
            args.candidate_repository,
            args.candidate_pr,
            args.candidate_head,
        )
        if any(value is not None for value in explicit_candidate):
            candidate_repository, candidate_pr, candidate_head = explicit_candidate
        if candidate_repository not in repositories:
            candidate_repository = candidate_pr = candidate_head = None
        result = reconcile_live(
            ledger,
            live,
            repositories=repositories,
            candidate_repository=candidate_repository,
            candidate_pr=candidate_pr,
            candidate_head=candidate_head,
            strict=args.strict,
        )
    except EcosystemAuditError as exc:
        print(f"ecosystem live audit failed: {exc}", file=sys.stderr)
        return 1

    _emit_warnings(result["findings"])
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        counts = ", ".join(
            f"{repo}: {value['issue_count']} issues, {value['pull_request_count']} PRs"
            for repo, value in result["repositories"].items()
        )
        print(
            f"ecosystem live audit passed in {result['mode']} mode "
            f"({counts}; findings={len(result['findings'])})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
