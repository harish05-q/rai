from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase
from app.recovery.service import RecoveryAnalysisService
from app.schemas.recovery import (
    AnalyzeRequest,
    AnalyzeResponse,
    PaginatedRecoveryCases,
    RecoveryCaseDetail,
    RecoveryCaseListItem,
    RecoverySummary,
)

router = APIRouter(prefix="/api/v1/recovery", tags=["recovery"])


@router.get("/cases", response_model=PaginatedRecoveryCases)
def list_recovery_cases(
    status: str | None = None,
    priority: str | None = None,
    eligibility: str | None = None,
    suggested_action: str | None = None,
    merchant_id: UUID | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedRecoveryCases:
    filters = []
    if merchant_id is not None:
        filters.append(RecoveryCase.merchant_id == merchant_id)
    if status is not None:
        filters.append(RecoveryCase.status == status)
    if priority is not None:
        filters.append(RecoveryCase.priority == priority)
    if eligibility is not None:
        filters.append(RecoveryCase.eligibility == eligibility)
    if suggested_action is not None:
        filters.append(RecoveryCase.suggested_action == suggested_action)

    total = db.scalar(select(func.count()).select_from(RecoveryCase).where(*filters)) or 0
    cases = db.scalars(
        select(RecoveryCase)
        .where(*filters)
        .options(
            selectinload(RecoveryCase.payment).selectinload(Payment.customer),
            selectinload(RecoveryCase.payment).selectinload(Payment.failures),
        )
        .order_by(RecoveryCase.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).unique().all()

    return PaginatedRecoveryCases(
        items=[_to_item(case) for case in cases],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.get("/cases/{case_id}", response_model=RecoveryCaseDetail)
def get_recovery_case(case_id: UUID, db: Session = Depends(get_db)) -> RecoveryCaseDetail:
    case = db.scalar(
        select(RecoveryCase)
        .where(RecoveryCase.id == case_id)
        .options(
            selectinload(RecoveryCase.payment).selectinload(Payment.customer),
            selectinload(RecoveryCase.payment).selectinload(Payment.failures),
        )
    )
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "case_not_found", "message": "Recovery case was not found"},
        )
    return _to_detail(case)


@router.get("/summary", response_model=RecoverySummary)
def recovery_summary(
    merchant_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> RecoverySummary:
    payload = RecoveryAnalysisService(db).summary(merchant_id=merchant_id)
    return RecoverySummary(**payload)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_recovery(
    body: AnalyzeRequest = AnalyzeRequest(),
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    request = body
    result = RecoveryAnalysisService(db).analyze_failed_payments(
        merchant_id=request.merchant_id,
        payment_id=request.payment_id,
        limit=request.limit,
    )
    return AnalyzeResponse(**result, executed_payment_operations=False)


def _to_item(case: RecoveryCase) -> RecoveryCaseListItem:
    payment = case.payment
    latest = max(payment.failures, key=lambda item: item.occurred_at) if payment.failures else None
    factors = case.explanation_factors or []
    return RecoveryCaseListItem(
        id=case.id,
        payment_id=case.payment_id,
        external_payment_id=payment.external_payment_id,
        revenue_at_risk=case.revenue_at_risk,
        currency=payment.currency,
        failure_category=latest.failure_category if latest else None,
        recoverability_score=case.recoverability_score,
        priority=case.priority,
        eligibility=case.eligibility,
        suggested_action=case.suggested_action,
        status=case.status,
        customer_name=payment.customer.name,
        explanation_factors=factors,
        created_at=case.created_at,
    )


def _to_detail(case: RecoveryCase) -> RecoveryCaseDetail:
    item = _to_item(case)
    payment = case.payment
    latest = max(payment.failures, key=lambda failure: failure.occurred_at) if payment.failures else None
    customer = payment.customer
    return RecoveryCaseDetail(
        **item.model_dump(),
        payment_method=payment.payment_method,
        attempt_number=payment.attempt_number,
        checkout_completed=payment.checkout_completed,
        failure_code=latest.failure_code if latest else None,
        failure_message=latest.failure_message if latest else None,
        customer_successful_payments=customer.successful_payments if customer else 0,
        customer_failed_payments=customer.failed_payments if customer else 0,
        customer_total_payments=customer.total_payments if customer else 0,
    )
