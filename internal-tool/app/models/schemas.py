"""SQLAlchemy models for accounts, audits, and check results."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Enum, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.database import Base


class AuditStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CheckStatus(str, enum.Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    NA = "na"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GoogleAdsAccount(Base):
    __tablename__ = "google_ads_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(String(20), unique=True, nullable=False, index=True)
    account_name = Column(String(255))
    refresh_token = Column(Text, nullable=False)  # Encrypted in production
    industry = Column(String(50))
    monthly_budget = Column(Float)
    primary_goal = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    audits = relationship("Audit", back_populates="account")


class Audit(Base):
    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("google_ads_accounts.id"), nullable=False)
    status = Column(Enum(AuditStatus), default=AuditStatus.PENDING)
    score = Column(Float)
    grade = Column(String(1))
    summary = Column(Text)
    raw_data = Column(JSON)  # Cached API responses for this audit run
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("GoogleAdsAccount", back_populates="audits")
    check_results = relationship("CheckResult", back_populates="audit")


class CheckResult(Base):
    __tablename__ = "check_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False)
    check_id = Column(String(10), nullable=False)  # e.g. "G05", "G-CT1"
    check_name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    status = Column(Enum(CheckStatus), nullable=False)
    detail = Column(Text)
    fix = Column(Text)
    fix_time_minutes = Column(Integer)
    is_quick_win = Column(Integer, default=0)  # 1 if quick win

    audit = relationship("Audit", back_populates="check_results")
