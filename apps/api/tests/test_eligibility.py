from decimal import Decimal

from app.models.enums import (
    FailureCategory,
    PaymentStatus,
    RecoveryCaseStatus,
    RecoveryEligibility,
    SuggestedAction,
)
from app.recovery.eligibility import EligibilityInput, evaluate_eligibility


def _payload(**overrides) -> EligibilityInput:
    payload = dict(
        payment_status=PaymentStatus.FAILED,
        failure_category=FailureCategory.TEMPORARY_TIMEOUT,
        failure_code="bank_timeout",
        attempt_number=1,
        amount=Decimal("1299.00"),
        customer_present=True,
        existing_case_status=None,
    )
    payload.update(overrides)
    return EligibilityInput(**payload)


def test_eligible_failed_payment() -> None:
    result = evaluate_eligibility(_payload())
    assert result.eligibility == RecoveryEligibility.ELIGIBLE
    assert result.suggested_action == SuggestedAction.SMART_RETRY


def test_already_recovered_is_ineligible() -> None:
    result = evaluate_eligibility(_payload(existing_case_status=RecoveryCaseStatus.RECOVERED))
    assert result.eligibility == RecoveryEligibility.INELIGIBLE
    assert result.suggested_action == SuggestedAction.DO_NOTHING
    assert result.reason == "already recovered"


def test_retry_limit_exceeded() -> None:
    result = evaluate_eligibility(_payload(attempt_number=4))
    assert result.eligibility == RecoveryEligibility.INELIGIBLE
    assert result.reason == "retry limit exceeded"


def test_non_recoverable_condition() -> None:
    result = evaluate_eligibility(
        _payload(failure_category=FailureCategory.NON_RECOVERABLE, failure_code="account_closed")
    )
    assert result.eligibility == RecoveryEligibility.INELIGIBLE
    assert result.suggested_action == SuggestedAction.DO_NOTHING
