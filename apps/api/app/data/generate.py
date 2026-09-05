"""Deterministic synthetic dataset for R.AI recovery intelligence.

All records are fake. Emails use the .invalid TLD. A fixed RNG seed makes
regeneration stable across runs.
"""

from __future__ import annotations

import argparse
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from random import Random

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.action_execution import ActionExecution
from app.models.ai_decision import AIDecision
from app.models.approval_request import ApprovalRequest
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.enums import (
    FailureCategory,
    PaymentMethod,
    PaymentStatus,
    SubscriptionStatus,
)
from app.models.merchant import Merchant
from app.models.payment import Payment
from app.models.payment_failure import PaymentFailure
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.recovery.service import RecoveryAnalysisService
from app.policies.service import apply_demo_guardrails, get_or_create_merchant_policy

DEMO_MERCHANT_EMAIL = "demo@rai.example"
DEMO_MERCHANT_NAME = "R.AI Demo Merchant"
DEFAULT_SEED = 42
DEFAULT_CUSTOMERS = 1000
DEFAULT_PAYMENTS = 10000

FIRST_NAMES = [
    "Aarav", "Diya", "Ishaan", "Meera", "Kabir", "Ananya", "Rohan", "Sara",
    "Vikram", "Nisha", "Arjun", "Priya", "Dev", "Leela", "Kiran", "Zara",
]
LAST_NAMES = [
    "Sharma", "Patel", "Reddy", "Iyer", "Khan", "Nair", "Gupta", "Das",
    "Mehta", "Joshi", "Bose", "Kapoor",
]
PLANS = ["Starter", "Growth", "Pro", "Scale"]
METHODS = list(PaymentMethod)

FAILURE_META: dict[FailureCategory, tuple[str, str]] = {
    FailureCategory.TEMPORARY_TIMEOUT: ("bank_timeout", "Issuing bank timed out"),
    FailureCategory.INSUFFICIENT_FUNDS: ("insufficient_funds", "Insufficient funds"),
    FailureCategory.EXPIRED_CARD: ("card_expired", "Card expired"),
    FailureCategory.AUTHENTICATION_FAILURE: ("authentication_failed", "Customer authentication failed"),
    FailureCategory.DECLINED: ("card_declined", "Payment declined by issuer"),
    FailureCategory.ABANDONED_CHECKOUT: ("checkout_abandoned", "Customer left checkout"),
    FailureCategory.OTHER: ("unknown_error", "Unclassified processor error"),
    FailureCategory.NON_RECOVERABLE: ("account_closed", "Account closed at issuer"),
}


@dataclass
class CustomerPersona:
    kind: str
    success_rate: float


SCENARIO_PERSONAS: list[tuple[str, str]] = [
    ("timeout_reliable", "Temporary bank timeout with strong history"),
    ("nsf_repeat", "Insufficient funds with repeated failures"),
    ("expired_card", "Expired card"),
    ("auth_failure", "Authentication failure"),
    ("declined", "Payment declined"),
    ("abandoned", "Abandoned checkout"),
    ("high_value", "High-value failed payment"),
    ("subscription_fail", "Subscription payment failure"),
    ("historically_reliable", "Historically reliable payment behavior"),
    ("historically_poor", "Historically poor payment behavior"),
]


def generate_synthetic_dataset(
    session: Session,
    *,
    seed: int = DEFAULT_SEED,
    customer_count: int = DEFAULT_CUSTOMERS,
    payment_count: int = DEFAULT_PAYMENTS,
    reset: bool = True,
    analyze: bool = False,
) -> dict[str, int]:
    rng = Random(seed)
    merchant = _ensure_merchant(session)
    policy = get_or_create_merchant_policy(session, merchant.id)
    apply_demo_guardrails(policy)
    if reset:
        _reset_merchant_data(session, merchant.id)

    now = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
    customers = _build_customers(rng, merchant.id, customer_count, now)
    session.add_all(customers)
    session.flush()

    subscriptions = _build_subscriptions(rng, merchant.id, customers, now)
    session.add_all(subscriptions)
    session.flush()

    payments, failures = _build_payments(
        rng,
        merchant.id,
        customers,
        subscriptions,
        payment_count,
        now,
    )
    session.add_all(payments)
    session.flush()
    session.add_all(failures)
    _refresh_customer_aggregates(customers, payments)
    session.flush()

    analyzed = {"payments_analyzed": 0, "cases_created": 0, "cases_updated": 0, "cases_skipped": 0}
    if analyze:
        analyzed = RecoveryAnalysisService(session).analyze_failed_payments(merchant_id=merchant.id)
        _mark_synthetic_recoveries(rng, session, merchant.id)

    session.commit()
    return {
        "merchants": 1,
        "customers": len(customers),
        "payments": len(payments),
        "payment_failures": len(failures),
        "subscriptions": len(subscriptions),
        **analyzed,
    }


