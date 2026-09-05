from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.actions.executor import ActionError, ActionExecutor
from app.api.deps import get_db
from app.models.approval_request import ApprovalRequest
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase
from app.schemas.actions import ExecuteResponse
from app.schemas.approvals import ApprovalResolutionRequest, ApprovalResponse, PaginatedApprovals

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


def _executor(db: Session = Depends(get_db)) -> ActionExecutor:
    return ActionExecutor(db)


@router.get("", response_model=PaginatedApprovals)
def list_approvals(
    status: str | None = None,
    case_id: UUID | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedApprovals:
    filters = []
    if status is not None:
        filters.append(ApprovalRequest.status == status)
    if case_id is not None:
        filters.append(ApprovalRequest.recovery_case_id == case_id)
    total = db.scalar(select(func.count()).select_from(ApprovalRequest).where(*filters)) or 0
    rows = db.scalars(
        select(ApprovalRequest)
        .where(*filters)
        .options(
            selectinload(ApprovalRequest.recovery_case)
            .selectinload(RecoveryCase.payment)
            .selectinload(Payment.customer)
        )
        .order_by(ApprovalRequest.requested_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    items = [_to_response(row) for row in rows]
    return PaginatedApprovals(items=items, total=int(total), limit=limit, offset=offset)


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(approval_id: UUID, db: Session = Depends(get_db)) -> ApprovalResponse:
    row = db.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.id == approval_id)
        .options(
            selectinload(ApprovalRequest.recovery_case)
            .selectinload(RecoveryCase.payment)
            .selectinload(Payment.customer)
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "approval_not_found", "message": "Approval request was not found"})
    return _to_response(row)


@router.post("/{approval_id}/approve", response_model=ExecuteResponse)
def approve_request(
    approval_id: UUID,
    body: ApprovalResolutionRequest | None = None,
    executor: ActionExecutor = Depends(_executor),
) -> ExecuteResponse:
    request = body or ApprovalResolutionRequest()
    try:
        return ExecuteResponse.model_validate(
            executor.approve(approval_id, resolved_by=request.resolved_by, note=request.note)
        )
    except ActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/{approval_id}/reject", response_model=ExecuteResponse)
def reject_request(
    approval_id: UUID,
    body: ApprovalResolutionRequest | None = None,
    executor: ActionExecutor = Depends(_executor),
) -> ExecuteResponse:
    request = body or ApprovalResolutionRequest()
    try:
        return ExecuteResponse.model_validate(
            executor.reject(approval_id, resolved_by=request.resolved_by, note=request.note)
        )
    except ActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


def _to_response(row: ApprovalRequest) -> ApprovalResponse:
    payment = row.recovery_case.payment if row.recovery_case else None
    customer_name = payment.customer.name if payment and payment.customer else None
    return ApprovalResponse(
        id=row.id,
        recovery_case_id=row.recovery_case_id,
        action_execution_id=row.action_execution_id,
        reason=row.reason,
        amount=row.amount,
        requested_action=row.requested_action,
        status=row.status,
        requested_at=row.requested_at,
        resolved_at=row.resolved_at,
        resolved_by=row.resolved_by,
        resolution_note=row.resolution_note,
        expires_at=row.expires_at,
        customer_name=customer_name,
        recommended_action=row.requested_action,
        external_payment_id=payment.external_payment_id if payment else None,
    )
