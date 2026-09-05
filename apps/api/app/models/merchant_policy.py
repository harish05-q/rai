from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.merchant import Merchant


class MerchantPolicy(Base):
    __tablename__ = "merchant_policies"
    __table_args__ = (UniqueConstraint("merchant_id", name="uq_merchant_policies_merchant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merchants.id"),
        nullable=False,
    )
    autonomous_execution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_autonomous_action_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    high_value_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_recovery_attempts: Mapped[int] = mapped_column(nullable=False, default=3)
    payment_link_creation_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notifications_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    subscription_recovery_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_approval_for_high_value: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_approval_for_uncertain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
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

    merchant: Mapped[Merchant] = relationship(back_populates="policy")
