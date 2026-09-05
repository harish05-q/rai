"""Centralized thresholds for deterministic recovery intelligence.

This module is the only place that should define recoverability weights,
retry limits, and high-value cutoffs. Do not scatter magic numbers in routes.
"""

from decimal import Decimal

from app.models.enums import FailureCategory, SuggestedAction

MAX_RETRY_ATTEMPTS = 3
HIGH_VALUE_THRESHOLD = Decimal("50000.00")
REVIEW_VALUE_THRESHOLD = Decimal("100000.00")
RELIABLE_SUCCESS_COUNT = 8
POOR_FAILURE_COUNT = 5

FAILURE_CATEGORY_BASE_SCORE: dict[FailureCategory, float] = {
    FailureCategory.TEMPORARY_TIMEOUT: 0.78,
    FailureCategory.AUTHENTICATION_FAILURE: 0.64,
    FailureCategory.EXPIRED_CARD: 0.58,
    FailureCategory.ABANDONED_CHECKOUT: 0.54,
    FailureCategory.INSUFFICIENT_FUNDS: 0.46,
    FailureCategory.DECLINED: 0.34,
    FailureCategory.OTHER: 0.28,
    FailureCategory.NON_RECOVERABLE: 0.04,
}

SCORE_WEIGHTS = {
    "success_history": 0.16,
    "failure_history": 0.14,
    "first_attempt": 0.06,
    "attempt_penalty": 0.10,
    "active_subscription": 0.08,
    "high_value": 0.04,
    "reliable_customer": 0.08,
    "poor_customer": 0.12,
    "expired_card_penalty": 0.05,
}

PRIORITY_HIGH_SCORE = 0.70
PRIORITY_MEDIUM_SCORE = 0.40

NON_RECOVERABLE_FAILURE_CODES = frozenset(
    {
        "card_stolen",
        "fraud_suspected",
        "account_closed",
        "chargeback_in_progress",
    }
)

DEFAULT_ACTION_BY_CATEGORY: dict[FailureCategory, SuggestedAction] = {
    FailureCategory.TEMPORARY_TIMEOUT: SuggestedAction.SMART_RETRY,
    FailureCategory.AUTHENTICATION_FAILURE: SuggestedAction.PAYMENT_REMINDER,
    FailureCategory.EXPIRED_CARD: SuggestedAction.ALTERNATE_PAYMENT_METHOD,
    FailureCategory.ABANDONED_CHECKOUT: SuggestedAction.PAYMENT_REMINDER,
    FailureCategory.INSUFFICIENT_FUNDS: SuggestedAction.WAIT,
    FailureCategory.DECLINED: SuggestedAction.SMART_RETRY,
    FailureCategory.OTHER: SuggestedAction.HUMAN_REVIEW,
    FailureCategory.NON_RECOVERABLE: SuggestedAction.DO_NOTHING,
}
