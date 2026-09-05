from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base
from app.models.ai_decision import AIDecision

if TYPE_CHECKING:
    from app.models.action_execution import ActionExecution
    from app.models.approval_request import ApprovalRequest
    from app.models.audit_log import AuditLog
    from app.models.merchant import Merchant
    from app.models.payment import Payment
    from app.models.recovery_outcome import RecoveryOutcome


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_recovery_cases_payment_id"),
        Index("ix_recovery_cases_merchant_id", "merchant_id"),
        Index("ix_recovery_cases_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merchants.id"),
        nullable=False,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id"),
        nullable=False,
    )
    revenue_at_risk: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    recoverability_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    eligibility: Mapped[str] = mapped_column(String(16), nullable=False)
    suggested_action: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    recovered_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    latest_outcome_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    explanation_factors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    merchant: Mapped[Merchant] = relationship(back_populates="recovery_cases")
    payment: Mapped[Payment] = relationship(back_populates="recovery_case")
    ai_decisions: Mapped[list[AIDecision]] = relationship(
        back_populates="recovery_case",
        cascade="all, delete-orphan",
    )
    action_executions: Mapped[list["ActionExecution"]] = relationship(
        back_populates="recovery_case",
        cascade="all, delete-orphan",
    )
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(
        back_populates="recovery_case",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="recovery_case",
        cascade="all, delete-orphan",
    )
    outcomes: Mapped[list["RecoveryOutcome"]] = relationship(
        back_populates="recovery_case",
        cascade="all, delete-orphan",
    )
