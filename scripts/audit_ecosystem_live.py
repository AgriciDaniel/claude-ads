#!/usr/bin/env python3
"""Reconcile the frozen ecosystem ledger with current GitHub tracker state."""

from __future__ import annotations

import argparse
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
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise EcosystemAuditError(
                f"GitHub tracker query failed for {endpoint.split('?', 1)[0]}"
            ) from exc

    return fetch


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
                state = "merged" if detail.get("merged_at") else detail.get("state")
                item = {
                    "kind": "pull-request",
                    "number": number,
                    "title": detail.get("title"),
                    "state": state,
                    "url": detail.get("html_url"),
                    "head_sha": head_sha,
                }
            else:
                item = {
                    "kind": "issue",
                    "number": number,
                    "title": raw.get("title"),
                    "state": raw.get("state"),
                    "url": raw.get("html_url"),
                    "head_sha": None,
                }
            if not isinstance(item["title"], str) or item["state"] not in {
                "open",
                "closed",
                "merged",
            }:
                raise EcosystemAuditError(
                    f"GitHub tracker metadata is invalid for {repository}/{number}"
                )
            items[(item["kind"], number)] = item
        if len(value) < 100:
            break
        page += 1
        if page > 100:
            raise EcosystemAuditError(f"GitHub pagination exceeded safety limit for {repository}")
    return items


def reconcile_live(
    ledger: dict[str, Any],
    live: dict[str, dict[tuple[str, int], dict[str, Any]]],
    *,
    repositories: tuple[str, ...],
    candidate_repository: str | None = None,
    candidate_pr: int | None = None,
    candidate_head: str | None = None,
) -> dict[str, Any]:
    """Require exact live coverage, allowing only the exact current candidate PR."""
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
    exclusion: dict[str, Any] | None = None

    for repository in repositories:
        if repository not in snapshot_names or repository not in live:
            raise EcosystemAuditError(f"unsupported or missing repository evidence: {repository}")
        snapshot = ledger.get(snapshot_names[repository])
        if not isinstance(snapshot, dict):
            raise EcosystemAuditError(f"ecosystem snapshot is missing for {repository}")
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

        live_issues = sorted(number for kind, number in current if kind == "issue")
        live_pulls = sorted(number for kind, number in current if kind == "pull-request")
        stored_issues = snapshot.get("issue_numbers")
        stored_pulls = snapshot.get("pull_request_numbers")
        if live_issues != stored_issues or live_pulls != stored_pulls:
            missing = sorted(set(current) - {
                *(('issue', number) for number in stored_issues or []),
                *(('pull-request', number) for number in stored_pulls or []),
            })
            extra = sorted({
                *(('issue', number) for number in stored_issues or []),
                *(('pull-request', number) for number in stored_pulls or []),
            } - set(current))
            raise EcosystemAuditError(
                f"live ecosystem coverage mismatch for {repository}; missing={missing}, extra={extra}"
            )

        heads = snapshot.get("pull_request_heads")
        if not isinstance(heads, dict):
            raise EcosystemAuditError(f"pull request heads are missing for {repository}")
        for number in live_pulls:
            if heads.get(str(number)) != current[("pull-request", number)]["head_sha"]:
                raise EcosystemAuditError(
                    f"live pull request head drift for {repository}/{number}"
                )

        for key, item in current.items():
            entry = by_item.get((repository, key[0], key[1]))
            if entry is None:
                raise EcosystemAuditError(f"live tracker item is not dispositioned: {repository}/{key}")
            for field in ("title", "state", "url"):
                if entry.get(field) != item.get(field):
                    raise EcosystemAuditError(
                        f"live tracker metadata drift for {repository}/{key[0]}/{key[1]}: {field}"
                    )

        results[repository] = {
            "issue_count": len(live_issues),
            "pull_request_count": len(live_pulls),
            "status": "reconciled",
        }

    if candidate_repository is not None and exclusion is None:
        raise EcosystemAuditError("candidate repository was outside the audited scope")
    return {
        "status": "pass",
        "ledger_reviewed_at": ledger.get("reviewed_at"),
        "repositories": results,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("control-plane/manifests/ecosystem-dispositions.json"),
    )
    parser.add_argument("--public-only", action="store_true")
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
        )
    except EcosystemAuditError as exc:
        print(f"ecosystem live audit failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        counts = ", ".join(
            f"{repo}: {value['issue_count']} issues, {value['pull_request_count']} PRs"
            for repo, value in result["repositories"].items()
        )
        print(f"ecosystem live audit passed ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