def _ensure_merchant(session: Session) -> Merchant:
    merchant = session.scalar(select(Merchant).where(Merchant.email == DEMO_MERCHANT_EMAIL))
    if merchant is None:
        merchant = Merchant(name=DEMO_MERCHANT_NAME, email=DEMO_MERCHANT_EMAIL)
        session.add(merchant)
        session.flush()
    return merchant


def _reset_merchant_data(session: Session, merchant_id: uuid.UUID) -> None:
    case_ids = select(RecoveryCase.id).where(RecoveryCase.merchant_id == merchant_id)
    session.execute(delete(AuditLog).where(AuditLog.recovery_case_id.in_(case_ids)))
    session.execute(delete(ApprovalRequest).where(ApprovalRequest.recovery_case_id.in_(case_ids)))
    session.execute(delete(ActionExecution).where(ActionExecution.recovery_case_id.in_(case_ids)))
    session.execute(delete(AIDecision).where(AIDecision.recovery_case_id.in_(case_ids)))
    payment_ids = select(Payment.id).where(Payment.merchant_id == merchant_id)
    session.execute(delete(RecoveryCase).where(RecoveryCase.merchant_id == merchant_id))
    session.execute(delete(PaymentFailure).where(PaymentFailure.payment_id.in_(payment_ids)))
    session.execute(delete(Payment).where(Payment.merchant_id == merchant_id))
    session.execute(delete(Subscription).where(Subscription.merchant_id == merchant_id))
    session.execute(delete(Customer).where(Customer.merchant_id == merchant_id))
    session.flush()


def _build_customers(rng: Random, merchant_id: uuid.UUID, count: int, now: datetime) -> list[Customer]:
    customers: list[Customer] = []
    for index in range(count):
        if index < len(SCENARIO_PERSONAS):
            kind, label = SCENARIO_PERSONAS[index]
            name = f"Scenario {index + 1} {label[:32]}"
        else:
            kind = rng.choice(["reliable", "mixed", "poor", "new"])
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        created = now - timedelta(days=rng.randint(30, 400))
        customers.append(
            Customer(
                id=uuid.uuid4(),
                merchant_id=merchant_id,
                external_reference=f"cust_{index + 1:04d}",
                name=name,
                email=f"customer.{index + 1:04d}@example.invalid",
                total_payments=0,
                successful_payments=0,
                failed_payments=0,
                total_amount_paid=Decimal("0.00"),
                created_at=created,
                updated_at=created,
            )
        )
        customers[-1]._persona = kind  # type: ignore[attr-defined]
    return customers


def _build_subscriptions(
    rng: Random,
    merchant_id: uuid.UUID,
    customers: list[Customer],
    now: datetime,
) -> list[Subscription]:
    subscriptions: list[Subscription] = []
    for index, customer in enumerate(customers):
        persona = getattr(customer, "_persona")
        should_subscribe = persona in {"subscription_fail", "timeout_reliable", "historically_reliable"}
        if not should_subscribe and rng.random() > 0.28:
            continue
        status = SubscriptionStatus.ACTIVE
        if persona == "subscription_fail":
            status = SubscriptionStatus.PAST_DUE
        elif persona == "historically_poor":
            status = rng.choice([SubscriptionStatus.PAST_DUE, SubscriptionStatus.CANCELLED])
        created = customer.created_at + timedelta(days=7)
        subscriptions.append(
            Subscription(
                merchant_id=merchant_id,
                customer_id=customer.id,
                external_subscription_id=f"sub_{index + 1:04d}",
                plan_name=rng.choice(PLANS),
                amount=Decimal(str(rng.choice([499, 999, 1499, 2999]))),
                currency="INR",
                status=status,
                next_billing_at=now + timedelta(days=rng.randint(1, 28)),
                created_at=created,
                updated_at=created,
            )
        )
        customer._has_subscription = True  # type: ignore[attr-defined]
    return subscriptions


