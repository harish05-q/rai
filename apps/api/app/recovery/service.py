from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.customer import Customer
from app.models.enums import PaymentStatus, RecoveryCaseStatus, RecoveryEligibility
from app.models.payment import Payment
from app.models.payment_failure import PaymentFailure
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.recovery.eligibility import EligibilityInput, evaluate_eligibility
from app.recovery.scoring import ScoringInput, score_recoverability


class RecoveryAnalysisService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def analyze_failed_payments(
        self,
        merchant_id=None,
        payment_id=None,
        limit: int | None = None,
    ) -> dict[str, int]:
        """Create or update recovery cases. Never executes a payment operation."""

        query: Select[tuple[Payment]] = (
            select(Payment)
            .options(
                selectinload(Payment.customer),
                selectinload(Payment.failures),
                selectinload(Payment.recovery_case),
                selectinload(Payment.customer).selectinload(Customer.subscriptions),
            )
            .order_by(Payment.created_at.asc())
        )
        if merchant_id is not None:
            query = query.where(Payment.merchant_id == merchant_id)
        if payment_id is not None:
            query = query.where(Payment.id == payment_id)
        else:
            query = query.where(Payment.status.in_([PaymentStatus.FAILED, PaymentStatus.ABANDONED]))
        if limit is not None:
            query = query.limit(limit)

        payments = self.session.scalars(query).unique().all()
        created = 0
        updated = 0
        skipped = 0

        for payment in payments:
            result = self._analyze_payment(payment)
            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1

        self.session.commit()
        return {
            "payments_analyzed": len(payments),
            "cases_created": created,
            "cases_updated": updated,
            "cases_skipped": skipped,
        }

    def _analyze_payment(self, payment: Payment) -> str:
        existing = payment.recovery_case
        latest_failure = _latest_failure(payment)
        customer = payment.customer
        subscription_status = _active_subscription_status(customer)

        if payment.status == PaymentStatus.SUCCEEDED:
            if existing and existing.status == RecoveryCaseStatus.OPEN:
                existing.status = RecoveryCaseStatus.RECOVERED
                existing.eligibility = RecoveryEligibility.INELIGIBLE
                existing.resolved_at = datetime.now(timezone.utc)
                existing.updated_at = datetime.now(timezone.utc)
                return "updated"
            return "skipped"

        scoring = score_recoverability(
            ScoringInput(
                failure_category=_category(latest_failure),
                successful_payments=customer.successful_payments if customer else 0,
                failed_payments=customer.failed_payments if customer else 0,
                total_payments=customer.total_payments if customer else 0,
                attempt_number=payment.attempt_number,
                amount=payment.amount,
                checkout_completed=payment.checkout_completed,
                subscription_status=subscription_status,
            )
        )
        eligibility = evaluate_eligibility(
            EligibilityInput(
                payment_status=PaymentStatus(payment.status),
                failure_category=_category(latest_failure),
                failure_code=latest_failure.failure_code if latest_failure else None,
                attempt_number=payment.attempt_number,
                amount=payment.amount,
                customer_present=customer is not None,
                existing_case_status=RecoveryCaseStatus(existing.status) if existing else None,
            )
        )

        if existing and existing.status in {RecoveryCaseStatus.RECOVERED, RecoveryCaseStatus.RESOLVED}:
            return "skipped"

        case_status = RecoveryCaseStatus.OPEN
        resolved_at = None
        if eligibility.eligibility == RecoveryEligibility.INELIGIBLE:
            case_status = RecoveryCaseStatus.BLOCKED

        if existing:
            existing.revenue_at_risk = payment.amount
            existing.recoverability_score = Decimal(str(scoring.recoverability_score))
            existing.priority = scoring.priority
            existing.eligibility = eligibility.eligibility
            existing.suggested_action = eligibility.suggested_action
            existing.status = case_status
            existing.explanation_factors = scoring.explanation_factors
            existing.resolved_at = resolved_at
            existing.updated_at = datetime.now(timezone.utc)
            return "updated"

        case = RecoveryCase(
            merchant_id=payment.merchant_id,
            payment_id=payment.id,
            revenue_at_risk=payment.amount,
            recoverability_score=Decimal(str(scoring.recoverability_score)),
            priority=scoring.priority,
            eligibility=eligibility.eligibility,
            suggested_action=eligibility.suggested_action,
            status=case_status,
            explanation_factors=scoring.explanation_factors,
            resolved_at=resolved_at,
        )
        self.session.add(case)
        payment.recovery_case = case
        return "created"

    def summary(self, merchant_id=None) -> dict:
        payment_filter = []
        case_filter = []
        if merchant_id is not None:
            payment_filter.append(Payment.merchant_id == merchant_id)
            case_filter.append(RecoveryCase.merchant_id == merchant_id)

        total_payments = self.session.scalar(select(func.count(Payment.id)).where(*payment_filter)) or 0
        total_failed = self.session.scalar(
            select(func.count(Payment.id)).where(
                Payment.status == PaymentStatus.FAILED,
                *payment_filter,
            )
        ) or 0
        recoverable = self.session.scalar(
            select(func.count(RecoveryCase.id)).where(
                RecoveryCase.eligibility == RecoveryEligibility.ELIGIBLE,
                *case_filter,
            )
        ) or 0
        revenue_at_risk = self.session.scalar(
            select(func.coalesce(func.sum(RecoveryCase.revenue_at_risk), 0)).where(
                RecoveryCase.status == RecoveryCaseStatus.OPEN,
                *case_filter,
            )
        ) or Decimal("0.00")
        open_cases = self.session.scalar(
            select(func.count(RecoveryCase.id)).where(
                RecoveryCase.status == RecoveryCaseStatus.OPEN,
                *case_filter,
            )
        ) or 0
        recovered_cases = self.session.scalar(
            select(func.count(RecoveryCase.id)).where(
                RecoveryCase.status == RecoveryCaseStatus.RECOVERED,
                *case_filter,
            )
        ) or 0
        recovered_revenue = self.session.scalar(
            select(func.coalesce(func.sum(RecoveryCase.revenue_at_risk), 0)).where(
                RecoveryCase.status == RecoveryCaseStatus.RECOVERED,
                *case_filter,
            )
        ) or Decimal("0.00")

        return {
            "total_payments": int(total_payments),
            "total_failed_payments": int(total_failed),
            "recoverable_payments": int(recoverable),
            "revenue_at_risk": revenue_at_risk,
            "open_recovery_cases": int(open_cases),
            "recovered_cases": int(recovered_cases),
            "recovered_revenue": recovered_revenue,
        }


def _latest_failure(payment: Payment) -> PaymentFailure | None:
    if not payment.failures:
        return None
    return max(payment.failures, key=lambda item: item.occurred_at)


def _category(failure: PaymentFailure | None):
    if failure is None:
        return None
    from app.models.enums import FailureCategory

    return FailureCategory(failure.failure_category)


def _active_subscription_status(customer: Customer | None):
    if customer is None or not customer.subscriptions:
        return None
    from app.models.enums import SubscriptionStatus

    ordered = sorted(customer.subscriptions, key=lambda item: item.created_at, reverse=True)
    return SubscriptionStatus(ordered[0].status)
