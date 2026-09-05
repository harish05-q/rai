from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.actions.executor import ActionError, ActionExecutor
from app.api.deps import get_db
from app.models.action_execution import ActionExecution
from app.models.approval_request import ApprovalRequest
from app.models.enums import ApprovalStatus, ExecutionStatus
from app.models.recovery_case import RecoveryCase
from app.payment_providers.factory import get_payment_provider
from app.schemas.actions import ActionExecutionResponse, ExecuteResponse, ExecutionSummary, PaginatedActions

router = APIRouter(tags=["actions"])


def _executor(db: Session = Depends(get_db)) -> ActionExecutor:
    return ActionExecutor(db)


@router.post("/api/v1/recovery/cases/{case_id}/execute", response_model=ExecuteResponse)
def execute_recovery(case_id: UUID, executor: ActionExecutor = Depends(_executor)) -> ExecuteResponse:
    try:
        payload = executor.execute(case_id)
        return ExecuteResponse.model_validate(payload)
    except ActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/api/v1/actions/summary", response_model=ExecutionSummary)
def action_summary(db: Session = Depends(get_db)) -> ExecutionSummary:
    executed = db.scalar(
        select(func.count(ActionExecution.id)).where(ActionExecution.status == ExecutionStatus.SUCCEEDED.value)
    ) or 0
    blocked = db.scalar(
        select(func.count(ActionExecution.id)).where(ActionExecution.status == ExecutionStatus.BLOCKED.value)
    ) or 0
    failed = db.scalar(
        select(func.count(ActionExecution.id)).where(ActionExecution.status == ExecutionStatus.FAILED.value)
    ) or 0
    pending = db.scalar(
        select(func.count(ApprovalRequest.id)).where(ApprovalRequest.status == ApprovalStatus.PENDING.value)
    ) or 0
    succeeded = db.scalars(
        select(ActionExecution).where(ActionExecution.status == ExecutionStatus.SUCCEEDED.value)
    ).all()
    amount = 0.0
    provider_ok = 0
    provider_total = 0
    for item in succeeded:
        result = item.result or {}
        if item.workflow in {"payment_link", "subscription_provider_managed"}:
            case = db.get(RecoveryCase, item.recovery_case_id)
            if case is not None:
                amount += float(case.revenue_at_risk)
            provider_total += 1
            if result.get("status") in {"created", "deferred", "notified", "skipped"} or item.provider_reference:
                provider_ok += 1
    rate = (provider_ok / provider_total) if provider_total else None
    return ExecutionSummary(
        actions_executed=int(executed),
        actions_blocked=int(blocked),
        actions_failed=int(failed),
        approvals_pending=int(pending),
        recovered_workflow_amount=f"{amount:.2f}",
        provider_success_rate=rate,
        provider=get_payment_provider().name,
    )


@router.get("/api/v1/actions", response_model=PaginatedActions)
def list_actions(
    case_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedActions:
    filters = []
    if case_id is not None:
        filters.append(ActionExecution.recovery_case_id == case_id)
    if status is not None:
        filters.append(ActionExecution.status == status)
    total = db.scalar(select(func.count()).select_from(ActionExecution).where(*filters)) or 0
    items = db.scalars(
        select(ActionExecution)
        .where(*filters)
        .order_by(ActionExecution.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return PaginatedActions(
        items=[ActionExecutionResponse.model_validate(item) for item in items],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.get("/api/v1/actions/{action_execution_id}", response_model=ActionExecutionResponse)
def get_action(action_execution_id: UUID, db: Session = Depends(get_db)) -> ActionExecutionResponse:
    execution = db.get(ActionExecution, action_execution_id)
    if execution is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "execution_not_found", "message": "Action execution was not found"},
        )
    return ActionExecutionResponse.model_validate(execution)
