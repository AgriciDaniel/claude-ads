from __future__ import annotations

import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path
import sys
from urllib.parse import quote

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit_ecosystem_live.py"
SPEC = importlib.util.spec_from_file_location("claude_ads_ecosystem_live", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)

BOTH = (module.PUBLIC_REPOSITORY, module.CANONICAL_REPOSITORY)


def _ledger() -> dict:
    path = SCRIPT.parents[1] / "control-plane/manifests/ecosystem-dispositions.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _observed_at() -> date:
    ledger = _ledger()
    observed = {
        ledger["public_snapshot"]["observed_at"],
        ledger["canonical_snapshot"]["observed_at"],
    }
    assert len(observed) == 1, "tests assume both snapshots share one observed_at"
    return date.fromisoformat(observed.pop())


# Timestamps relative to the frozen snapshot date; derived so that the tests
# keep working when the ledger is re-observed.
BEFORE_SNAPSHOT = f"{_observed_at() - timedelta(days=5)}T10:00:00Z"
ON_SNAPSHOT = f"{_observed_at()}T23:59:59Z"
AFTER_SNAPSHOT = f"{_observed_at() + timedelta(days=1)}T00:00:01Z"
OPEN_PUBLIC_PR = max(
    entry["number"]
    for entry in _ledger()["entries"]
    if entry["repository"] == module.PUBLIC_REPOSITORY
    and entry["kind"] == "pull-request"
    and entry["state"] == "open"
)


def _live(ledger: dict) -> dict:
    result = {
        module.PUBLIC_REPOSITORY: {},
        module.CANONICAL_REPOSITORY: {},
    }
    snapshots = {
        module.PUBLIC_REPOSITORY: ledger["public_snapshot"],
        module.CANONICAL_REPOSITORY: ledger["canonical_snapshot"],
    }
    for entry in ledger["entries"]:
        repository = entry["repository"]
        head = None
        if entry["kind"] == "pull-request":
            head = snapshots[repository]["pull_request_heads"][str(entry["number"])]
        result[repository][(entry["kind"], entry["number"])] = {
            "kind": entry["kind"],
            "number": entry["number"],
            "title": entry["title"],
            "state": entry["state"],
            "url": entry["url"],
            "head_sha": head,
            "created_at": BEFORE_SNAPSHOT,
            "merged_at": BEFORE_SNAPSHOT if entry["state"] == "merged" else None,
        }
    return result


def _issue(number: int, created_at: str) -> dict:
    return {
        "kind": "issue",
        "number": number,
        "title": "unreviewed data",
        "state": "open",
        "url": f"https://github.com/AgriciDaniel/claude-ads/issues/{number}",
        "head_sha": None,
        "created_at": created_at,
        "merged_at": None,
    }


def _pull(number: int, head: str, *, created_at: str, merged_at: str | None = None) -> dict:
    return {
        "kind": "pull-request",
        "number": number,
        "title": "current candidate",
        "state": "merged" if merged_at else "open",
        "url": f"https://github.com/AI-Marketing-Hub/claude-ads/pull/{number}",
        "head_sha": head,
        "created_at": created_at,
        "merged_at": merged_at,
    }


def _finding_kinds(result: dict) -> list[str]:
    return sorted(finding["kind"] for finding in result["findings"])


def test_live_reconciliation_allows_only_exact_current_candidate() -> None:
    ledger = _ledger()
    live = _live(ledger)
    candidate_head = "a" * 40
    live[module.CANONICAL_REPOSITORY][("pull-request", 14)] = _pull(
        14, candidate_head, created_at=AFTER_SNAPSHOT
    )

    for strict in (False, True):
        result = module.reconcile_live(
            ledger,
            live,
            repositories=BOTH,
            candidate_repository=module.CANONICAL_REPOSITORY,
            candidate_pr=14,
            candidate_head=candidate_head,
            strict=strict,
        )
        assert result["status"] == "pass"
        assert result["mode"] == ("strict" if strict else "default")
        assert result["findings"] == []
        assert result["candidate_exclusion"]["pull_request"] == 14


def test_exact_reconciliation_has_no_findings_in_either_mode() -> None:
    ledger = _ledger()
    for strict in (False, True):
        result = module.reconcile_live(ledger, _live(ledger), repositories=BOTH, strict=strict)
        assert result["findings"] == []
        assert all(
            value["status"] == "reconciled" for value in result["repositories"].values()
        )


def test_post_snapshot_item_is_a_finding_by_default_and_fails_strict() -> None:
    ledger = _ledger()
    live = _live(ledger)
    live[module.PUBLIC_REPOSITORY][("issue", 999)] = _issue(999, AFTER_SNAPSHOT)

    result = module.reconcile_live(ledger, live, repositories=BOTH)
    assert result["status"] == "pass"
    assert _finding_kinds(result) == ["unreviewed"]
    assert result["repositories"][module.PUBLIC_REPOSITORY]["unreviewed"] == ["issue/999"]
    assert result["repositories"][module.PUBLIC_REPOSITORY]["status"] == (
        "reconciled-with-findings"
    )

    with pytest.raises(module.EcosystemAuditError, match="coverage mismatch"):
        module.reconcile_live(ledger, live, repositories=BOTH, strict=True)