def _build_payments(
    rng: Random,
    merchant_id: uuid.UUID,
    customers: list[Customer],
    subscriptions: list[Subscription],
    payment_count: int,
    now: datetime,
) -> tuple[list[Payment], list[PaymentFailure]]:
    payments: list[Payment] = []
    failures: list[PaymentFailure] = []
    sub_by_customer = {item.customer_id: item for item in subscriptions}

    sequence = 0

    def add_payment(
        customer: Customer,
        *,
        status: PaymentStatus,
        category: FailureCategory | None,
        amount: Decimal,
        attempt: int,
        days_ago: int,
        method: PaymentMethod,
        abandoned: bool = False,
        recovered_later: bool = False,
    ) -> Payment:
        nonlocal sequence
        sequence += 1
        created = now - timedelta(days=days_ago, hours=rng.randint(0, 20))
        checkout_completed = status == PaymentStatus.SUCCEEDED or (
            status == PaymentStatus.FAILED and not abandoned
        )
        payment = Payment(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=customer.id,
            external_payment_id=f"pay_{sequence:06d}",
            amount=amount,
            currency="INR",
            payment_method=method,
            status=PaymentStatus.SUCCEEDED if recovered_later else status,
            attempt_number=attempt,
            checkout_started=True,
            checkout_completed=False if abandoned else checkout_completed,
            created_at=created,
            updated_at=created,
        )
        payments.append(payment)
        if category is not None and status in {PaymentStatus.FAILED, PaymentStatus.ABANDONED}:
            code, message = FAILURE_META[category]
            failures.append(
                PaymentFailure(
                    payment_id=payment.id,
                    failure_code=code,
                    failure_category=category,
                    failure_message=message,
                    occurred_at=created + timedelta(minutes=2),
                )
            )
        return payment

    # Named recovery scenarios for the first 10 customers.
    scenario_builders = [
        lambda c: _scenario_timeout_reliable(add_payment, rng, c),
        lambda c: _scenario_nsf_repeat(add_payment, rng, c),
        lambda c: _scenario_expired_card(add_payment, rng, c),
        lambda c: _scenario_auth(add_payment, rng, c),
        lambda c: _scenario_declined(add_payment, rng, c),
        lambda c: _scenario_abandoned(add_payment, rng, c),
        lambda c: _scenario_high_value(add_payment, rng, c),
        lambda c: _scenario_subscription(add_payment, rng, c, sub_by_customer.get(c.id)),
        lambda c: _scenario_reliable(add_payment, rng, c),
        lambda c: _scenario_poor(add_payment, rng, c),
    ]
    for customer, builder in zip(customers[:10], scenario_builders):
        builder(customer)

    remaining = payment_count - len(payments)
    pool = customers[10:] or customers
    for index in range(max(remaining, 0)):
        customer = pool[index % len(pool)]
        persona = getattr(customer, "_persona")
        _persona_payment(add_payment, rng, customer, persona, index)

    if len(payments) > payment_count:
        keep_ids = {payment.id for payment in payments[:payment_count]}
        payments = payments[:payment_count]
        failures = [item for item in failures if item.payment_id in keep_ids]

    return payments, failures


def _amount(rng: Random, high: bool = False) -> Decimal:
    if high:
        return Decimal(str(rng.choice([75000, 88000, 125000, 150000])))
    return Decimal(str(rng.choice([199, 499, 799, 1299, 2499, 4999, 8999, 15999])))


def _scenario_timeout_reliable(add_payment, rng: Random, customer: Customer) -> None:
    for day in range(8, 0, -1):
        add_payment(
            customer,
            status=PaymentStatus.SUCCEEDED,
            category=None,
            amount=_amount(rng),
            attempt=1,
            days_ago=40 + day * 10,
            method=PaymentMethod.CARD,
        )
    add_payment(
        customer,
        status=PaymentStatus.FAILED,
        category=FailureCategory.TEMPORARY_TIMEOUT,
        amount=_amount(rng),
        attempt=1,
        days_ago=2,
        method=PaymentMethod.CARD,
    )


def _scenario_nsf_repeat(add_payment, rng: Random, customer: Customer) -> None:
    add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=_amount(rng), attempt=1, days_ago=120, method=PaymentMethod.UPI)
    for attempt in range(1, 4):
        add_payment(
            customer,
            status=PaymentStatus.FAILED,
            category=FailureCategory.INSUFFICIENT_FUNDS,
            amount=_amount(rng),
            attempt=attempt,
            days_ago=20 - attempt,
            method=PaymentMethod.CARD,
        )


