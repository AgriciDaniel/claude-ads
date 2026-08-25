"""Fail-closed normalization of versioned native advertising report projections."""

from __future__ import annotations

import csv
import math
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from os import PathLike
from pathlib import Path
from typing import Any, Mapping

from ..contracts import ContractError, validate_contract
from ..models import AccountSnapshot
from .base import AdapterCapabilities, AdapterError, BaseAdapter, Capability
from .csv_export import MAX_EXPORT_BYTES, MAX_EXPORT_COLUMNS, MAX_EXPORT_ROWS
from .mappings_v1 import NativeFieldMapping, get_native_profile


class NativeExportError(AdapterError):
    """Raised when a native report does not satisfy its exact versioned profile."""


def _nonempty(value: str | None, label: str, row_number: int | None = None) -> str:
    if value is None or not value.strip():
        prefix = f"row {row_number}: " if row_number is not None else ""
        raise NativeExportError(f"{prefix}{label} must not be empty")
    return value.strip()


def _decimal(value: str, label: str, row_number: int) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise NativeExportError(f"row {row_number}: {label} must be numeric") from exc
    if not number.is_finite() or number < 0:
        raise NativeExportError(f"row {row_number}: {label} must be a finite non-negative number")
    return number


def _float(value: Decimal) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise NativeExportError("numeric value is outside the supported finite range")
    return number


def _transform(mapping: NativeFieldMapping, value: str, row_number: int) -> str | date | Decimal:
    if mapping.transform == "text":
        return value
    if mapping.transform == "lower_text":
        return value.lower()
    if mapping.transform == "linkedin_campaign_urn":
        prefix = "urn:li:sponsoredCampaign:"
        suffix = value.removeprefix(prefix)
        if not value.startswith(prefix) or not suffix.isdigit():
            raise NativeExportError(
                f"row {row_number}: {mapping.source} must be a sponsoredCampaign URN from a CAMPAIGN pivot"
            )
        return value
    if mapping.transform == "iso_date":
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise NativeExportError(f"row {row_number}: {mapping.source} must be an ISO 8601 date") from exc
    if mapping.transform == "iso_datetime_date":
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise NativeExportError(
                f"row {row_number}: {mapping.source} must be an ISO 8601 timestamp with offset"
            ) from exc
        if parsed.tzinfo is None:
            raise NativeExportError(
                f"row {row_number}: {mapping.source} must include a timezone offset"
            )
        return parsed.date()
    if mapping.transform == "decimal":
        return _decimal(value, mapping.source, row_number)
    if mapping.transform == "micros":
        return _decimal(value, mapping.source, row_number) / Decimal("1000000")
    raise NativeExportError(f"unsupported transform in profile: {mapping.transform}")


