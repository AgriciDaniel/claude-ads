"""Google Ads account listing endpoint."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.connectors.google_ads import list_accessible_accounts
from app.models.database import User
from app.models.schemas import AccountListResponse, GoogleAdsAccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=AccountListResponse)
async def list_accounts(
    user: User = Depends(get_current_user),
):
    """List all Google Ads accounts accessible to the authenticated user."""
    if not user.google_refresh_token_encrypted:
        raise HTTPException(
            status_code=400,
            detail="No Google refresh token stored. Please re-authenticate.",
        )

    try:
        loop = asyncio.get_event_loop()
        accounts = await loop.run_in_executor(
            None, list_accessible_accounts, user.google_refresh_token_encrypted,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return AccountListResponse(
        accounts=[
            GoogleAdsAccountOut(
                customer_id=a["customer_id"],
                account_name=a.get("account_name"),
            )
            for a in accounts
        ]
    )
