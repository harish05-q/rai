from datetime import datetime, timezone
from decimal import Decimal

from app.agents.schemas import (
    CustomerAgentContext,
    DeterministicSignals,
    FailureAgentContext,
    PaymentAgentContext,
    RecoveryAgentContext,
    SubscriptionAgentContext,
)
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase


def build_recovery_context(case: RecoveryCase) -> RecoveryAgentContext:
    payment = case.payment
    if payment is None:
        raise ValueError("Recovery case is missing payment context")

    customer = payment.customer
    latest_failure = _latest_failure(payment)
    subscription = _latest_subscription(customer)

    failure_context = None
    if latest_failure is not None:
        failure_context = FailureAgentContext(
            failure_code=latest_failure.failure_code,
            failure_category=latest_failure.failure_category,
            failure_message=_truncate(latest_failure.failure_message, 240),
            occurred_at=_aware(latest_failure.occurred_at),
        )

    customer_context = None
    if customer is not None:
        customer_context = CustomerAgentContext(
            successful_payments=customer.successful_payments,
            failed_payments=customer.failed_payments,
            total_payments=customer.total_payments,
            total_amount_paid=customer.total_amount_paid,
        )

    subscription_context = None
    if subscription is not None:
        subscription_context = SubscriptionAgentContext(
            status=subscription.status,
            plan_name=subscription.plan_name,
            amount=subscription.amount,
            next_billing_at=_aware(subscription.next_billing_at) if subscription.next_billing_at else None,
        )

    return RecoveryAgentContext(
        case_id=case.id,
        payment=PaymentAgentContext(
            amount=payment.amount,
            currency=payment.currency,
            payment_method=payment.payment_method,
            status=payment.status,
            attempt_number=payment.attempt_number,
            checkout_started=payment.checkout_started,
            checkout_completed=payment.checkout_completed,
            external_payment_id=payment.external_payment_id,
        ),
        failure=failure_context,
        customer=customer_context,
        subscription=subscription_context,
        deterministic=DeterministicSignals(
            recoverability_score=Decimal(str(case.recoverability_score)),
            priority=case.priority,
            eligibility=case.eligibility,
            suggested_action=case.suggested_action,
            explanation_factors=list(case.explanation_factors or []),
            case_status=case.status,
        ),
    )


def _latest_failure(payment: Payment):
    if not payment.failures:
        return None
    return max(payment.failures, key=lambda item: item.occurred_at)


def _latest_subscription(customer):
    if customer is None or not customer.subscriptions:
        return None
    return max(customer.subscriptions, key=lambda item: item.created_at)


def _truncate(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
