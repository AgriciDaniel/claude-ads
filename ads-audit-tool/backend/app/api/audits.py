"""Audit CRUD endpoints -- trigger, status, and list."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.models.database import (
    Audit,
    AuditStatus,
    CheckResult,
    GoogleAdsAccount,
    User,
    get_db,
)
from app.models.schemas import (
    AuditCreateRequest,
    AuditCreateResponse,
    AuditDetailResponse,
    AuditListItem,
    AuditListResponse,
    CategoryScore,
    CheckResultOut,
)
from app.services.audit_runner import execute_audit

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post("", response_model=AuditCreateResponse)
async def create_audit(
    req: AuditCreateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new audit for the given Google Ads account."""
    customer_id = req.account_id.replace("-", "")

    # Find or create account record
    result = await db.execute(
        select(GoogleAdsAccount).where(GoogleAdsAccount.customer_id == customer_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        # Create a new account record using the user's refresh token
        if not user.google_refresh_token_encrypted:
            raise HTTPException(
                status_code=400,
                detail="No Google refresh token available. Please re-authenticate.",
            )
        account = GoogleAdsAccount(
            id=uuid4(),
            customer_id=customer_id,
            refresh_token=user.google_refresh_token_encrypted,
        )
        db.add(account)
        await db.flush()

    # Create audit record
    audit = Audit(
        id=uuid4(),
        account_id=account.id,
        user_id=user.id,
        status=AuditStatus.PENDING,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    # Kick off the audit in the background
    refresh_token = account.refresh_token or user.google_refresh_token_encrypted
    background_tasks.add_task(execute_audit, audit.id, customer_id, refresh_token)

    return AuditCreateResponse(audit_id=str(audit.id), status=audit.status.value)


@router.get("/{audit_id}", response_model=AuditDetailResponse)
async def get_audit(
    audit_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit status and results."""
    result = await db.execute(
        select(Audit)
        .options(selectinload(Audit.check_results))
        .where(Audit.id == audit_id, Audit.user_id == user.id)
    )
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    # Build response
    check_results = None
    category_scores = None

    if audit.status == AuditStatus.COMPLETED and audit.check_results:
        check_results = [
            CheckResultOut(
                check_id=cr.check_id,
                check_name=cr.check_name,
                category=cr.category,
                severity=cr.severity.value,
                status=cr.status.value,
                score=cr.score or 0,
                detail=cr.detail,
                fix=cr.fix,
                fix_time_minutes=cr.fix_time_minutes,
                is_quick_win=bool(cr.is_quick_win),
            )
            for cr in audit.check_results
        ]

        # Extract category scores from raw_data
        if audit.raw_data and "category_scores" in audit.raw_data:
            category_scores = [
                CategoryScore(**cs) for cs in audit.raw_data["category_scores"]
            ]

    return AuditDetailResponse(
        audit_id=str(audit.id),
        account_id=str(audit.account_id),
        status=audit.status.value,
        score=audit.score,
        grade=audit.grade,
        summary=audit.summary,
        category_scores=category_scores,
        check_results=check_results,
        started_at=audit.started_at,
        completed_at=audit.completed_at,
        created_at=audit.created_at,
    )


@router.get("", response_model=AuditListResponse)
async def list_audits(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all audits for the current user."""
    result = await db.execute(
        select(Audit)
        .where(Audit.user_id == user.id)
        .order_by(Audit.created_at.desc())
    )
    audits = result.scalars().all()

    return AuditListResponse(
        audits=[
            AuditListItem(
                audit_id=str(a.id),
                account_id=str(a.account_id),
                status=a.status.value,
                score=a.score,
                grade=a.grade,
                created_at=a.created_at,
            )
            for a in audits
        ]
    )
