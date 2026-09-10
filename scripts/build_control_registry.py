#!/usr/bin/env python3
"""Rebuild the checked-in typed registry from the canonical catalog/references."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$")

# Narrow mappings only: each listed catalog intent is directly within the
# corresponding verified claim's scope.  The mappings ground discovery; they do
# not assign severity or make a control scoreable.
CLAIM_SUPPORT: dict[tuple[str, str], tuple[tuple[str, ...], tuple[str, ...]]] = {
    ("google", "G42"): (("CLM-0007",), ("google-ads-conversion-goals-official",)),
    ("google", "G43"): (("CLM-0007",), ("google-ads-enhanced-conversions-official",)),
    ("google", "G96"): (("CLM-0211",), ("google-ads-dsa-ad-rank-official", "google-ads-keyword-prioritization-official")),
    ("google", "G97"): (("CLM-0210",), ("google-ads-keyword-prioritization-official",)),
    ("meta", "M01"): (("CLM-0008",), ("meta-conversions-api-official",)),
    ("meta", "M02"): (("CLM-0008",), ("meta-conversions-api-official",)),
    ("meta", "M03"): (("CLM-0008",), ("meta-conversions-api-official",)),
    ("linkedin", "L01"): (("CLM-0009",), ("linkedin-conversion-tracking-official",)),
    ("linkedin", "L02"): (("CLM-0009",), ("linkedin-conversions-api-official",)),
    ("tiktok", "T01"): (("CLM-0010",), ("tiktok-pixel-official",)),
    ("microsoft", "MS01"): (("CLM-0011",), ("microsoft-uet-official",)),
    ("microsoft", "MS03"): (("CLM-0011",), ("microsoft-google-import-official",)),
    ("reddit", "RD-M02"): (("CLM-0015",), ("reddit-business-help",)),
    ("reddit", "RD-M03"): (("CLM-0015",), ("reddit-business-help",)),
    ("pinterest", "PN-M01"): (("CLM-0016",), ("pinterest-conversions-api",)),
    ("pinterest", "PN-M02"): (("CLM-0016",), ("pinterest-conversions-api",)),
}


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML is required to rebuild the control registry") from exc
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain an object")
    return payload


def _reference_rows(path: Path) -> tuple[bool, dict[str, tuple[str, str]]]:
    text = path.read_text(encoding="utf-8")
    categorized = "| ID | Category |" in text
    rows: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        match = ROW.match(line)
        if not match:
            continue
        first, second, third = (part.strip() for part in match.groups())
        if first == "ID" or set(first) == {"-"}:
            continue
        rows[first] = (second, third)
    return categorized, rows


def build(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    catalog = _load_yaml(root / "tests" / "fixtures" / "check-catalog.yaml")
    claim_payload = json.loads(
        (root / "control-plane" / "manifests" / "claim-ledger.json").read_text(encoding="utf-8")
    )
    claims = {claim["id"]: claim for claim in claim_payload["claims"]}
    controls: list[dict[str, Any]] = []
    for platform, platform_data in catalog["platforms"].items():
        categorized, rows = _reference_rows(root / platform_data["reference"])
        for control_id in platform_data["check_ids"]:
            if control_id not in rows:
                raise SystemExit(f"missing reference row: {platform}/{control_id}")
            second, third = rows[control_id]
            if categorized:
                category = second.lower().replace(" ", "-")
                intent = third
                disposition = "conditional_watchlist"
            else:
                category = "unclassified"
                intent = second
                disposition = (
                    "source_refresh_discovery"
                    if third.startswith("Unscored source-refresh discovery")
                    else "conditional_watchlist"
                )
            claim_ids, source_ids = CLAIM_SUPPORT.get((platform, control_id), ((), ()))
            for claim_id in claim_ids:
                unsupported = set(source_ids) - set(claims[claim_id]["source_ids"])
                if unsupported:
                    raise SystemExit(
                        f"{platform}/{control_id} maps sources outside {claim_id}: {sorted(unsupported)}"
                    )
            controls.append(
                {
                    "platform": platform,
                    "control_id": control_id,
                    "intent": intent,
                    "disposition": disposition,
                    "source_claim_ids": list(claim_ids),
                    "control_definition": {
                        "schema_version": "1.0.0",
                        "control_id": control_id,
                        "category": category,
                        "severity": "informational",
                        "required_inputs": [
                            "applicability_context",
                            "current_account_evidence",
                            "current_source_support",
                        ],
                        "source_ids": list(source_ids),
                        "maturity": "source-grounded" if claim_ids else "inventory-baselined",
                        "geographies": ["account-configured"],
                        "scoring_behavior": "watchlist",
                        "stability": "experimental",
                    },
                }
            )
    reason = (
        "No approved source-grounded control-severity decision set exists; "
        "enabling health would invent severity or category weights."
    )
    profiles = [
        {
            "profile_id": f"{platform}-health-v1",
            "platform": platform,
            "status": "disabled",
            "category_weights": {},
            "health_control_ids": [],
            "disabled_reason": reason,
        }
        for platform in sorted(catalog["platforms"])
    ]
    return (
        {
            "schema_version": "1.0.0",
            "registry_version": "1.0.0",
            "catalog_version": str(catalog["version"]),
            "controls": controls,
        },
        {
            "schema_version": "1.0.0",
            "profile_version": "1.0.0",
            "profiles": profiles,
        },
    )


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    registry, profiles = build(root)
    manifest_root = root / "control-plane" / "manifests"
    (manifest_root / "control-registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (manifest_root / "scoring-profiles.json").write_text(
        json.dumps(profiles, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
