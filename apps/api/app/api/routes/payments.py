from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.models.payment import Payment
from app.models.payment_failure import PaymentFailure
from app.schemas.recovery import PaginatedPayments, PaymentListItem

router = APIRouter(prefix="/api/v1", tags=["payments"])


@router.get("/payments", response_model=PaginatedPayments)
def list_payments(
    status: str | None = None,
    payment_method: str | None = None,
    failure_category: str | None = None,
    merchant_id: UUID | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedPayments:
    filters = []
    if merchant_id is not None:
        filters.append(Payment.merchant_id == merchant_id)
    if status is not None:
        filters.append(Payment.status == status)
    if payment_method is not None:
        filters.append(Payment.payment_method == payment_method)

    base = select(Payment).where(*filters)
    count_stmt = select(func.count()).select_from(Payment).where(*filters)
    if failure_category is not None:
        base = base.join(PaymentFailure).where(PaymentFailure.failure_category == failure_category)
        count_stmt = (
            select(func.count(func.distinct(Payment.id)))
            .select_from(Payment)
            .join(PaymentFailure)
            .where(*filters, PaymentFailure.failure_category == failure_category)
        )

    total = db.scalar(count_stmt) or 0
    payments = db.scalars(
        base.options(
            selectinload(Payment.customer),
            selectinload(Payment.failures),
            selectinload(Payment.recovery_case),
        )
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).unique().all()

    return PaginatedPayments(
        items=[_to_item(payment) for payment in payments],
        total=int(total),
        limit=limit,
        offset=offset,
    )


def _to_item(payment: Payment) -> PaymentListItem:
    latest = max(payment.failures, key=lambda item: item.occurred_at) if payment.failures else None
    return PaymentListItem(
        id=payment.id,
        external_payment_id=payment.external_payment_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        payment_method=payment.payment_method,
        failure_category=latest.failure_category if latest else None,
        customer_name=payment.customer.name,
        customer_email=payment.customer.email,
        created_at=payment.created_at,
        recovery_status=payment.recovery_case.status if payment.recovery_case else None,
    )