def _scenario_expired_card(add_payment, rng: Random, customer: Customer) -> None:
    for _ in range(5):
        add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=_amount(rng), attempt=1, days_ago=rng.randint(30, 200), method=PaymentMethod.CARD)
    add_payment(
        customer,
        status=PaymentStatus.FAILED,
        category=FailureCategory.EXPIRED_CARD,
        amount=_amount(rng),
        attempt=1,
        days_ago=3,
        method=PaymentMethod.CARD,
    )


def _scenario_auth(add_payment, rng: Random, customer: Customer) -> None:
    for _ in range(4):
        add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=_amount(rng), attempt=1, days_ago=rng.randint(20, 90), method=PaymentMethod.CARD)
    add_payment(
        customer,
        status=PaymentStatus.FAILED,
        category=FailureCategory.AUTHENTICATION_FAILURE,
        amount=_amount(rng),
        attempt=1,
        days_ago=1,
        method=PaymentMethod.CARD,
    )


def _scenario_declined(add_payment, rng: Random, customer: Customer) -> None:
    add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=_amount(rng), attempt=1, days_ago=80, method=PaymentMethod.NETBANKING)
    add_payment(
        customer,
        status=PaymentStatus.FAILED,
        category=FailureCategory.DECLINED,
        amount=_amount(rng),
        attempt=2,
        days_ago=4,
        method=PaymentMethod.CARD,
    )


def _scenario_abandoned(add_payment, rng: Random, customer: Customer) -> None:
    for _ in range(3):
        add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=_amount(rng), attempt=1, days_ago=rng.randint(15, 70), method=PaymentMethod.UPI)
    add_payment(
        customer,
        status=PaymentStatus.ABANDONED,
        category=FailureCategory.ABANDONED_CHECKOUT,
        amount=_amount(rng),
        attempt=1,
        days_ago=1,
        method=PaymentMethod.CARD,
        abandoned=True,
    )


def _scenario_high_value(add_payment, rng: Random, customer: Customer) -> None:
    for _ in range(6):
        add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=_amount(rng), attempt=1, days_ago=rng.randint(20, 180), method=PaymentMethod.NETBANKING)
    add_payment(
        customer,
        status=PaymentStatus.FAILED,
        category=FailureCategory.TEMPORARY_TIMEOUT,
        amount=_amount(rng, high=True),
        attempt=1,
        days_ago=2,
        method=PaymentMethod.NETBANKING,
    )


def _scenario_subscription(add_payment, rng: Random, customer: Customer, subscription: Subscription | None) -> None:
    amount = subscription.amount if subscription else Decimal("999.00")
    for _ in range(7):
        add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=amount, attempt=1, days_ago=rng.randint(40, 240), method=PaymentMethod.CARD)
    add_payment(
        customer,
        status=PaymentStatus.FAILED,
        category=FailureCategory.INSUFFICIENT_FUNDS,
        amount=amount,
        attempt=1,
        days_ago=1,
        method=PaymentMethod.CARD,
    )


def _scenario_reliable(add_payment, rng: Random, customer: Customer) -> None:
    for _ in range(12):
        add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=_amount(rng), attempt=1, days_ago=rng.randint(10, 300), method=rng.choice(METHODS))
    add_payment(
        customer,
        status=PaymentStatus.FAILED,
        category=FailureCategory.TEMPORARY_TIMEOUT,
        amount=_amount(rng),
        attempt=1,
        days_ago=5,
        method=PaymentMethod.CARD,
        recovered_later=True,
    )


def _scenario_poor(add_payment, rng: Random, customer: Customer) -> None:
    add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=_amount(rng), attempt=1, days_ago=300, method=PaymentMethod.WALLET)
    for attempt in range(1, 6):
        add_payment(
            customer,
            status=PaymentStatus.FAILED,
            category=rng.choice(
                [FailureCategory.DECLINED, FailureCategory.INSUFFICIENT_FUNDS, FailureCategory.NON_RECOVERABLE]
            ),
            amount=_amount(rng),
            attempt=min(attempt, 5),
            days_ago=40 - attempt,
            method=PaymentMethod.CARD,
        )


