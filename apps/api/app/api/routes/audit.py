from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogResponse, PaginatedAudit

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=PaginatedAudit)
def list_audit(
    case_id: UUID | None = None,
    action_execution_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedAudit:
    filters = []
    if case_id is not None:
        filters.append(AuditLog.recovery_case_id == case_id)
    if action_execution_id is not None:
        filters.append(AuditLog.action_execution_id == action_execution_id)
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
    items = db.scalars(
        select(AuditLog).where(*filters).order_by(AuditLog.created_at.asc()).offset(offset).limit(limit)
    ).all()
    return PaginatedAudit(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=int(total),
        limit=limit,
        offset=offset,
    )
