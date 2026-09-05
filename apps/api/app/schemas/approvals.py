from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recovery_case_id: UUID
    action_execution_id: UUID
    reason: str
    amount: Decimal
    requested_action: str
    status: str
    requested_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    resolution_note: str | None
    expires_at: datetime | None
    customer_name: str | None = None
    recommended_action: str | None = None
    external_payment_id: str | None = None


class PaginatedApprovals(BaseModel):
    items: list[ApprovalResponse]
    total: int
    limit: int
    offset: int


class ApprovalResolutionRequest(BaseModel):
    resolved_by: str = "merchant-operator"
    note: str | None = Field(default=None, max_length=1024)
