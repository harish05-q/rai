from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import FailureCategory, RecoveryPriority, SubscriptionStatus
from app.recovery.constants import (
    FAILURE_CATEGORY_BASE_SCORE,
    HIGH_VALUE_THRESHOLD,
    MAX_RETRY_ATTEMPTS,
    POOR_FAILURE_COUNT,
    PRIORITY_HIGH_SCORE,
    PRIORITY_MEDIUM_SCORE,
    RELIABLE_SUCCESS_COUNT,
    SCORE_WEIGHTS,
)


@dataclass(frozen=True)
class ScoringInput:
    failure_category: FailureCategory | None
    successful_payments: int
    failed_payments: int
    total_payments: int
    attempt_number: int
    amount: Decimal
    checkout_completed: bool
    subscription_status: SubscriptionStatus | None


@dataclass(frozen=True)
class ScoringResult:
    recoverability_score: float
    explanation_factors: list[str]
    priority: RecoveryPriority


def _clamp(value: float) -> float:
    return round(min(1.0, max(0.0, value)), 4)


def priority_for_score(score: float) -> RecoveryPriority:
    if score >= PRIORITY_HIGH_SCORE:
        return RecoveryPriority.HIGH
    if score >= PRIORITY_MEDIUM_SCORE:
        return RecoveryPriority.MEDIUM
    return RecoveryPriority.LOW


def score_recoverability(payload: ScoringInput) -> ScoringResult:
    """Return a deterministic recoverability score in [0.0, 1.0].

    The formula is:

        score = base(failure_category)
              + success_history_weight * success_ratio
              - failure_history_weight * min(failed_payments / 8, 1)
              + first_attempt_bonus OR - attempt_penalty * extra_attempts_ratio
              + active_subscription_bonus
              + high_value_bonus
              + reliable_customer_bonus
              - poor_customer_penalty

    All weights live in ``recovery.constants``. The explanation factors are
    operator-facing labels, not hidden chain-of-thought.
    """

    category = payload.failure_category or FailureCategory.OTHER
    base = FAILURE_CATEGORY_BASE_SCORE[category]
    factors: list[str] = [_category_factor(category)]

    if category == FailureCategory.EXPIRED_CARD:
        score_adjustment = SCORE_WEIGHTS["expired_card_penalty"]
        factors.append("expired card")
    else:
        score_adjustment = 0.0
    total_payments = max(payload.total_payments, 1)
    success_ratio = payload.successful_payments / total_payments
    score = (
        base
        + SCORE_WEIGHTS["success_history"] * success_ratio
        - score_adjustment
    )
    if payload.successful_payments > 0:
        factors.append(f"{payload.successful_payments} previous successful payments")

    failure_ratio = min(payload.failed_payments / 8, 1.0)
    score -= SCORE_WEIGHTS["failure_history"] * failure_ratio
    if payload.failed_payments > 0:
        factors.append(f"{payload.failed_payments} previous failed payments")

    if payload.attempt_number <= 1:
        score += SCORE_WEIGHTS["first_attempt"]
        factors.append("first failed attempt")
    else:
        extra = min((payload.attempt_number - 1) / MAX_RETRY_ATTEMPTS, 1.0)
        score -= SCORE_WEIGHTS["attempt_penalty"] * extra
        factors.append(f"attempt {payload.attempt_number} of {MAX_RETRY_ATTEMPTS} retries")

    if payload.subscription_status == SubscriptionStatus.ACTIVE:
        score += SCORE_WEIGHTS["active_subscription"]
        factors.append("active subscription")
    elif payload.subscription_status == SubscriptionStatus.PAST_DUE:
        factors.append("past-due subscription")

    if payload.amount >= HIGH_VALUE_THRESHOLD:
        score += SCORE_WEIGHTS["high_value"]
        factors.append(f"high-value payment of {payload.amount}")

    if not payload.checkout_completed:
        factors.append("checkout not completed")

    if (
        payload.successful_payments >= RELIABLE_SUCCESS_COUNT
        and payload.failed_payments <= 1
    ):
        score += SCORE_WEIGHTS["reliable_customer"]
        factors.append("historically reliable customer")

    if payload.failed_payments >= POOR_FAILURE_COUNT:
        score -= SCORE_WEIGHTS["poor_customer"]
        factors.append("historically poor payment behavior")

    recoverability_score = _clamp(score)
    return ScoringResult(
        recoverability_score=recoverability_score,
        explanation_factors=factors,
        priority=priority_for_score(recoverability_score),
    )


def _category_factor(category: FailureCategory) -> str:
    labels = {
        FailureCategory.TEMPORARY_TIMEOUT: "temporary bank failure",
        FailureCategory.INSUFFICIENT_FUNDS: "insufficient funds",
        FailureCategory.EXPIRED_CARD: "expired card",
        FailureCategory.AUTHENTICATION_FAILURE: "authentication failure",
        FailureCategory.DECLINED: "payment declined",
        FailureCategory.ABANDONED_CHECKOUT: "abandoned checkout",
        FailureCategory.NON_RECOVERABLE: "non-recoverable failure",
        FailureCategory.OTHER: "unclassified failure",
    }
    return labels[category]
