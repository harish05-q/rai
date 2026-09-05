from decimal import Decimal

from app.models.enums import FailureCategory, SubscriptionStatus
from app.recovery.scoring import ScoringInput, score_recoverability


def _score(**overrides) -> ScoringInput:
    payload = dict(
        failure_category=FailureCategory.TEMPORARY_TIMEOUT,
        successful_payments=8,
        failed_payments=1,
        total_payments=9,
        attempt_number=1,
        amount=Decimal("1299.00"),
        checkout_completed=True,
        subscription_status=SubscriptionStatus.ACTIVE,
    )
    payload.update(overrides)
    return ScoringInput(**payload)


def test_temporary_failure_scores_high() -> None:
    result = score_recoverability(_score())
    assert 0.7 <= result.recoverability_score <= 1.0
    assert "temporary bank failure" in result.explanation_factors
    assert "first failed attempt" in result.explanation_factors
    assert "active subscription" in result.explanation_factors


def test_insufficient_funds_scores_lower_than_timeout() -> None:
    timeout = score_recoverability(_score())
    nsf = score_recoverability(_score(failure_category=FailureCategory.INSUFFICIENT_FUNDS))
    assert nsf.recoverability_score < timeout.recoverability_score
    assert "insufficient funds" in nsf.explanation_factors


def test_expired_card_is_explainable() -> None:
    result = score_recoverability(_score(failure_category=FailureCategory.EXPIRED_CARD))
    assert 0.4 <= result.recoverability_score <= 0.9
    assert "expired card" in result.explanation_factors


def test_authentication_failure_is_explainable() -> None:
    result = score_recoverability(_score(failure_category=FailureCategory.AUTHENTICATION_FAILURE))
    assert result.recoverability_score > 0.5
    assert "authentication failure" in result.explanation_factors


def test_customer_success_history_increases_score() -> None:
    weak = score_recoverability(
        _score(successful_payments=0, failed_payments=0, total_payments=1, subscription_status=None)
    )
    strong = score_recoverability(_score(successful_payments=8, failed_payments=1, total_payments=9))
    assert strong.recoverability_score > weak.recoverability_score
    assert "8 previous successful payments" in strong.explanation_factors


def test_repeated_failures_decrease_score() -> None:
    first = score_recoverability(_score(failed_payments=1, attempt_number=1))
    repeat = score_recoverability(_score(failed_payments=6, attempt_number=4, total_payments=10))
    assert repeat.recoverability_score < first.recoverability_score
    assert "historically poor payment behavior" in repeat.explanation_factors
