from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor: str
    source: str
    recovery_case_id: UUID | None
    ai_decision_id: UUID | None
    action_execution_id: UUID | None
    approval_id: UUID | None
    policy_decision: str | None
    requested_action: str | None
    executed_action: str | None
    provider: str | None
    provider_reference: str | None
    status: str
    reason: str
    details: dict[str, Any]
    created_at: datetime


class PaginatedAudit(BaseModel):
    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int