def test_pre_snapshot_unrecorded_item_fails_in_both_modes() -> None:
    ledger = _ledger()
    for created_at in (BEFORE_SNAPSHOT, ON_SNAPSHOT):
        live = _live(ledger)
        live[module.PUBLIC_REPOSITORY][("issue", 999)] = _issue(999, created_at)
        for strict in (False, True):
            with pytest.raises(module.EcosystemAuditError, match="predates the snapshot"):
                module.reconcile_live(ledger, live, repositories=BOTH, strict=strict)


def test_head_drift_is_a_finding_by_default_and_fails_strict() -> None:
    ledger = _ledger()
    live = _live(ledger)
    live[module.PUBLIC_REPOSITORY][("pull-request", OPEN_PUBLIC_PR)]["head_sha"] = "b" * 40

    result = module.reconcile_live(ledger, live, repositories=BOTH)
    assert result["status"] == "pass"
    assert _finding_kinds(result) == ["head_drift"]
    finding = result["findings"][0]
    assert finding["number"] == OPEN_PUBLIC_PR and finding["live_head"] == "b" * 40

    with pytest.raises(module.EcosystemAuditError, match="head drift"):
        module.reconcile_live(ledger, live, repositories=BOTH, strict=True)


def test_metadata_drift_is_a_finding_by_default_and_fails_strict() -> None:
    ledger = _ledger()
    live = _live(ledger)
    live[module.PUBLIC_REPOSITORY][("issue", 1)]["title"] = "renamed by a third party"

    result = module.reconcile_live(ledger, live, repositories=BOTH)
    assert _finding_kinds(result) == ["metadata_drift"]
    assert result["findings"][0]["field"] == "title"

    with pytest.raises(module.EcosystemAuditError, match="metadata drift"):
        module.reconcile_live(ledger, live, repositories=BOTH, strict=True)


def test_extra_recorded_item_fails_in_both_modes() -> None:
    ledger = _ledger()
    live = _live(ledger)
    del live[module.PUBLIC_REPOSITORY][("pull-request", OPEN_PUBLIC_PR)]
    expected = rf"extra=\[\('pull-request', {OPEN_PUBLIC_PR}\)\]"
    for strict in (False, True):
        with pytest.raises(module.EcosystemAuditError, match=expected):
            module.reconcile_live(ledger, live, repositories=BOTH, strict=strict)


def test_merged_after_snapshot_pull_is_set_aside_in_default_mode_only() -> None:
    ledger = _ledger()
    live = _live(ledger)
    live[module.CANONICAL_REPOSITORY][("pull-request", 14)] = _pull(
        14, "a" * 40, created_at=AFTER_SNAPSHOT, merged_at=AFTER_SNAPSHOT
    )

    result = module.reconcile_live(ledger, live, repositories=BOTH)
    assert result["status"] == "pass"
    assert _finding_kinds(result) == ["merged_after_snapshot"]
    assert result["findings"][0]["recorded"] is False
    assert result["repositories"][module.CANONICAL_REPOSITORY]["merged_after_snapshot"] == [14]
    assert result["repositories"][module.CANONICAL_REPOSITORY]["pull_request_count"] == 13

    with pytest.raises(module.EcosystemAuditError, match="coverage mismatch"):
        module.reconcile_live(ledger, live, repositories=BOTH, strict=True)


def test_unrecorded_pre_snapshot_pull_merged_later_still_fails_default_mode() -> None:
    ledger = _ledger()
    live = _live(ledger)
    live[module.PUBLIC_REPOSITORY][("pull-request", 999)] = _pull(
        999, "b" * 40, created_at=BEFORE_SNAPSHOT, merged_at=AFTER_SNAPSHOT
    )

    for strict in (False, True):
        with pytest.raises(
            module.EcosystemAuditError, match="predates the snapshot|coverage mismatch"
        ):
            module.reconcile_live(ledger, live, repositories=BOTH, strict=strict)


def test_recorded_pull_merged_after_snapshot_is_set_aside_not_extra() -> None:
    ledger = _ledger()
    live = _live(ledger)
    item = live[module.PUBLIC_REPOSITORY][("pull-request", OPEN_PUBLIC_PR)]
    item.update({"state": "merged", "merged_at": AFTER_SNAPSHOT, "head_sha": "f" * 40})

    result = module.reconcile_live(ledger, live, repositories=BOTH)
    assert _finding_kinds(result) == ["merged_after_snapshot"]
    assert result["findings"][0]["recorded"] is True

    with pytest.raises(module.EcosystemAuditError, match="head drift|metadata drift"):
        module.reconcile_live(ledger, live, repositories=BOTH, strict=True)


