from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActionExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recovery_case_id: UUID
    ai_decision_id: UUID | None
    action: str
    workflow: str
    provider: str
    provider_reference: str | None
    status: str
    policy_decision: str
    approval_id: UUID | None
    result: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None


class PaginatedActions(BaseModel):
    items: list[ActionExecutionResponse]
    total: int
    limit: int
    offset: int


class ExecutionSummary(BaseModel):
    actions_executed: int
    actions_blocked: int
    actions_failed: int
    approvals_pending: int
    recovered_workflow_amount: str
    provider_success_rate: float | None
    provider: str


class ExecuteResponse(BaseModel):
    case_id: UUID
    requested_action: str
    policy_decision: str
    execution_status: str
    execution_id: UUID | None = None
    provider: str | None = None
    provider_reference: str | None = None
    payment_link: str | None = None
    recommendation_only: bool
    audit_id: UUID | None = None
    approval_id: UUID | None = None
    reason: str | None = None
    workflow: str | None = None
    mock: bool | None = None