def _persona_payment(add_payment, rng: Random, customer: Customer, persona: str, index: int) -> None:
    method = rng.choice(METHODS)
    amount = _amount(rng, high=rng.random() < 0.04)
    days_ago = rng.randint(0, 240)
    roll = rng.random()
    if persona == "reliable":
        if roll < 0.88:
            add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=amount, attempt=1, days_ago=days_ago, method=method)
        elif roll < 0.94:
            add_payment(customer, status=PaymentStatus.FAILED, category=FailureCategory.TEMPORARY_TIMEOUT, amount=amount, attempt=1, days_ago=days_ago, method=method)
        else:
            add_payment(customer, status=PaymentStatus.ABANDONED, category=FailureCategory.ABANDONED_CHECKOUT, amount=amount, attempt=1, days_ago=days_ago, method=method, abandoned=True)
    elif persona == "poor":
        if roll < 0.35:
            add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=amount, attempt=1, days_ago=days_ago, method=method)
        elif roll < 0.55:
            add_payment(customer, status=PaymentStatus.FAILED, category=FailureCategory.INSUFFICIENT_FUNDS, amount=amount, attempt=rng.randint(2, 4), days_ago=days_ago, method=method)
        elif roll < 0.75:
            add_payment(customer, status=PaymentStatus.FAILED, category=FailureCategory.DECLINED, amount=amount, attempt=rng.randint(1, 4), days_ago=days_ago, method=method)
        elif roll < 0.85:
            add_payment(customer, status=PaymentStatus.FAILED, category=FailureCategory.NON_RECOVERABLE, amount=amount, attempt=1, days_ago=days_ago, method=method)
        else:
            add_payment(customer, status=PaymentStatus.FAILED, category=FailureCategory.EXPIRED_CARD, amount=amount, attempt=1, days_ago=days_ago, method=method)
    elif persona == "new":
        if roll < 0.55:
            add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=amount, attempt=1, days_ago=min(days_ago, 25), method=method)
        elif roll < 0.75:
            add_payment(customer, status=PaymentStatus.FAILED, category=FailureCategory.AUTHENTICATION_FAILURE, amount=amount, attempt=1, days_ago=min(days_ago, 25), method=method)
        else:
            add_payment(customer, status=PaymentStatus.PENDING, category=None, amount=amount, attempt=1, days_ago=min(days_ago, 10), method=method)
    else:
        if roll < 0.68:
            add_payment(customer, status=PaymentStatus.SUCCEEDED, category=None, amount=amount, attempt=1, days_ago=days_ago, method=method)
        elif roll < 0.80:
            add_payment(
                customer,
                status=PaymentStatus.FAILED,
                category=rng.choice([item for item in FailureCategory if item != FailureCategory.NON_RECOVERABLE]),
                amount=amount,
                attempt=rng.randint(1, 3),
                days_ago=days_ago,
                method=method,
            )
        elif roll < 0.90:
            add_payment(customer, status=PaymentStatus.ABANDONED, category=FailureCategory.ABANDONED_CHECKOUT, amount=amount, attempt=1, days_ago=days_ago, method=method, abandoned=True)
        else:
            add_payment(customer, status=PaymentStatus.PENDING, category=None, amount=amount, attempt=1, days_ago=days_ago, method=method)


def _refresh_customer_aggregates(customers: list[Customer], payments: list[Payment]) -> None:
    by_customer: dict[uuid.UUID, list[Payment]] = {}
    for payment in payments:
        by_customer.setdefault(payment.customer_id, []).append(payment)
    for customer in customers:
        owned = by_customer.get(customer.id, [])
        customer.total_payments = len(owned)
        customer.successful_payments = sum(1 for item in owned if item.status == PaymentStatus.SUCCEEDED)
        customer.failed_payments = sum(1 for item in owned if item.status == PaymentStatus.FAILED)
        customer.total_amount_paid = sum(
            (item.amount for item in owned if item.status == PaymentStatus.SUCCEEDED),
            Decimal("0.00"),
        )


def _mark_synthetic_recoveries(rng: Random, session: Session, merchant_id: uuid.UUID) -> None:
    cases = session.scalars(
        select(RecoveryCase).where(
            RecoveryCase.merchant_id == merchant_id,
            RecoveryCase.status == "open",
            RecoveryCase.eligibility == "eligible",
        )
    ).all()
    for case in cases:
        if case.recoverability_score >= Decimal("0.80") and rng.random() < 0.35:
            case.status = "recovered"
            case.resolved_at = datetime.now(timezone.utc)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic R.AI data")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMERS)
    parser.add_argument("--payments", type=int, default=DEFAULT_PAYMENTS)
    parser.add_argument("--reset", action="store_true", default=True)
    parser.add_argument("--no-reset", action="store_false", dest="reset")
    parser.add_argument("--analyze", action="store_true", default=False)
    return parser.parse_args(argv)
