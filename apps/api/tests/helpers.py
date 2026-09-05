from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Customer, Merchant, Payment, PaymentFailure, RecoveryCase, Subscription
from app.models.enums import (
    FailureCategory,
    PaymentMethod,
    PaymentStatus,
    RecoveryCaseStatus,
    RecoveryEligibility,
    SubscriptionStatus,
    SuggestedAction,
)


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return factory()


def seed_failed_payment(
    session: Session,
    *,
    email: str = "ops@example.invalid",
    status: PaymentStatus = PaymentStatus.FAILED,
    category: FailureCategory = FailureCategory.TEMPORARY_TIMEOUT,
    attempt: int = 1,
    successful_payments: int = 8,
    failed_payments: int = 1,
    amount: Decimal = Decimal("1299.00"),
    failure_code: str = "bank_timeout",
    case_status: RecoveryCaseStatus | None = None,
    subscription: bool = False,
) -> Payment:
    merchant = Merchant(name="Test Merchant", email=email)
    session.add(merchant)
    session.flush()
    customer = Customer(
        merchant_id=merchant.id,
        external_reference="cust_test",
        name="Test Customer",
        email="customer@example.invalid",
        total_payments=successful_payments + failed_payments,
        successful_payments=successful_payments,
        failed_payments=failed_payments,
        total_amount_paid=Decimal("9000.00"),
    )
    session.add(customer)
    session.flush()
    if subscription:
        session.add(
            Subscription(
                merchant_id=merchant.id,
                customer_id=customer.id,
                external_subscription_id="sub_test",
                plan_name="Growth",
                amount=Decimal("999.00"),
                currency="INR",
                status=SubscriptionStatus.ACTIVE,
            )
        )
    payment = Payment(
        merchant_id=merchant.id,
        customer_id=customer.id,
        external_payment_id="pay_test",
        amount=amount,
        currency="INR",
        payment_method=PaymentMethod.CARD,
        status=status,
        attempt_number=attempt,
        checkout_started=True,
        checkout_completed=status != PaymentStatus.ABANDONED,
    )
    session.add(payment)
    session.flush()
    session.add(
        PaymentFailure(
            payment_id=payment.id,
            failure_code=failure_code,
            failure_category=category,
            failure_message="synthetic",
        )
    )
    if case_status is not None:
        session.add(
            RecoveryCase(
                merchant_id=merchant.id,
                payment_id=payment.id,
                revenue_at_risk=amount,
                recoverability_score=Decimal("0.5000"),
                priority="medium",
                eligibility=RecoveryEligibility.INELIGIBLE,
                suggested_action=SuggestedAction.DO_NOTHING,
                status=case_status,
                explanation_factors=["existing"],
            )
        )
    session.commit()
    return session.scalar(
        select(Payment)
        .where(Payment.id == payment.id)
        .options(
            selectinload(Payment.customer).selectinload(Customer.subscriptions),
            selectinload(Payment.failures),
            selectinload(Payment.recovery_case),
        )
    )
