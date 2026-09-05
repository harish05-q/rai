from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.action_execution import ActionExecution
    from app.models.recovery_case import RecoveryCase


class RecoveryOutcome(Base):
    __tablename__ = "recovery_outcomes"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_recovery_outcomes_fingerprint"),
        Index("ix_recovery_outcomes_recovery_case_id", "recovery_case_id"),
        Index("ix_recovery_outcomes_action_execution_id", "action_execution_id"),
        Index("ix_recovery_outcomes_outcome_status", "outcome_status"),
        Index("ix_recovery_outcomes_observed_at", "observed_at"),
        Index("ix_recovery_outcomes_provider_reference", "provider", "provider_reference"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recovery_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_cases.id"),
        nullable=False,
    )
    action_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("action_executions.id"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    workflow: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome_status: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_attempted: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_recovered: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    extra: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)

    recovery_case: Mapped[RecoveryCase] = relationship(back_populates="outcomes")
    action_execution: Mapped[ActionExecution | None] = relationship()
