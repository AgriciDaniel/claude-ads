"""Typed public interfaces for the v1 JSON contracts."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


class AccountIdentity(TypedDict):
    platform: str
    account_id: str
    name: NotRequired[str]


class DateWindow(TypedDict):
    start: str
    end: str


class AccountSnapshot(TypedDict):
    schema_version: Literal["1.0.0"]
    account: AccountIdentity
    window: DateWindow
    currency: str
    spend: NotRequired[float | None]
    campaigns: list[dict[str, Any]]
    creatives: list[dict[str, Any]]
    conversions: list[dict[str, Any]]
    budgets: list[dict[str, Any]]


class AdapterRecord(TypedDict):
    platform: str
    mode: Literal["export", "live_read", "write_preview", "write_apply"]


class RunManifest(TypedDict):
    schema_version: Literal["1.0.0"]
    run_id: str
    started_at: str
    scopes: list[str]
    adapters: list[AdapterRecord]
    sources: list[str]
    privacy_class: Literal["public", "internal", "confidential", "restricted"]
    data_lifecycle: dict[str, Any]
    worker_status: dict[str, Literal["pending", "running", "completed", "failed", "skipped"]]
    completeness: Literal["complete", "partial", "failed"]


class ControlDefinition(TypedDict):
    schema_version: Literal["1.0.0"]
    control_id: str
    category: str
    severity: Literal["critical", "high", "medium", "informational"]
    required_inputs: list[str]
    source_ids: list[str]
    maturity: Literal[
        "inventory-baselined",
        "source-grounded",
        "domain-integrated",
        "eval-verified",
        "release-ready",
    ]
    geographies: list[str]
    expires_at: NotRequired[str | None]
    scoring_behavior: Literal["health", "opportunity", "watchlist"]
    stability: Literal["stable", "experimental"]


class Finding(TypedDict):
    schema_version: Literal["1.0.0"]
    control_id: str
    status: Literal["pass", "fail", "unknown", "not_applicable"]
    evidence: list[dict[str, Any]]
    confidence: Literal["high", "medium", "low", "none"]
    source_classification: NotRequired[Literal["evidence_based", "practitioner", "contested", "folklore"]]
    observation: str
    diagnosis: str
    recommendation: str
    score_contribution: NotRequired[float | None]


class AuditWorkerResult(TypedDict):
    schema_version: Literal["1.0.0"]
    status: Literal["ok", "needs_input", "blocked", "failed"]
    platform: str
    scope: list[str]
    findings: list[Finding]
    contradictions: list[str]
    missing_inputs: list[str]
    stale_sources: list[str]
    recovery_hints: list[str]


class ScoringOutput(TypedDict):
    health_score: float | None
    evidence_coverage: float
    status: Literal["normal", "provisional", "insufficient_evidence"]
    categories: list[dict[str, Any]]


class ReportBundle(TypedDict):
    schema_version: Literal["1.0.0"]
    run_manifest: RunManifest
    account_snapshot: AccountSnapshot
    control_definitions: list[ControlDefinition]
    findings: list[Finding]
    scoring: ScoringOutput
