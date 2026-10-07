"""Registry-backed semantic validation for public report operations."""

from __future__ import annotations

from typing import Any, Mapping

from .contracts import ContractError, validate_contract
from .control_registry import ControlRegistry, RegistryError


def validate_report_bundle_policy(
    bundle: Mapping[str, Any],
    registry: ControlRegistry,
) -> None:
    """Reject bundles whose account controls or score are not registry-derived."""

    try:
        validate_contract("report-bundle", bundle)
    except ContractError as exc:
        raise RegistryError(f"invalid report bundle: {exc}") from exc

    raw_platform = str(bundle["account_snapshot"]["account"]["platform"])
    platform = raw_platform.lower()
    if raw_platform != platform:
        raise RegistryError(
            f"report account platform must use canonical lowercase ID: {raw_platform}"
        )
    manifest = bundle["run_manifest"]
    adapter_platforms = {
        str(adapter["platform"])
        for adapter in manifest["adapters"]
    }
    if platform not in adapter_platforms:
        raise RegistryError(
            f"report account platform {platform} has no matching run-manifest adapter"
        )
    worker_status = manifest["worker_status"]
    if platform not in worker_status:
        raise RegistryError(
            f"report account platform {platform} has no matching worker status"
        )
    if manifest["completeness"] == "complete":
        if not worker_status:
            raise RegistryError("complete report requires at least one worker status")
        unfinished = sorted(
            worker
            for worker, status in worker_status.items()
            if status not in {"completed", "skipped"}
        )
        if unfinished:
            raise RegistryError(
                "complete report has unfinished or failed workers: "
                + ", ".join(unfinished)
            )
    canonical = {
        entry.control_id: dict(entry.control_definition)
        for entry in registry.entries_for(platform)
    }
    supplied: dict[str, Mapping[str, Any]] = {}
    for raw_control in bundle["control_definitions"]:
        control_id = str(raw_control["control_id"])
        if control_id in supplied:
            raise RegistryError(f"duplicate report control definition: {control_id}")
        if canonical.get(control_id) != raw_control:
            raise RegistryError(
                f"report control definition is not canonical for {platform}: {control_id}"
            )
        supplied[control_id] = raw_control

    finding_ids: set[str] = set()
    for index, finding in enumerate(bundle["findings"]):
        control_id = str(finding["control_id"])
        if control_id in finding_ids:
            raise RegistryError(f"duplicate report finding: {control_id}")
        if control_id not in supplied:
            raise RegistryError(
                f"report finding has no canonical control definition: {control_id}"
            )
        finding_ids.add(control_id)

    expected = registry.score_platform(platform, bundle["findings"]).to_dict()
    if bundle["scoring"] != expected:
        raise RegistryError(
            f"report scoring does not match canonical {platform} scoring profile"
        )