class NativeCSVExportAdapter(BaseAdapter):
    """Normalize one exact official-report CSV projection.

    Profiles are intentionally strict: every mapped header must be present,
    extra headers are rejected, required request-scope context must be bound,
    and disabled profiles never attempt best-effort inference.  JSON APIs may be
    serialized as CSV after deterministic dot-path flattening; the profile's
    ``source_format`` says when that projection is required.
    """

    def __init__(self, platform: str, context: Mapping[str, str] | None = None) -> None:
        try:
            self.profile = get_native_profile(platform)
        except ValueError as exc:
            raise NativeExportError(str(exc)) from exc
        self.platform = self.profile.platform
        self.adapter_id = self.profile.profile_id
        supplied = dict(context or {})
        unknown_context = sorted(set(supplied) - set(self.profile.required_context))
        if unknown_context:
            raise NativeExportError(
                f"{self.profile.profile_id} does not accept context field(s): {', '.join(unknown_context)}"
            )
        self.context = {
            field: _nonempty(supplied.get(field), f"context.{field}")
            for field in self.profile.required_context
        }

    def discover_capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            schema_version="1.0.0",
            adapter_id=self.adapter_id,
            platform=self.platform,
            default_mutation_mode="read-only",
            capabilities=(
                Capability(
                    "native-export-normalization",
                    "export-read",
                    self.profile.status,
                    self.profile.disabled_reason,
                ),
                Capability(
                    "account-mutation",
                    "live-write",
                    "disabled",
                    "Native report adapters have no authenticated write destination.",
                ),
            ),
        )

    def read_snapshot(self, source: str | PathLike[str]) -> AccountSnapshot:
        if self.profile.status == "disabled":
            raise NativeExportError(
                f"{self.profile.profile_id} is disabled: {self.profile.disabled_reason}"
            )
        path = Path(source)
        try:
            if not path.is_file():
                raise NativeExportError(f"export is not a regular file: {path}")
            size = path.stat().st_size
        except OSError as exc:
            raise NativeExportError(f"cannot inspect export: {exc}") from exc
        if size > MAX_EXPORT_BYTES:
            raise NativeExportError(f"export exceeds {MAX_EXPORT_BYTES} byte limit")

        rows: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, strict=True)
                headers = reader.fieldnames or []
                self._validate_headers(headers)
                for row_number, row in enumerate(reader, start=2):
                    if row_number - 1 > MAX_EXPORT_ROWS:
                        raise NativeExportError(f"export exceeds {MAX_EXPORT_ROWS} row limit")
                    rows.append(self._normalize_row(row, row_number))
        except (OSError, UnicodeError, csv.Error) as exc:
            raise NativeExportError(f"cannot read export: {exc}") from exc
        if not rows:
            raise NativeExportError("export must contain at least one data row")
        return self._build_snapshot(rows)

    def _validate_headers(self, headers: list[str]) -> None:
        if len(headers) > MAX_EXPORT_COLUMNS:
            raise NativeExportError(f"export exceeds {MAX_EXPORT_COLUMNS} column limit")
        duplicates = sorted(field for field, count in Counter(headers).items() if count > 1)
        if duplicates:
            raise NativeExportError(f"export contains duplicate column(s): {', '.join(duplicates)}")
        expected = set(self.profile.expected_headers)
        actual = set(headers)
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            raise NativeExportError(f"export missing profile column(s): {', '.join(missing)}")
        if extra:
            raise NativeExportError(
                "export contains unmapped column(s); select the exact versioned report projection: "
                + ", ".join(extra)
            )

    def _normalize_row(self, row: Mapping[str, str | None], row_number: int) -> dict[str, Any]:
        normalized: dict[str, Any] = dict(self.context)
        for mapping in self.profile.fields:
            value = _nonempty(row.get(mapping.source), mapping.source, row_number)
            normalized[mapping.target] = _transform(mapping, value, row_number)
        for guard in self.profile.guards:
            value = _nonempty(row.get(guard.source), guard.source, row_number)
            if guard.allowed_values and value not in guard.allowed_values:
                raise NativeExportError(
                    f"row {row_number}: {guard.source}={value!r} is outside profile values "
                    f"{', '.join(guard.allowed_values)}"
                )
            if guard.forbidden_values and value in guard.forbidden_values:
                raise NativeExportError(
                    f"row {row_number}: {guard.source}={value!r} routes to a different platform profile"
                )
        for check in self.profile.date_checks:
            left = normalized[check.left_target]
            right = normalized[check.right_target]
            valid = (
                left == right
                if check.relation == "same_date"
                else right == left + timedelta(days=1)
            )
            if not valid:
                raise NativeExportError(
                    f"row {row_number}: native report date relationship {check.relation} failed"
                )
        required = ("date", "account_id", "currency", "campaign_id", "spend")
        missing = [field for field in required if field not in normalized]
        if missing:
            raise NativeExportError(
                f"{self.profile.profile_id} cannot produce required normalized field(s): {', '.join(missing)}"
            )
        currency = str(normalized["currency"])
        if len(currency) != 3 or not currency.isalpha() or currency != currency.upper():
            raise NativeExportError(f"row {row_number}: currency must be a three-letter uppercase code")
        return normalized

    def _build_snapshot(self, rows: list[dict[str, Any]]) -> AccountSnapshot:
        account_ids = {str(row["account_id"]) for row in rows}
        currencies = {str(row["currency"]) for row in rows}
        account_names = {str(row["account_name"]) for row in rows if "account_name" in row}
        if len(account_ids) != 1:
            raise NativeExportError("export must contain exactly one normalized account_id")
        if len(currencies) != 1:
            raise NativeExportError("export must contain exactly one normalized currency")
        if len(account_names) > 1:
            raise NativeExportError("export contains conflicting normalized account_name values")

        campaigns: dict[str, dict[str, Any]] = {}
        creatives: dict[str, dict[str, Any]] = {}
        conversions = Decimal("0")
        budgets: dict[tuple[str, date], Decimal] = {}
        grains: set[tuple[Any, ...]] = set()
        total_spend = Decimal("0")
        for row in rows:
            grain = tuple(row[field] for field in self.profile.report_grain)
            if grain in grains:
                raise NativeExportError(f"export contains duplicate native report grain: {grain!r}")
            grains.add(grain)
            campaign_id = str(row["campaign_id"])
            campaign = {"campaign_id": campaign_id}
            if "campaign_name" in row:
                campaign["name"] = str(row["campaign_name"])
            if "campaign_status" in row:
                campaign["status"] = str(row["campaign_status"])
            existing = campaigns.get(campaign_id)
            identity = {key: value for key, value in campaign.items() if key != "spend"}
            if existing and {key: value for key, value in existing.items() if key != "spend"} != identity:
                raise NativeExportError(f"campaign_id {campaign_id!r} has conflicting identity fields")
            if not existing:
                existing = {**identity, "spend": Decimal("0")}
                campaigns[campaign_id] = existing
            existing["spend"] += row["spend"]
            total_spend += row["spend"]

            if "creative_id" in row:
                creative_id = str(row["creative_id"])
                creative = {"creative_id": creative_id, "campaign_id": campaign_id}
                if "creative_name" in row:
                    creative["name"] = str(row["creative_name"])
                if creative_id in creatives and creatives[creative_id] != creative:
                    raise NativeExportError(f"creative_id {creative_id!r} has conflicting identity fields")
                creatives[creative_id] = creative

            if "conversions" in row:
                conversions += row["conversions"]
            if "budget" in row:
                key = (campaign_id, row["date"])
                if key in budgets and budgets[key] != row["budget"]:
                    raise NativeExportError(
                        f"campaign_id {campaign_id!r} has conflicting budget values for {row['date']}"
                    )
                budgets[key] = row["budget"]

        account: dict[str, Any] = {
            "platform": self.platform,
            "account_id": next(iter(account_ids)),
        }
        if account_names:
            account["name"] = next(iter(account_names))
        snapshot: AccountSnapshot = {
            "schema_version": "1.0.0",
            "account": account,
            "window": {
                "start": min(row["date"] for row in rows).isoformat(),
                "end": max(row["date"] for row in rows).isoformat(),
            },
            "currency": next(iter(currencies)),
            "spend": _float(total_spend),
            "campaigns": [
                {**campaign, "spend": _float(campaign["spend"])}
                for _, campaign in sorted(campaigns.items())
            ],
            "creatives": [creative for _, creative in sorted(creatives.items())],
            "conversions": (
                [{"action": self.profile.conversion_action, "count": _float(conversions)}]
                if self.profile.conversion_action is not None
                else []
            ),
            "budgets": [
                {"campaign_id": campaign_id, "date": budget_date.isoformat(), "amount": _float(amount)}
                for (campaign_id, budget_date), amount in sorted(budgets.items())
            ],
        }
        try:
            validate_contract("account-snapshot", snapshot)
        except ContractError as exc:
            raise NativeExportError(f"normalized snapshot violates AccountSnapshot contract: {exc}") from exc
        return snapshot
