"""Deterministic repository status and next-blocker selection.

This module has no network or account access. It reports only what versioned
repository artifacts establish and uses an explicit, stable blocker order.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from .contracts import PLATFORMS
from .control_registry import RegistryError, load_control_registry

STATUS_SCHEMA_VERSION = "1.0.0"
MATURITY_IDS = (
    "inventory-baselined",
    "source-grounded",
    "domain-integrated",
    "eval-verified",
    "release-ready",
)
CAPABILITY_STATUSES = {"declared", "implemented", "fixture-verified", "live-verified", "disabled"}
LEGACY_RELEASE_CHECK_IDS = (
    "repository-audit",
    "clean-subject",
    "source-capability-integrity",
    "ecosystem-dispositions",
    "canonical-model-evaluation",
    "independent-reviews",
    "remote-ci",
)
RELEASE_CHECK_IDS = (
    "repository-audit",
    "clean-subject",
    "source-capability-integrity",
    "vulnerability-exception-integrity",
    "ecosystem-ledger-integrity",
    "canonical-model-evaluation",
    "independent-reviews",
    "remote-ci",
)
RELEASE_CHECK_IDS_BY_VERSION = {
    "1.0.0": LEGACY_RELEASE_CHECK_IDS,
    "2.0.0": RELEASE_CHECK_IDS,
}
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ProductStatusError(ValueError):
    """Raised when required repository status evidence is missing or malformed."""


def _read_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductStatusError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ProductStatusError(f"{label} must be a JSON object")
    return value


def _date(value: Any, path: str) -> date:
    if not isinstance(value, str):
        raise ProductStatusError(f"{path} must be an ISO 8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ProductStatusError(f"{path} must be an ISO 8601 date") from exc


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductStatusError(f"{path} must be a non-empty string")
    return value


def _strings(value: Any, path: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ProductStatusError(f"{path} must be an array")
    result = [_nonempty(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise ProductStatusError(f"{path} must contain unique values")
    return result


def _validate_maturity(document: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]], list[str]]:
    required = {"schema_version", "evaluated_at", "current", "levels", "automatic_demotion", "blockers"}
    allowed = required
    if set(document) != allowed or document.get("schema_version") != "1.0.0":
        raise ProductStatusError("maturity status has unsupported or missing fields")
    _date(document.get("evaluated_at"), "maturity.evaluated_at")
    current = _nonempty(document.get("current"), "maturity.current")
    if current not in MATURITY_IDS:
        raise ProductStatusError("maturity.current is unsupported")
    raw_levels = document.get("levels")
    if not isinstance(raw_levels, list) or len(raw_levels) != len(MATURITY_IDS):
        raise ProductStatusError("maturity.levels must contain exactly five levels")
    levels: list[dict[str, Any]] = []
    seen_unsatisfied = False
    for index, raw in enumerate(raw_levels):
        if not isinstance(raw, Mapping):
            raise ProductStatusError(f"maturity.levels[{index}] must be an object")
        if set(raw) - {"id", "ordinal", "requirements", "satisfied", "evidence"}:
            raise ProductStatusError(f"maturity.levels[{index}] has unsupported fields")
        level_id = raw.get("id")
        if level_id != MATURITY_IDS[index] or raw.get("ordinal") != index + 1:
            raise ProductStatusError("maturity levels must use canonical ID and ordinal order")
        requirements = _strings(raw.get("requirements"), f"maturity.levels[{index}].requirements", allow_empty=False)
        evidence = _strings(raw.get("evidence", []), f"maturity.levels[{index}].evidence")
        satisfied = raw.get("satisfied")
        if not isinstance(satisfied, bool):
            raise ProductStatusError(f"maturity.levels[{index}].satisfied must be boolean")
        if seen_unsatisfied and satisfied:
            raise ProductStatusError("maturity satisfaction must be a contiguous prefix")
        seen_unsatisfied = seen_unsatisfied or not satisfied
        levels.append(
            {
                "id": level_id,
                "ordinal": index + 1,
                "satisfied": satisfied,
                "requirements": requirements,
                "evidence": evidence,
            }
        )
    satisfied_ids = [level["id"] for level in levels if level["satisfied"]]
    if not satisfied_ids or satisfied_ids[-1] != current:
        raise ProductStatusError("maturity.current must equal the highest satisfied level")
    _strings(document.get("automatic_demotion"), "maturity.automatic_demotion", allow_empty=False)
    blockers = _strings(document.get("blockers"), "maturity.blockers")
    return current, levels, blockers


def _validate_evidence_ledgers(
    claim_document: Mapping[str, Any],
    source_document: Mapping[str, Any],
    as_of: date,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    for label, document, collection in (
        ("claim ledger", claim_document, "claims"),
        ("source ledger", source_document, "sources"),
    ):
        if document.get("schema_version") != "1.0.0":
            raise ProductStatusError(f"{label} schema_version is unsupported")
        _date(document.get("generated_at"), f"{label}.generated_at")
        if not isinstance(document.get(collection), list):
            raise ProductStatusError(f"{label}.{collection} must be an array")
    raw_sources = source_document["sources"]
    sources: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(raw_sources):
        if not isinstance(raw, Mapping):
            raise ProductStatusError(f"source ledger.sources[{index}] must be an object")
        source_id = _nonempty(raw.get("id"), f"source ledger.sources[{index}].id")
        if source_id in sources:
            raise ProductStatusError(f"duplicate source ID: {source_id}")
        _date(raw.get("refresh_due"), f"source {source_id}.refresh_due")
        _strings(raw.get("claim_ids"), f"source {source_id}.claim_ids")
        sources[source_id] = raw
    stale: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    claims: dict[str, set[str]] = {}
    for index, raw in enumerate(claim_document["claims"]):
        if not isinstance(raw, Mapping):
            raise ProductStatusError(f"claim ledger.claims[{index}] must be an object")
        claim_id = _nonempty(raw.get("id"), f"claim ledger.claims[{index}].id")
        if claim_id in claims:
            raise ProductStatusError(f"duplicate claim ID: {claim_id}")
        source_ids = _strings(raw.get("source_ids"), f"claim {claim_id}.source_ids", allow_empty=False)
        claims[claim_id] = set(source_ids)
        refresh_due = _date(raw.get("refresh_due"), f"claim {claim_id}.refresh_due")
        _date(raw.get("last_verified"), f"claim {claim_id}.last_verified")
        for source_id in source_ids:
            source = sources.get(source_id)
            if source is None or claim_id not in source.get("claim_ids", []):
                raise ProductStatusError(f"claim/source reciprocity failed: {claim_id} -> {source_id}")
        load_bearing = raw.get("load_bearing")
        if not isinstance(load_bearing, bool):
            raise ProductStatusError(f"claim {claim_id}.load_bearing must be boolean")
        if load_bearing and raw.get("verdict") != "verified":
            unverified.append(
                {
                    "claim_id": claim_id,
                    "verdict": _nonempty(raw.get("verdict"), f"claim {claim_id}.verdict"),
                    "source_ids": sorted(source_ids),
                }
            )
        if load_bearing and refresh_due < as_of:
            stale.append(
                {
                    "claim_id": claim_id,
                    "refresh_due": refresh_due.isoformat(),
                    "source_ids": sorted(source_ids),
                }
            )
    for source_id, source in sources.items():
        for claim_id in source.get("claim_ids", []):
            if claim_id not in claims or source_id not in claims[claim_id]:
                raise ProductStatusError(f"source references unknown claim: {source_id} -> {claim_id}")
    return sorted(stale, key=lambda item: (item["refresh_due"], item["claim_id"])), sorted(
        unverified, key=lambda item: item["claim_id"]
    )


def _disabled_capabilities(document: Mapping[str, Any]) -> list[dict[str, str]]:
    if set(document) != {"schema_version", "snapshot_at", "default_mutation_mode", "platforms"}:
        raise ProductStatusError("capability manifest has unsupported or missing fields")
    if document.get("schema_version") != "1.0.0" or document.get("default_mutation_mode") != "read-only":
        raise ProductStatusError("capability manifest header is invalid")
    raw_platforms = document.get("platforms")
    if not isinstance(raw_platforms, list):
        raise ProductStatusError("capability manifest platforms must be an array")
    platform_ids: set[str] = set()
    disabled: list[dict[str, str]] = []
    for index, raw_platform in enumerate(raw_platforms):
        if not isinstance(raw_platform, Mapping):
            raise ProductStatusError(f"capability platforms[{index}] must be an object")
        if set(raw_platform) != {"id", "display_name", "target_tier", "skill_path", "capabilities"}:
            raise ProductStatusError(f"capability platforms[{index}] has unsupported or missing fields")
        platform = _nonempty(raw_platform.get("id"), f"capability platforms[{index}].id")
        if platform not in PLATFORMS or platform in platform_ids:
            raise ProductStatusError(f"invalid or duplicate capability platform: {platform}")
        platform_ids.add(platform)
        capabilities = raw_platform.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            raise ProductStatusError(f"capability platform {platform} has no capabilities")
        capability_ids: set[str] = set()
        for cap_index, raw_capability in enumerate(capabilities):
            if not isinstance(raw_capability, Mapping):
                raise ProductStatusError(f"{platform}.capabilities[{cap_index}] must be an object")
            required = {"id", "mode", "status", "implementation_paths", "fixture_paths", "test_paths", "source_ids"}
            allowed = required | {"disabled_reason"}
            if not required <= set(raw_capability) or set(raw_capability) - allowed:
                raise ProductStatusError(f"{platform}.capabilities[{cap_index}] has unsupported or missing fields")
            capability_id = _nonempty(raw_capability.get("id"), f"{platform}.capabilities[{cap_index}].id")
            status = _nonempty(raw_capability.get("status"), f"{platform}.{capability_id}.status")
            if capability_id in capability_ids or status not in CAPABILITY_STATUSES:
                raise ProductStatusError(f"invalid or duplicate capability: {platform}/{capability_id}")
            capability_ids.add(capability_id)
            if status == "disabled":
                disabled.append(
                    {
                        "platform": platform,
                        "capability_id": capability_id,
                        "reason": _nonempty(
                            raw_capability.get("disabled_reason"),
                            f"{platform}.{capability_id}.disabled_reason",
                        ),
                    }
                )
    if platform_ids != PLATFORMS:
        raise ProductStatusError("capability manifest must cover exactly the twelve platforms")
    return sorted(disabled, key=lambda item: (item["platform"], item["capability_id"]))


def _repository_subject(root: Path) -> dict[str, str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD", "HEAD^{tree}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ProductStatusError("cannot resolve repository release-gate subject") from exc
    values = completed.stdout.splitlines() if completed.returncode == 0 else []
    if len(values) != 2 or not all(SHA_PATTERN.fullmatch(value) for value in values):
        raise ProductStatusError("cannot resolve repository release-gate subject")
    return {"commit_sha": values[0], "tree_sha": values[1]}


def _release_gate(path: Path | None, root: Path) -> dict[str, Any] | None:
    if path is None:
        return None
    document = _read_json(path, "release gate report")
    expected_fields = {
        "schema_version",
        "evidence_class",
        "evaluated_at",
        "subject",
        "checks",
        "release_gate_satisfied",
    }
    version = document.get("schema_version")
    if set(document) != expected_fields or version not in RELEASE_CHECK_IDS_BY_VERSION:
        raise ProductStatusError("release gate report fields or schema_version are invalid")
    check_ids = RELEASE_CHECK_IDS_BY_VERSION[str(version)]
    if document.get("evidence_class") != "release-gate-assessment":
        raise ProductStatusError("release gate evidence_class is invalid")
    try:
        evaluated = datetime.fromisoformat(str(document.get("evaluated_at")).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProductStatusError("release gate evaluated_at is invalid") from exc
    if evaluated.tzinfo is None:
        raise ProductStatusError("release gate evaluated_at must include an offset")
    subject = document.get("subject")
    if not isinstance(subject, Mapping) or set(subject) != {"commit_sha", "tree_sha"}:
        raise ProductStatusError("release gate subject is invalid")
    if not all(SHA_PATTERN.fullmatch(str(subject.get(key, ""))) for key in ("commit_sha", "tree_sha")):
        raise ProductStatusError("release gate subject hashes are invalid")
    expected_subject = _repository_subject(root)
    if dict(subject) != expected_subject:
        raise ProductStatusError("release gate subject does not match the reported repository")
    raw_checks = document.get("checks")
    if not isinstance(raw_checks, list) or len(raw_checks) != len(check_ids):
        raise ProductStatusError(
            f"release gate {version} must contain exactly {len(check_ids)} checks"
        )
    checks: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(raw_checks):
        if not isinstance(raw, Mapping):
            raise ProductStatusError(f"release gate checks[{index}] must be an object")
        check_id = _nonempty(raw.get("id"), f"release gate checks[{index}].id")
        status = raw.get("status")
        if check_id not in check_ids or check_id in checks or status not in {"pass", "fail"}:
            raise ProductStatusError(f"release gate check is invalid or duplicate: {check_id}")
        expected_check_fields = {"id", "status", "evidence"} if status == "pass" else {"id", "status", "error"}
        if set(raw) != expected_check_fields:
            raise ProductStatusError(f"release gate check fields are invalid: {check_id}")
        if status == "pass":
            if not isinstance(raw.get("evidence"), Mapping) or "error" in raw:
                raise ProductStatusError(f"passing release check lacks evidence: {check_id}")
        elif not isinstance(raw.get("error"), str) or not raw["error"].strip() or "evidence" in raw:
            raise ProductStatusError(f"failing release check lacks error: {check_id}")
        checks[check_id] = raw
    if set(checks) != set(check_ids):
        raise ProductStatusError("release gate check coverage is incomplete")
    satisfied = document.get("release_gate_satisfied")
    if not isinstance(satisfied, bool) or satisfied != all(
        checks[item]["status"] == "pass" for item in check_ids
    ):
        raise ProductStatusError("release_gate_satisfied disagrees with checks")
    failed = [
        {"id": check_id, "error": str(checks[check_id]["error"])}
        for check_id in check_ids
        if checks[check_id]["status"] == "fail"
    ]
    try:
        evidence_path = str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        evidence_path = "external-release-gate-report"
    return {
        "_schema_version": version,
        "evaluated_at": evaluated.isoformat(),
        "subject": dict(subject),
        "release_gate_satisfied": satisfied and version == "2.0.0",
        "failed_checks": failed,
        "evidence_path": evidence_path,
    }


def _next_blocker(
    *,
    stale: list[dict[str, Any]],
    unverified: list[dict[str, Any]],
    blockers: list[str],
    release_gate: dict[str, Any] | None,
    disabled_profiles: list[dict[str, str]],
    disabled_capabilities: list[dict[str, str]],
    levels: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply artifact-order-v1 and return exactly one decision object."""

    if unverified:
        selected = unverified[0]
        return {
            "kind": "unverified-load-bearing-claim",
            "id": selected["claim_id"],
            "summary": f"Restore or demote load-bearing claim {selected['claim_id']} before relying on it.",
            "rationale": "Unverified load-bearing evidence invalidates downstream maturity before feature work.",
            "evidence_paths": [
                "control-plane/manifests/claim-ledger.json",
                "control-plane/manifests/source-ledger.json",
            ],
        }
    if stale:
        selected = stale[0]
        return {
            "kind": "stale-load-bearing-claim",
            "id": selected["claim_id"],
            "summary": f"Refresh or demote {selected['claim_id']}; it expired on {selected['refresh_due']}.",
            "rationale": "The maturity manifest explicitly makes stale load-bearing evidence an automatic demotion.",
            "evidence_paths": [
                "control-plane/manifests/maturity-status.json",
                "control-plane/manifests/claim-ledger.json",
                "control-plane/manifests/source-ledger.json",
            ],
        }
    if blockers:
        return {
            "kind": "maturity-blocker",
            "id": "maturity-blocker-001",
            "summary": blockers[0],
            "rationale": "This is the first explicit blocker in the authoritative maturity manifest.",
            "evidence_paths": ["control-plane/manifests/maturity-status.json"],
        }
    if release_gate and release_gate["failed_checks"]:
        selected = release_gate["failed_checks"][0]
        return {
            "kind": "release-gate-check",
            "id": selected["id"],
            "summary": selected["error"],
            "rationale": "This is the first failed check in the canonical release-check order.",
            "evidence_paths": [release_gate["evidence_path"]],
        }
    if release_gate and release_gate["_schema_version"] != "2.0.0":
        return {
            "kind": "release-gate-version",
            "id": "current-release-gate-v2-required",
            "summary": "A current v2 release-gate report is required for this repository subject.",
            "rationale": "Historical v1 evidence remains readable but cannot satisfy the current release gate.",
            "evidence_paths": [release_gate["evidence_path"]],
        }
    if disabled_profiles:
        selected = disabled_profiles[0]
        return {
            "kind": "disabled-scoring-profile",
            "id": selected["profile_id"],
            "summary": selected["reason"],
            "rationale": "No higher-priority evidence or maturity blocker exists; disabled profiles are ordered by platform and ID.",
            "evidence_paths": [
                "control-plane/manifests/scoring-profiles.json",
                "control-plane/manifests/control-registry.json",
            ],
        }
    if disabled_capabilities:
        selected = disabled_capabilities[0]
        return {
            "kind": "disabled-capability",
            "id": f"{selected['platform']}/{selected['capability_id']}",
            "summary": selected["reason"],
            "rationale": "No higher-priority evidence or maturity blocker exists; disabled capabilities are ordered by platform and ID.",
            "evidence_paths": ["control-plane/manifests/capability-manifest.json"],
        }
    unsatisfied = [level for level in levels if not level["satisfied"]]
    if unsatisfied:
        selected = unsatisfied[0]
        return {
            "kind": "unsatisfied-maturity-level",
            "id": selected["id"],
            "summary": selected["requirements"][0],
            "rationale": "This is the lowest-ordinal unsatisfied maturity level.",
            "evidence_paths": ["control-plane/manifests/maturity-status.json", *selected["evidence"]],
        }
    return {
        "kind": "none",
        "id": "release-ready",
        "summary": "No repository-artifact blocker is declared.",
        "rationale": "All inspected artifact states are satisfied and no disabled surface remains.",
        "evidence_paths": ["control-plane/manifests/maturity-status.json"],
    }


