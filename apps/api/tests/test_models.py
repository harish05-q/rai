from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Customer, Merchant, Payment, PaymentFailure, RecoveryCase
from app.models.enums import PaymentMethod, PaymentStatus, RecoveryCaseStatus, RecoveryEligibility, SuggestedAction
from tests.helpers import make_session


def test_customer_requires_merchant_and_identity() -> None:
    session = make_session()
    session.add(Customer(name="No Merchant", email="a@example.invalid", external_reference="x"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_payment_relationships_round_trip() -> None:
    session = make_session()
    merchant = Merchant(name="Rel Merchant", email="rel@example.invalid")
    session.add(merchant)
    session.flush()
    customer = Customer(
        merchant_id=merchant.id,
        external_reference="cust_1",
        name="Ada",
        email="ada@example.invalid",
        total_payments=1,
        successful_payments=0,
        failed_payments=1,
        total_amount_paid=Decimal("0.00"),
    )
    session.add(customer)
    session.flush()
    payment = Payment(
        merchant_id=merchant.id,
        customer_id=customer.id,
        external_payment_id="pay_1",
        amount=Decimal("499.00"),
        currency="INR",
        payment_method=PaymentMethod.UPI,
        status=PaymentStatus.FAILED,
        attempt_number=1,
        checkout_started=True,
        checkout_completed=True,
    )
    session.add(payment)
    session.flush()
    session.add(
        PaymentFailure(
            payment_id=payment.id,
            failure_code="bank_timeout",
            failure_category="temporary_timeout",
            failure_message="timeout",
        )
    )
    session.add(
        RecoveryCase(
            merchant_id=merchant.id,
            payment_id=payment.id,
            revenue_at_risk=Decimal("499.00"),
            recoverability_score=Decimal("0.8000"),
            priority="high",
            eligibility=RecoveryEligibility.ELIGIBLE,
            suggested_action=SuggestedAction.SMART_RETRY,
            status=RecoveryCaseStatus.OPEN,
            explanation_factors=["temporary bank failure"],
        )
    )
    session.commit()
    session.refresh(payment)

    assert payment.customer.name == "Ada"
    assert payment.merchant.email == "rel@example.invalid"
    assert len(payment.failures) == 1
    assert payment.failures[0].failure_category == "temporary_timeout"
    assert payment.recovery_case is not None
    assert payment.recovery_case.priority == "high"
