from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MerchantPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    autonomous_execution: bool
    max_autonomous_action_amount: Decimal
    high_value_threshold: Decimal
    max_recovery_attempts: int
    payment_link_creation_allowed: bool
    notifications_allowed: bool
    subscription_recovery_allowed: bool
    require_approval_for_high_value: bool
    require_approval_for_uncertain: bool
    policy_version: str
    updated_at: datetime


class MerchantPolicyUpdate(BaseModel):
    autonomous_execution: bool | None = None
    max_autonomous_action_amount: Decimal | None = Field(default=None, ge=0)
    high_value_threshold: Decimal | None = Field(default=None, ge=0)
    max_recovery_attempts: int | None = Field(default=None, ge=0, le=20)
    payment_link_creation_allowed: bool | None = None
    notifications_allowed: bool | None = None
    subscription_recovery_allowed: bool | None = None
    require_approval_for_high_value: bool | None = None
    require_approval_for_uncertain: bool | None = None


class ExecutionPreview(BaseModel):
    case_id: UUID
    requested_action: str
    policy_decision: str
    reason: str
    required_approval: bool
    workflow: str
    policy_version: str
    limits_checked: list[str]
    can_execute: bool
    can_request_approval: bool
    blocked: bool
    recommendation_only: bool
    ai_decision_id: UUID | None = None