def evaluate_product_status(
    root: str | Path,
    *,
    as_of: date,
    release_gate_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return repository-only product status and one deterministic next blocker."""

    repo_root = Path(root).resolve()
    manifests = repo_root / "control-plane" / "manifests"
    maturity_document = _read_json(manifests / "maturity-status.json", "maturity status")
    claim_document = _read_json(manifests / "claim-ledger.json", "claim ledger")
    source_document = _read_json(manifests / "source-ledger.json", "source ledger")
    capability_document = _read_json(manifests / "capability-manifest.json", "capability manifest")
    current, levels, blockers = _validate_maturity(maturity_document)
    stale, unverified = _validate_evidence_ledgers(claim_document, source_document, as_of)
    disabled_capabilities = _disabled_capabilities(capability_document)
    try:
        registry = load_control_registry(repo_root)
    except RegistryError as exc:
        raise ProductStatusError(f"control registry is invalid: {exc}") from exc
    disabled_profiles = sorted(
        (
            {
                "platform": profile.platform,
                "profile_id": profile.profile_id,
                "reason": profile.disabled_reason or "disabled without reason",
            }
            for profile in registry.profiles
            if profile.status == "disabled"
        ),
        key=lambda item: (item["platform"], item["profile_id"]),
    )
    gate_path = None if release_gate_path is None else Path(release_gate_path)
    release_gate = _release_gate(gate_path, repo_root)
    public_release_gate = (
        None
        if release_gate is None
        else {key: value for key, value in release_gate.items() if not key.startswith("_")}
    )
    next_level = next((level["id"] for level in levels if not level["satisfied"]), None)
    next_blocker = _next_blocker(
        stale=stale,
        unverified=unverified,
        blockers=blockers,
        release_gate=release_gate,
        disabled_profiles=disabled_profiles,
        disabled_capabilities=disabled_capabilities,
        levels=levels,
    )
    return {
        "schema_version": STATUS_SCHEMA_VERSION,
        "evidence_class": "repository-artifact-status",
        "as_of": as_of.isoformat(),
        "selection_policy": "artifact-order-v1",
        "maturity": {
            "current": current,
            "next_level": next_level,
            "evaluated_at": maturity_document["evaluated_at"],
            "levels": [
                {"id": level["id"], "ordinal": level["ordinal"], "satisfied": level["satisfied"]}
                for level in levels
            ],
            "declared_blockers": blockers,
        },
        "evidence": {
            "stale_load_bearing_claims": stale,
            "unverified_load_bearing_claims": unverified,
        },
        "capabilities": {"disabled": disabled_capabilities},
        "scoring_profiles": {"disabled": disabled_profiles},
        "release_gate": public_release_gate,
        "next_blocker": next_blocker,
    }
