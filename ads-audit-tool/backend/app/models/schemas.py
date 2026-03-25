"""Pydantic schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class OAuthLoginResponse(BaseModel):
    authorization_url: str


class OAuthCallbackResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class GoogleAdsAccountOut(BaseModel):
    customer_id: str
    account_name: str | None = None

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    accounts: list[GoogleAdsAccountOut]


# ---------------------------------------------------------------------------
# Audits
# ---------------------------------------------------------------------------

class AuditCreateRequest(BaseModel):
    account_id: str  # Google Ads customer ID (no dashes)


class AuditCreateResponse(BaseModel):
    audit_id: str
    status: str


class CheckResultOut(BaseModel):
    check_id: str
    check_name: str
    category: str
    severity: str
    status: str
    score: int
    detail: str | None = None
    fix: str | None = None
    fix_time_minutes: int | None = None
    is_quick_win: bool = False

    model_config = {"from_attributes": True}


class CategoryScore(BaseModel):
    category: str
    score: float
    weight: float
    check_count: int
    pass_count: int
    warn_count: int
    fail_count: int


class AuditDetailResponse(BaseModel):
    audit_id: str
    account_id: str
    status: str
    score: float | None = None
    grade: str | None = None
    summary: str | None = None
    category_scores: list[CategoryScore] | None = None
    check_results: list[CheckResultOut] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class AuditListItem(BaseModel):
    audit_id: str
    account_id: str
    status: str
    score: float | None = None
    grade: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditListResponse(BaseModel):
    audits: list[AuditListItem]
