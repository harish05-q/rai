from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.recovery_case import RecoveryCase


class AuditLog(Base):
    """Append-only execution audit record. Rows are not updated after insert."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_recovery_case_id", "recovery_case_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_action_execution_id", "action_execution_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    recovery_case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_cases.id"),
        nullable=True,
    )
    ai_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ai_decisions.id"),
        nullable=True,
    )
    action_execution_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    policy_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    requested_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    executed_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(1024), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    recovery_case: Mapped[RecoveryCase | None] = relationship(back_populates="audit_logs")
