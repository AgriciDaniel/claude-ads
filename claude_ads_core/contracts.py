"""Versioned contract validation with no runtime dependencies.

The JSON Schema files are the portable contract.  This module provides strict
semantic validation for the v1 fields used by the deterministic engine so the
CLI remains useful in environments where a JSON Schema library is unavailable.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .workflow_contracts import (
    WORKFLOW_CONTRACT_NAMES,
    WorkflowContractError,
    validate_workflow_contract,
)

SCHEMA_VERSION = "1.0.0"
CORE_CONTRACT_NAMES = (
    "account-snapshot",
    "audit-worker-result",
    "run-manifest",
    "control-definition",
    "finding",
    "report-bundle",
)
COCKPIT_CONTRACT_NAMES = (
    "cockpit-index",
    "cockpit-snapshot",
    "cockpit-action-receipt",
)
CONTRACT_NAMES = CORE_CONTRACT_NAMES + WORKFLOW_CONTRACT_NAMES + COCKPIT_CONTRACT_NAMES
PLATFORMS = {
    "google",
    "meta",
    "youtube",
    "linkedin",
    "tiktok",
    "microsoft",
    "apple",
    "amazon",
    "reddit",
    "pinterest",
    "snapchat",
    "x",
}
FINDING_STATUSES = {"pass", "fail", "unknown", "not_applicable"}
SEVERITIES = {"critical", "high", "medium", "informational"}


class ContractError(ValueError):
    """Raised when a payload does not satisfy its versioned contract."""


def _require_object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _require_string(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _require_number(value: Any, path: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{path} must be a number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ContractError(f"{path} must be finite") from exc
    if not math.isfinite(result):
        raise ContractError(f"{path} must be finite")
    if minimum is not None and result < minimum:
        raise ContractError(f"{path} must be >= {minimum}")
    return result


def _require_list(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{path} must be an array")
    return value


def _require_keys(payload: Mapping[str, Any], keys: Sequence[str], path: str = "$") -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ContractError(f"{path} missing required field(s): {', '.join(missing)}")


def _require_exact_keys(payload: Mapping[str, Any], keys: Sequence[str], path: str = "$") -> None:
    _require_keys(payload, keys, path)
    unexpected = sorted(set(payload) - set(keys))
    if unexpected:
        raise ContractError(f"{path} has unsupported field(s): {', '.join(unexpected)}")


def _validate_version(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ContractError(f"$.schema_version must equal {SCHEMA_VERSION!r}")


def _validate_date(value: Any, path: str) -> date:
    text = _require_string(value, path)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ContractError(f"{path} must be an ISO 8601 date") from exc


def _validate_datetime(value: Any, path: str) -> None:
    text = _require_string(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{path} must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{path} must include a UTC offset")


def _validate_account_snapshot(payload: Mapping[str, Any]) -> None:
    _require_keys(
        payload,
        ("schema_version", "account", "window", "currency", "campaigns", "creatives", "conversions", "budgets"),
    )
    _validate_version(payload)
    account = _require_object(payload["account"], "$.account")
    _require_keys(account, ("platform", "account_id"), "$.account")
    platform = _require_string(account["platform"], "$.account.platform").lower()
    if platform not in PLATFORMS:
        raise ContractError(f"$.account.platform must be one of: {', '.join(sorted(PLATFORMS))}")
    _require_string(account["account_id"], "$.account.account_id")
    window = _require_object(payload["window"], "$.window")
    _require_keys(window, ("start", "end"), "$.window")
    start = _validate_date(window["start"], "$.window.start")
    end = _validate_date(window["end"], "$.window.end")
    if end < start:
        raise ContractError("$.window.end must be on or after $.window.start")
    currency = _require_string(payload["currency"], "$.currency")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ContractError("$.currency must be a three-letter uppercase currency code")
    if "spend" in payload and payload["spend"] is not None:
        _require_number(payload["spend"], "$.spend", minimum=0)
    for field in ("campaigns", "creatives", "conversions", "budgets"):
        items = _require_list(payload[field], f"$.{field}")
        for index, item in enumerate(items):
            _require_object(item, f"$.{field}[{index}]")


def _validate_run_manifest(payload: Mapping[str, Any]) -> None:
    _require_keys(
        payload,
        ("schema_version", "run_id", "started_at", "scopes", "adapters", "sources", "privacy_class", "data_lifecycle", "worker_status", "completeness"),
    )
    _validate_version(payload)
    _require_string(payload["run_id"], "$.run_id")
    _validate_datetime(payload["started_at"], "$.started_at")
    for field in ("scopes", "sources"):
        values = _require_list(payload[field], f"$.{field}")
        for index, value in enumerate(values):
            _require_string(value, f"$.{field}[{index}]")
    adapters = _require_list(payload["adapters"], "$.adapters")
    for index, adapter_value in enumerate(adapters):
        adapter = _require_object(adapter_value, f"$.adapters[{index}]")
        _require_keys(adapter, ("platform", "mode"), f"$.adapters[{index}]")
        if _require_string(adapter["platform"], f"$.adapters[{index}].platform").lower() not in PLATFORMS:
            raise ContractError(f"$.adapters[{index}].platform is unsupported")
        if adapter["mode"] not in {"export", "live_read", "write_preview", "write_apply"}:
            raise ContractError(f"$.adapters[{index}].mode is invalid")
    if payload["privacy_class"] not in {"public", "internal", "confidential", "restricted"}:
        raise ContractError("$.privacy_class is invalid")
    try:
        validate_workflow_contract("data-lifecycle", payload["data_lifecycle"])
    except WorkflowContractError as exc:
        raise ContractError(f"$.data_lifecycle: {exc}") from exc
    lifecycle = _require_object(payload["data_lifecycle"], "$.data_lifecycle")
    if lifecycle.get("classification") != payload["privacy_class"]:
        raise ContractError("$.privacy_class must match $.data_lifecycle.classification")
    statuses = _require_object(payload["worker_status"], "$.worker_status")
    for worker, status in statuses.items():
        _require_string(worker, "$.worker_status key")
        if status not in {"pending", "running", "completed", "failed", "skipped"}:
            raise ContractError(f"$.worker_status.{worker} is invalid")
    if payload["completeness"] not in {"complete", "partial", "failed"}:
        raise ContractError("$.completeness is invalid")


def _validate_control_definition(payload: Mapping[str, Any]) -> None:
    _require_keys(
        payload,
        (
            "schema_version",
            "control_id",
            "category",
            "severity",
            "required_inputs",
            "source_ids",
            "maturity",
            "geographies",
            "scoring_behavior",
            "stability",
        ),
    )
    _validate_version(payload)
    for field in ("control_id", "category"):
        _require_string(payload[field], f"$.{field}")
    if payload["severity"] not in SEVERITIES:
        raise ContractError(f"$.severity must be one of: {', '.join(sorted(SEVERITIES))}")
    for field in ("required_inputs", "source_ids", "geographies"):
        values = _require_list(payload[field], f"$.{field}")
        for index, value in enumerate(values):
            _require_string(value, f"$.{field}[{index}]")
    if payload["maturity"] not in {
        "inventory-baselined",
        "source-grounded",
        "domain-integrated",
        "eval-verified",
        "release-ready",
    }:
        raise ContractError("$.maturity is invalid")
    if payload["scoring_behavior"] not in {"health", "opportunity", "watchlist"}:
        raise ContractError("$.scoring_behavior is invalid")
    if payload["stability"] not in {"stable", "experimental"}:
        raise ContractError("$.stability is invalid")
    if "expires_at" in payload and payload["expires_at"] is not None:
        _validate_date(payload["expires_at"], "$.expires_at")


def _validate_finding(payload: Mapping[str, Any]) -> None:
    _require_keys(
        payload,
        ("schema_version", "control_id", "status", "evidence", "confidence", "observation", "diagnosis", "recommendation"),
    )
    _validate_version(payload)
    _require_string(payload["control_id"], "$.control_id")
    if payload["status"] not in FINDING_STATUSES:
        raise ContractError(f"$.status must be one of: {', '.join(sorted(FINDING_STATUSES))}")
    evidence = _require_list(payload["evidence"], "$.evidence")
    for index, item in enumerate(evidence):
        _require_object(item, f"$.evidence[{index}]")
    if payload["confidence"] not in {"high", "medium", "low", "none"}:
        raise ContractError("$.confidence is invalid")
    if "source_classification" in payload and payload["source_classification"] not in {
        "evidence_based",
        "practitioner",
        "contested",
        "folklore",
    }:
        raise ContractError("$.source_classification is invalid")
    for field in ("observation", "diagnosis", "recommendation"):
        _require_string(payload[field], f"$.{field}", nonempty=False)
    if payload["status"] in {"pass", "fail"} and not evidence:
        raise ContractError("$.evidence must not be empty for pass/fail findings")
    if "score_contribution" in payload and payload["score_contribution"] is not None:
        _require_number(payload["score_contribution"], "$.score_contribution")


def _validate_string_array(value: Any, path: str) -> None:
    items = _require_list(value, path)
    strings = [_require_string(item, f"{path}[{index}]") for index, item in enumerate(items)]
    if len(strings) != len(set(strings)):
        raise ContractError(f"{path} must contain unique values")


def _validate_audit_worker_result(payload: Mapping[str, Any]) -> None:
    fields = (
        "schema_version",
        "status",
        "platform",
        "scope",
        "findings",
        "contradictions",
        "missing_inputs",
        "stale_sources",
        "recovery_hints",
    )
    _require_exact_keys(payload, fields)
    _validate_version(payload)
    if payload["status"] not in {"ok", "needs_input", "blocked", "failed"}:
        raise ContractError("$.status is invalid")
    platform = _require_string(payload["platform"], "$.platform")
    if platform not in PLATFORMS:
        raise ContractError(f"$.platform must be one of: {', '.join(sorted(PLATFORMS))}")
    _validate_string_array(payload["scope"], "$.scope")
    allowed_finding_fields = {
        "schema_version",
        "control_id",
        "status",
        "evidence",
        "confidence",
        "source_classification",
        "observation",
        "diagnosis",
        "recommendation",
        "score_contribution",
    }
    findings = _require_list(payload["findings"], "$.findings")
    for index, raw_finding in enumerate(findings):
        finding = _require_object(raw_finding, f"$.findings[{index}]")
        unexpected = sorted(set(finding) - allowed_finding_fields)
        if unexpected:
            raise ContractError(
                f"$.findings[{index}] has unsupported field(s): {', '.join(unexpected)}"
            )
        _validate_finding(finding)
    for field in ("contradictions", "missing_inputs", "stale_sources", "recovery_hints"):
        _validate_string_array(payload[field], f"$.{field}")


def _validate_report_bundle(payload: Mapping[str, Any]) -> None:
    _require_keys(payload, ("schema_version", "run_manifest", "account_snapshot", "control_definitions", "findings", "scoring"))
    _validate_version(payload)
    validate_contract("run-manifest", payload["run_manifest"])
    validate_contract("account-snapshot", payload["account_snapshot"])
    controls = _require_list(payload["control_definitions"], "$.control_definitions")
    findings = _require_list(payload["findings"], "$.findings")
    for item in controls:
        validate_contract("control-definition", item)
    for item in findings:
        validate_contract("finding", item)
    scoring = _require_object(payload["scoring"], "$.scoring")
    _require_keys(scoring, ("health_score", "evidence_coverage", "status", "categories"), "$.scoring")
    if scoring["health_score"] is not None:
        value = _require_number(scoring["health_score"], "$.scoring.health_score", minimum=0)
        if value > 100:
            raise ContractError("$.scoring.health_score must be <= 100")
    coverage = _require_number(scoring["evidence_coverage"], "$.scoring.evidence_coverage", minimum=0)
    if coverage > 100:
        raise ContractError("$.scoring.evidence_coverage must be <= 100")
    if scoring["status"] not in {"normal", "provisional", "insufficient_evidence"}:
        raise ContractError("$.scoring.status is invalid")
    _require_list(scoring["categories"], "$.scoring.categories")


_VALIDATORS: dict[str, Callable[[Mapping[str, Any]], None]] = {
    "account-snapshot": _validate_account_snapshot,
    "audit-worker-result": _validate_audit_worker_result,
    "run-manifest": _validate_run_manifest,
    "control-definition": _validate_control_definition,
    "finding": _validate_finding,
    "report-bundle": _validate_report_bundle,
}


def validate_contract(name: str, payload: Any) -> None:
    """Validate *payload* against the supported semantic v1 contract."""

    if name in COCKPIT_CONTRACT_NAMES:
        # Keep the optional projection's validator out of core import cycles.
        from .cockpit_contracts import validate_cockpit_contract

        try:
            validate_cockpit_contract(name, payload)
        except ValueError as exc:
            raise ContractError(str(exc)) from exc
        return
    if name in WORKFLOW_CONTRACT_NAMES:
        try:
            validate_workflow_contract(name, payload)
        except WorkflowContractError as exc:
            raise ContractError(str(exc)) from exc
        return
    if name not in _VALIDATORS:
        raise ContractError(f"unknown contract {name!r}; expected one of: {', '.join(CONTRACT_NAMES)}")
    _VALIDATORS[name](_require_object(payload, "$"))


def load_contract(name: str, path: str | Path) -> dict[str, Any]:
    """Load JSON from *path*, validate it, and return the decoded object."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load {path}: {exc}") from exc
    validate_contract(name, payload)
    return payload


def schema_path(name: str) -> Path:
    """Return the installed JSON Schema path for a contract."""

    if name not in CONTRACT_NAMES:
        raise ContractError(f"unknown contract {name!r}")
    return Path(str(files("claude_ads_core").joinpath("schemas", "v1", f"{name}.schema.json")))
