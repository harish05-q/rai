from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.recovery_case import RecoveryCase


class AIDecision(Base):
    """Immutable R.AI recommendation record. New analyses append; they never overwrite."""

    __tablename__ = "ai_decisions"
    __table_args__ = (
        Index("ix_ai_decisions_recovery_case_id", "recovery_case_id"),
        Index("ix_ai_decisions_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recovery_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_cases.id"),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    ai_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    diagnosis: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    rationale: Mapped[str] = mapped_column(String(1024), nullable=False)
    alternative_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timing: Mapped[str] = mapped_column(String(32), nullable=False)
    concerns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    baseline_action: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    comparison_status: Mapped[str] = mapped_column(String(16), nullable=False)
    comparison_reason: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    recovery_case: Mapped[RecoveryCase] = relationship(back_populates="ai_decisions")