def test_candidate_exclusion_rejects_wrong_head_or_recorded_input() -> None:
    ledger = _ledger()
    live = _live(ledger)
    live[module.CANONICAL_REPOSITORY][("pull-request", 14)] = _pull(
        14, "c" * 40, created_at=AFTER_SNAPSHOT
    )
    with pytest.raises(module.EcosystemAuditError, match="does not match"):
        module.reconcile_live(
            ledger,
            live,
            repositories=BOTH,
            candidate_repository=module.CANONICAL_REPOSITORY,
            candidate_pr=14,
            candidate_head="d" * 40,
        )

    live = _live(ledger)
    recorded_head = ledger["public_snapshot"]["pull_request_heads"][str(OPEN_PUBLIC_PR)]
    assert live[module.PUBLIC_REPOSITORY][("pull-request", OPEN_PUBLIC_PR)]["state"] == "open"
    for strict in (False, True):
        with pytest.raises(module.EcosystemAuditError, match="must not also be recorded"):
            module.reconcile_live(
                ledger,
                live,
                repositories=BOTH,
                candidate_repository=module.PUBLIC_REPOSITORY,
                candidate_pr=OPEN_PUBLIC_PR,
                candidate_head=recorded_head,
                strict=strict,
            )


def test_event_candidate_is_bound_to_repository_number_and_head(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": module.CANONICAL_REPOSITORY},
                "pull_request": {
                    "number": 14,
                    "head": {"sha": "e" * 40},
                },
            }
        ),
        encoding="utf-8",
    )

    assert module._candidate_from_event(str(event_path)) == (
        module.CANONICAL_REPOSITORY,
        14,
        "e" * 40,
    )


def _fake_fetch(live: dict):
    """Serve the issues list and pull detail endpoints from a live fixture."""
    encoded = {
        "/".join(quote(part, safe="") for part in repository.split("/")): repository
        for repository in live
    }

    def fetch(endpoint: str):
        path, _, query = endpoint.partition("?")
        parts = path.split("/")
        repository = encoded["/".join(parts[1:3])]
        items = live[repository]
        if parts[3] == "issues":
            assert "page=1" in query
            listing = []
            for (kind, number), item in sorted(items.items(), key=lambda kv: kv[0][1]):
                raw = {
                    "number": number,
                    "title": item["title"],
                    "state": "closed" if item["state"] == "merged" else item["state"],
                    "html_url": item["url"],
                    "created_at": item["created_at"],
                }
                if kind == "pull-request":
                    raw["pull_request"] = {"merged_at": item["merged_at"]}
                listing.append(raw)
            return listing
        assert parts[3] == "pulls"
        item = items[("pull-request", int(parts[4]))]
        return {
            "title": item["title"],
            "state": "closed" if item["state"] == "merged" else item["state"],
            "html_url": item["url"],
            "head": {"sha": item["head_sha"]},
            "created_at": item["created_at"],
            "merged_at": item["merged_at"],
        }

    return fetch


def test_collect_live_repository_reads_created_and_merged_times() -> None:
    ledger = _ledger()
    live = _live(ledger)
    collected = module.collect_live_repository(
        module.PUBLIC_REPOSITORY, _fake_fetch(live)
    )
    assert collected == live[module.PUBLIC_REPOSITORY]


def test_main_drops_candidate_from_out_of_scope_event_repository(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    ledger = _ledger()
    live = _live(ledger)
    live[module.PUBLIC_REPOSITORY][("issue", 999)] = _issue(999, AFTER_SNAPSHOT)
    monkeypatch.setattr(module, "_github_fetcher", lambda token: _fake_fetch(live))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "someone-else/fork"},
                "pull_request": {"number": 7, "head": {"sha": "e" * 40}},
            }
        ),
        encoding="utf-8",
    )

    code = module.main(
        ["--ledger", str(ledger_path), "--event-path", str(event_path), "--json"]
    )
    captured = capsys.readouterr()
    assert code == 0
    result = json.loads(captured.out)
    assert result["candidate_exclusion"] is None
    assert result["mode"] == "default"
    assert _finding_kinds(result) == ["unreviewed"]
    assert captured.err.startswith("::warning::ecosystem live audit: ")

    code = module.main(
        ["--ledger", str(ledger_path), "--event-path", str(event_path), "--strict"]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "coverage mismatch" in captured.err


def test_fetcher_reports_status_code_and_path_only(monkeypatch) -> None:
    from urllib.error import HTTPError

    def failing_urlopen(request, timeout):
        raise HTTPError(request.full_url, 403, "rate limited", {}, None)

    monkeypatch.setattr(module, "urlopen", failing_urlopen)
    fetch = module._github_fetcher("ghp_" + "x" * 36)
    with pytest.raises(module.EcosystemAuditError) as excinfo:
        fetch("repos/AgriciDaniel/claude-ads/issues?state=all&per_page=100&page=1")
    message = str(excinfo.value)
    assert message == (
        "GitHub tracker query failed for repos/AgriciDaniel/claude-ads/issues: HTTP 403"
    )
    assert "ghp_" not in message and "state=all" not in message
