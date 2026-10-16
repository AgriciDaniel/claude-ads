"""Versioned, fail-closed control registry and platform scoring profiles.

The audit catalog is useful for discovery, but a named check is not automatically
a scoreable control.  This loader enforces that distinction at runtime.  Only an
enabled profile whose health controls resolve to verified, load-bearing claims
may enter the deterministic scoring engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import PLATFORMS, ContractError, validate_contract
from .scoring import ScoreResult, score_account

REGISTRY_SCHEMA_VERSION = "1.0.0"
REGISTRY_VERSION = "1.0.0"
PROFILE_VERSION = "1.0.0"
DISPOSITIONS = {"conditional_watchlist", "source_refresh_discovery", "opportunity", "health"}
PROFILE_STATUSES = {"disabled", "enabled"}


class RegistryError(ValueError):
    """Raised when registry or scoring-profile state is unsafe or inconsistent."""


@dataclass(frozen=True)
class RegistryEntry:
    platform: str
    control_id: str
    intent: str
    disposition: str
    source_claim_ids: tuple[str, ...]
    control_definition: Mapping[str, Any]


@dataclass(frozen=True)
class ScoringProfile:
    profile_id: str
    platform: str
    status: str
    category_weights: Mapping[str, float]
    health_control_ids: tuple[str, ...]
    disabled_reason: str | None


@dataclass(frozen=True)
class ControlRegistry:
    entries: tuple[RegistryEntry, ...]
    profiles: tuple[ScoringProfile, ...]

    def entries_for(self, platform: str) -> tuple[RegistryEntry, ...]:
        normalized = platform.lower()
        if normalized not in PLATFORMS:
            raise RegistryError(f"unsupported platform: {platform}")
        return tuple(entry for entry in self.entries if entry.platform == normalized)

    def controls_for(self, platform: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(entry.control_definition for entry in self.entries_for(platform))

    def profile_for(self, platform: str) -> ScoringProfile:
        normalized = platform.lower()
        for profile in self.profiles:
            if profile.platform == normalized:
                return profile
        raise RegistryError(f"no scoring profile for platform: {platform}")

    def scoring_inputs(self, platform: str) -> tuple[tuple[Mapping[str, Any], ...], Mapping[str, float]]:
        """Return approved health controls and weights, or fail closed."""

        profile = self.profile_for(platform)
        if profile.status != "enabled":
            raise RegistryError(
                f"scoring profile {profile.profile_id} is disabled: {profile.disabled_reason}"
            )
        entries = {entry.control_id: entry for entry in self.entries_for(platform)}
        return (
            tuple(entries[control_id].control_definition for control_id in profile.health_control_ids),
            profile.category_weights,
        )

    def canonical_scoring_inputs(
        self, platform: str
    ) -> tuple[tuple[Mapping[str, Any], ...], Mapping[str, float]]:
        """Return exact public scoring inputs, including the disabled empty set."""

        profile = self.profile_for(platform)
        if profile.status != "enabled":
            return (), {}
        return self.scoring_inputs(platform)

    def validate_findings(
        self,
        platform: str,
        findings: Sequence[Mapping[str, Any]],
    ) -> None:
        """Validate finding contracts and bind their IDs to one platform."""

        canonical_ids = {entry.control_id for entry in self.entries_for(platform)}
        seen: set[str] = set()
        for index, finding in enumerate(findings):
            try:
                validate_contract("finding", finding)
            except ContractError as exc:
                raise RegistryError(f"findings[{index}]: {exc}") from exc
            control_id = str(finding["control_id"])
            if control_id not in canonical_ids:
                raise RegistryError(
                    f"finding references a non-canonical {platform} control: {control_id}"
                )
            if control_id in seen:
                raise RegistryError(f"duplicate finding for control_id: {control_id}")
            seen.add(control_id)

    def score_platform(
        self,
        platform: str,
        findings: Sequence[Mapping[str, Any]],
    ) -> ScoreResult:
        """Score through the approved profile; disabled profiles yield no health.

        A disabled profile means no evidence obligation has been approved, so its
        evidence coverage is zero rather than the scoring engine's normal 100%
        result for an empty set of applicable controls.
        """

        self.validate_findings(platform, findings)
        profile = self.profile_for(platform)
        if profile.status != "enabled":
            return ScoreResult(
                health_score=None,
                evidence_coverage=0.0,
                status="insufficient_evidence",
                categories=(),
            )
        controls, weights = self.scoring_inputs(platform)
        return score_account(controls, findings, weights)


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot load {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise RegistryError(f"{path} must contain a JSON object")
    return payload


def _nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{path} must be a non-empty string")
    return value


def _string_tuple(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise RegistryError(f"{path} must be an array")
    result = tuple(_nonempty_string(item, f"{path}[{index}]") for index, item in enumerate(value))
    if len(result) != len(set(result)):
        raise RegistryError(f"{path} must contain unique values")
    return result


def _verified_claims(claim_ledger: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    claims = claim_ledger.get("claims")
    if not isinstance(claims, list):
        raise RegistryError("claim ledger claims must be an array")
    result: dict[str, Mapping[str, Any]] = {}
    for index, raw_claim in enumerate(claims):
        if not isinstance(raw_claim, Mapping):
            raise RegistryError(f"claim ledger claims[{index}] must be an object")
        claim_id = _nonempty_string(raw_claim.get("id"), f"claim ledger claims[{index}].id")
        if claim_id in result:
            raise RegistryError(f"duplicate claim id: {claim_id}")
        result[claim_id] = raw_claim
    return result


def _known_sources(source_ledger: Mapping[str, Any]) -> set[str]:
    sources = source_ledger.get("sources")
    if not isinstance(sources, list):
        raise RegistryError("source ledger sources must be an array")
    result: set[str] = set()
    for index, raw_source in enumerate(sources):
        if not isinstance(raw_source, Mapping):
            raise RegistryError(f"source ledger sources[{index}] must be an object")
        source_id = _nonempty_string(raw_source.get("id"), f"source ledger sources[{index}].id")
        if source_id in result:
            raise RegistryError(f"duplicate source id: {source_id}")
        result.add(source_id)
    return result


def _validate_entry(
    raw_entry: Any,
    index: int,
    claims: Mapping[str, Mapping[str, Any]],
    sources: set[str],
) -> RegistryEntry:
    if not isinstance(raw_entry, Mapping):
        raise RegistryError(f"controls[{index}] must be an object")
    platform = _nonempty_string(raw_entry.get("platform"), f"controls[{index}].platform").lower()
    if platform not in PLATFORMS:
        raise RegistryError(f"controls[{index}].platform is unsupported")
    control_id = _nonempty_string(raw_entry.get("control_id"), f"controls[{index}].control_id")
    intent = _nonempty_string(raw_entry.get("intent"), f"controls[{index}].intent")
    disposition = _nonempty_string(raw_entry.get("disposition"), f"controls[{index}].disposition")
    if disposition not in DISPOSITIONS:
        raise RegistryError(f"controls[{index}].disposition is invalid")
    claim_ids = _string_tuple(raw_entry.get("source_claim_ids"), f"controls[{index}].source_claim_ids")
    definition = raw_entry.get("control_definition")
    if not isinstance(definition, Mapping):
        raise RegistryError(f"controls[{index}].control_definition must be an object")
    try:
        validate_contract("control-definition", definition)
    except ContractError as exc:
        raise RegistryError(f"controls[{index}].control_definition: {exc}") from exc
    if definition["control_id"] != control_id:
        raise RegistryError(f"controls[{index}] control_id does not match its definition")
    expected_behavior = "health" if disposition == "health" else (
        "opportunity" if disposition == "opportunity" else "watchlist"
    )
    if definition["scoring_behavior"] != expected_behavior:
        raise RegistryError(f"{control_id} disposition does not match scoring_behavior")
    definition_sources = set(_string_tuple(definition["source_ids"], f"{control_id}.source_ids"))
    unknown_sources = definition_sources - sources
    if unknown_sources:
        raise RegistryError(f"{control_id} references unknown sources: {sorted(unknown_sources)}")
    for claim_id in claim_ids:
        if claim_id not in claims:
            raise RegistryError(f"{control_id} references unknown claim: {claim_id}")
        claim_sources = set(claims[claim_id].get("source_ids", []))
        if not definition_sources <= claim_sources:
            raise RegistryError(f"{control_id} source_ids are not supported by claim {claim_id}")
    if disposition == "health":
        if not claim_ids or not definition_sources or not definition["required_inputs"]:
            raise RegistryError(f"health control {control_id} lacks typed evidence grounding")
        if definition["severity"] == "informational":
            raise RegistryError(f"health control {control_id} has zero-weight severity")
        if definition["maturity"] not in {"source-grounded", "domain-integrated", "eval-verified", "release-ready"}:
            raise RegistryError(f"health control {control_id} is not source-grounded")
        if definition["stability"] != "stable":
            raise RegistryError(f"health control {control_id} is not stable")
        for claim_id in claim_ids:
            claim = claims[claim_id]
            if claim.get("verdict") != "verified" or claim.get("load_bearing") is not True:
                raise RegistryError(f"health control {control_id} uses an unverified claim: {claim_id}")
    elif definition["severity"] != "informational":
        raise RegistryError(f"unscored control {control_id} must remain informational")
    return RegistryEntry(platform, control_id, intent, disposition, claim_ids, definition)


def _validate_profile(raw_profile: Any, index: int, entries: Mapping[tuple[str, str], RegistryEntry]) -> ScoringProfile:
    if not isinstance(raw_profile, Mapping):
        raise RegistryError(f"profiles[{index}] must be an object")
    profile_id = _nonempty_string(raw_profile.get("profile_id"), f"profiles[{index}].profile_id")
    platform = _nonempty_string(raw_profile.get("platform"), f"profiles[{index}].platform").lower()
    if platform not in PLATFORMS:
        raise RegistryError(f"profiles[{index}].platform is unsupported")
    status = _nonempty_string(raw_profile.get("status"), f"profiles[{index}].status")
    if status not in PROFILE_STATUSES:
        raise RegistryError(f"profiles[{index}].status is invalid")
    raw_weights = raw_profile.get("category_weights")
    if not isinstance(raw_weights, Mapping):
        raise RegistryError(f"profiles[{index}].category_weights must be an object")
    weights: dict[str, float] = {}
    for category, raw_weight in raw_weights.items():
        if not isinstance(category, str) or not category:
            raise RegistryError(f"profiles[{index}] category names must be non-empty strings")
        if isinstance(raw_weight, bool) or not isinstance(raw_weight, (int, float)):
            raise RegistryError(f"profiles[{index}].category_weights.{category} must be numeric")
        weights[category] = float(raw_weight)
    health_ids = _string_tuple(raw_profile.get("health_control_ids"), f"profiles[{index}].health_control_ids")
    disabled_reason = raw_profile.get("disabled_reason")
    if disabled_reason is not None:
        disabled_reason = _nonempty_string(disabled_reason, f"profiles[{index}].disabled_reason")
    if status == "disabled":
        if weights or health_ids or disabled_reason is None:
            raise RegistryError(f"disabled profile {profile_id} requires only an explicit reason")
    else:
        if disabled_reason is not None or not health_ids or sum(weights.values()) != 100.0:
            raise RegistryError(f"enabled profile {profile_id} requires controls and weights totaling 100")
        selected: list[RegistryEntry] = []
        for control_id in health_ids:
            entry = entries.get((platform, control_id))
            if entry is None:
                raise RegistryError(f"profile {profile_id} references unknown control {control_id}")
            if entry.disposition != "health":
                raise RegistryError(f"profile {profile_id} references unscored control {control_id}")
            selected.append(entry)
        categories = {str(entry.control_definition["category"]) for entry in selected}
        if set(weights) != categories:
            raise RegistryError(f"profile {profile_id} weights do not exactly match health-control categories")
    return ScoringProfile(profile_id, platform, status, weights, health_ids, disabled_reason)


def load_control_registry(root: str | Path) -> ControlRegistry:
    """Load and semantically validate the repository control-plane registry."""

    repo_root = Path(root).resolve()
    manifest_root = repo_root / "control-plane" / "manifests"
    registry_payload = _read_json(manifest_root / "control-registry.json")
    profile_payload = _read_json(manifest_root / "scoring-profiles.json")
    claims = _verified_claims(_read_json(manifest_root / "claim-ledger.json"))
    sources = _known_sources(_read_json(manifest_root / "source-ledger.json"))
    if registry_payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise RegistryError("unsupported control-registry schema_version")
    if registry_payload.get("registry_version") != REGISTRY_VERSION:
        raise RegistryError("unsupported control-registry registry_version")
    if profile_payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise RegistryError("unsupported scoring-profiles schema_version")
    if profile_payload.get("profile_version") != PROFILE_VERSION:
        raise RegistryError("unsupported scoring-profiles profile_version")
    raw_entries = registry_payload.get("controls")
    if not isinstance(raw_entries, list):
        raise RegistryError("control registry controls must be an array")
    entries = tuple(_validate_entry(raw, index, claims, sources) for index, raw in enumerate(raw_entries))
    by_key: dict[tuple[str, str], RegistryEntry] = {}
    for entry in entries:
        key = (entry.platform, entry.control_id)
        if key in by_key:
            raise RegistryError(f"duplicate platform control: {entry.platform}/{entry.control_id}")
        by_key[key] = entry
    if {entry.platform for entry in entries} != PLATFORMS:
        raise RegistryError("control registry must cover exactly the twelve supported platforms")
    raw_profiles = profile_payload.get("profiles")
    if not isinstance(raw_profiles, list):
        raise RegistryError("scoring profiles must be an array")
    profiles = tuple(_validate_profile(raw, index, by_key) for index, raw in enumerate(raw_profiles))
    profile_platforms = [profile.platform for profile in profiles]
    if set(profile_platforms) != PLATFORMS or len(profile_platforms) != len(PLATFORMS):
        raise RegistryError("scoring profiles must define exactly one profile per supported platform")
    return ControlRegistry(entries, profiles)
