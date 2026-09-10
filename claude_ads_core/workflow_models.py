"""Typed structures for Claude Ads workflow and orchestration artifacts."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


PrivacyClass = Literal["public", "internal", "confidential", "restricted"]
ArtifactStatus = Literal["draft", "complete", "partial", "failed"]


class DataLifecycle(TypedDict):
    schema_version: Literal["1.0.0"]
    lifecycle_id: str
    classification: PrivacyClass
    retention: dict[str, Any]
    encryption: dict[str, Any]
    access: dict[str, Any]
    deletion: dict[str, Any]
    incident: dict[str, Any]


class SetupProfile(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["setup-profile"]
    run_id: str
    created_at: str
    business: dict[str, Any]
    objective: dict[str, Any]
    platforms: list[str]
    account_refs: list[dict[str, str]]
    data_sources: list[dict[str, str]]
    privacy_class: PrivacyClass
    mutation_authority: Literal["none", "draft-only", "approved-plan-required"]
    approver_ids: list[str]
    assumptions: list[str]
    data_lifecycle: DataLifecycle


class BrandProfile(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["brand-profile"]
    run_id: str
    created_at: str
    brand_name: str
    website_url: str | None
    observations: list[dict[str, Any]]
    inferences: list[dict[str, Any]]
    source_ids: list[str]
    source_assets_authorized: bool
    missing_fields: list[str]
    status: ArtifactStatus
    data_lifecycle: DataLifecycle


class MediaPlan(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["media-plan"]
    run_id: str
    created_at: str
    objective: str
    currency: str
    channels: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    assumptions: list[str]
    exclusions: list[str]
    status: ArtifactStatus
    data_lifecycle: DataLifecycle


class CreativeBrief(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["creative-brief"]
    run_id: str
    created_at: str
    objective: str
    audience: str
    offer: str
    approved_claims: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    copy_deck: list[dict[str, Any]]
    specification_source_ids: list[str]
    human_review: Literal["pending", "approved", "rejected"]
    status: ArtifactStatus
    data_lifecycle: DataLifecycle


class GenerationManifest(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["generation-manifest"]
    run_id: str
    created_at: str
    provider: dict[str, Any]
    inputs: dict[str, Any]
    outputs: list[dict[str, Any]]
    failures: list[dict[str, str]]
    human_review: Literal["pending", "approved", "rejected"]
    status: ArtifactStatus
    data_lifecycle: DataLifecycle


class MonitoringBundle(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["monitoring-bundle"]
    run_id: str
    created_at: str
    window: dict[str, str]
    checkpoints: list[dict[str, Any]]
    missing_inputs: list[str]
    contradictions: list[str]
    completeness: Literal["complete", "partial", "failed"]
    data_lifecycle: DataLifecycle


class ExperimentArtifact(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["experiment-artifact"]
    run_id: str
    created_at: str
    experiment_id: str
    stage: Literal["setup", "readout"]
    design: dict[str, Any]
    result: dict[str, Any] | None
    decision: str | None
    status: ArtifactStatus
    data_lifecycle: DataLifecycle


class MutationPlan(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["mutation-plan"]
    run_id: str
    created_at: str
    plan_id: str
    platform: str
    account_id: str
    object_id: str
    operation: str
    before: dict[str, Any]
    after: dict[str, Any]
    reason: str
    blast_radius: str
    ceilings: list[dict[str, Any]]
    approval: dict[str, Any] | None
    idempotency_key: str
    audit_destination: str
    verification_steps: list[str]
    rollback: dict[str, Any]
    remote_precondition_sha256: str
    status: Literal["draft", "approved", "applied", "verified", "rolled-back"]
    data_lifecycle: DataLifecycle


class OrchestrationRun(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["orchestration-run"]
    run_id: str
    created_at: str
    objective: str
    scopes: list[str]
    phases: list[str]
    privacy_class: PrivacyClass
    mutation_authority: Literal["none", "repository-only", "draft-external", "approved-external"]
    status: Literal["open"]
    data_lifecycle: DataLifecycle


class OrchestrationTask(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["orchestration-task"]
    task_id: str
    run_id: str
    role: str
    objective: str
    scope: list[str]
    exclusions: list[str]
    evidence_policy: list[str]
    privacy_class: PrivacyClass
    mutation_authority: Literal["none", "repository-only", "draft-external", "approved-external"]
    inputs: list[dict[str, str]]
    output_contract: dict[str, Any]
    verification: list[str]
    recovery: list[str]
    depends_on: list[str]
    created_at: str
    status: Literal["queued"]


class OrchestrationResult(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["orchestration-result"]
    result_id: str
    task_id: str
    run_id: str
    role: str
    created_at: str
    status: Literal["ok", "needs_input", "blocked", "failed"]
    output_artifacts: list[dict[str, str]]
    evidence_refs: list[str]
    summary: str
    blockers: list[str]
    recovery_hints: list[str]
    supersedes: str | None


class OrchestrationGate(TypedDict):
    schema_version: Literal["1.0.0"]
    artifact_type: Literal["orchestration-gate"]
    gate_id: str
    run_id: str
    stage: str
    evaluated_at: str
    evaluator: Literal["artifact-only-v1"]
    required_task_ids: list[str]
    evaluated_result_ids: list[str]
    checks: list[dict[str, Any]]
    decision: Literal["pass", "fail"]
    blockers: list[str]
