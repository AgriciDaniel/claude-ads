"""Audit runner service -- orchestrates fetch -> audit -> save."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auditors.google_ads import run_audit
from app.connectors.google_ads import GoogleAdsData, fetch_account_data
from app.models.database import (
    Audit,
    AuditStatus,
    CheckResult,
    CheckStatus,
    GoogleAdsAccount,
    Severity,
    async_session,
)

logger = logging.getLogger(__name__)


async def execute_audit(audit_id: UUID, customer_id: str, refresh_token: str) -> None:
    """Run a full Google Ads audit and persist results.

    This function is designed to be called from a BackgroundTask so it
    manages its own DB session.

    Steps:
      1. Mark audit as RUNNING
      2. Fetch data from Google Ads API
      3. Run the auditor checks
      4. Save check results and overall score
      5. Mark audit as COMPLETED (or FAILED on error)
    """
    async with async_session() as db:
        try:
            # 1. Mark as running
            audit = await db.get(Audit, audit_id)
            if not audit:
                logger.error("Audit %s not found", audit_id)
                return

            audit.status = AuditStatus.RUNNING
            audit.started_at = datetime.now(timezone.utc)
            await db.commit()

            # 2. Fetch data (sync call -- runs in default executor)
            import asyncio
            loop = asyncio.get_event_loop()
            data: GoogleAdsData = await loop.run_in_executor(
                None, fetch_account_data, customer_id, refresh_token,
            )

            # 3. Run auditor
            result = run_audit(data)

            # 4. Save check results
            for cr in result.check_results:
                severity_val = cr["severity"].upper()
                status_val = cr["status"].upper()
                # Map status names to enum values
                status_map = {
                    "PASS": CheckStatus.PASS,
                    "WARNING": CheckStatus.WARNING,
                    "FAIL": CheckStatus.FAIL,
                    "NA": CheckStatus.NA,
                }
                severity_map = {
                    "CRITICAL": Severity.CRITICAL,
                    "HIGH": Severity.HIGH,
                    "MEDIUM": Severity.MEDIUM,
                    "LOW": Severity.LOW,
                }
                db.add(CheckResult(
                    audit_id=audit_id,
                    check_id=cr["check_id"],
                    check_name=cr["name"],
                    category=cr["category"],
                    severity=severity_map.get(severity_val, Severity.MEDIUM),
                    status=status_map.get(status_val, CheckStatus.NA),
                    score=cr.get("score", 0),
                    detail=cr.get("detail", ""),
                    fix=cr.get("fix", ""),
                    fix_time_minutes=cr.get("fix_time_minutes", 0),
                    is_quick_win=1 if cr.get("is_quick_win") else 0,
                ))

            # 5. Update audit record
            audit.score = result.score
            audit.grade = result.grade
            audit.summary = result.summary
            audit.raw_data = {
                "category_scores": result.category_scores,
            }
            audit.status = AuditStatus.COMPLETED
            audit.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info("Audit %s completed: score=%.1f grade=%s",
                        audit_id, result.score, result.grade)

        except Exception:
            logger.exception("Audit %s failed", audit_id)
            try:
                audit = await db.get(Audit, audit_id)
                if audit:
                    audit.status = AuditStatus.FAILED
                    audit.summary = f"Audit failed: {traceback.format_exc()[-500:]}"
                    audit.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                logger.exception("Failed to mark audit %s as failed", audit_id)
