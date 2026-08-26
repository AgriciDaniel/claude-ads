from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit_ecosystem_live.py"
SPEC = importlib.util.spec_from_file_location("claude_ads_ecosystem_live", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def _ledger() -> dict:
    path = SCRIPT.parents[1] / "control-plane/manifests/ecosystem-dispositions.json"
    return json.loads(path.read_text(encoding="utf-8"))


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
        }
    return result


def test_live_reconciliation_allows_only_exact_current_candidate() -> None:
    ledger = _ledger()
    live = _live(ledger)
    candidate_head = "a" * 40
    live[module.CANONICAL_REPOSITORY][("pull-request", 14)] = {
        "kind": "pull-request",
        "number": 14,
        "title": "current candidate",
        "state": "open",
        "url": "https://github.com/AI-Marketing-Hub/claude-ads/pull/14",
        "head_sha": candidate_head,
    }

    result = module.reconcile_live(
        ledger,
        live,
        repositories=(module.PUBLIC_REPOSITORY, module.CANONICAL_REPOSITORY),
        candidate_repository=module.CANONICAL_REPOSITORY,
        candidate_pr=14,
        candidate_head=candidate_head,
    )

    assert result["status"] == "pass"
    assert result["candidate_exclusion"]["pull_request"] == 14


def test_live_reconciliation_rejects_unreviewed_or_drifted_items() -> None:
    ledger = _ledger()
    live = _live(ledger)
    live[module.PUBLIC_REPOSITORY][("issue", 999)] = {
        "kind": "issue",
        "number": 999,
        "title": "unreviewed data",
        "state": "open",
        "url": "https://github.com/AgriciDaniel/claude-ads/issues/999",
        "head_sha": None,
    }
    with pytest.raises(module.EcosystemAuditError, match="coverage mismatch"):
        module.reconcile_live(
            ledger,
            live,
            repositories=(module.PUBLIC_REPOSITORY, module.CANONICAL_REPOSITORY),
        )

    live = _live(ledger)
    live[module.PUBLIC_REPOSITORY][("pull-request", 62)]["head_sha"] = "b" * 40
    with pytest.raises(module.EcosystemAuditError, match="head drift"):
        module.reconcile_live(
            ledger,
            live,
            repositories=(module.PUBLIC_REPOSITORY, module.CANONICAL_REPOSITORY),
        )


def test_candidate_exclusion_rejects_wrong_head_or_recorded_input() -> None:
    ledger = _ledger()
    live = _live(ledger)
    live[module.CANONICAL_REPOSITORY][("pull-request", 14)] = {
        "kind": "pull-request",
        "number": 14,
        "title": "current candidate",
        "state": "open",
        "url": "https://github.com/AI-Marketing-Hub/claude-ads/pull/14",
        "head_sha": "c" * 40,
    }
    with pytest.raises(module.EcosystemAuditError, match="does not match"):
        module.reconcile_live(
            ledger,
            live,
            repositories=(module.PUBLIC_REPOSITORY, module.CANONICAL_REPOSITORY),
            candidate_repository=module.CANONICAL_REPOSITORY,
            candidate_pr=14,
            candidate_head="d" * 40,
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
