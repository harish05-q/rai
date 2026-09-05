from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import (
    FailureCategory,
    PaymentStatus,
    RecoveryCaseStatus,
    RecoveryEligibility,
    SuggestedAction,
)
from app.recovery.constants import (
    DEFAULT_ACTION_BY_CATEGORY,
    MAX_RETRY_ATTEMPTS,
    NON_RECOVERABLE_FAILURE_CODES,
    REVIEW_VALUE_THRESHOLD,
)


@dataclass(frozen=True)
class EligibilityInput:
    payment_status: PaymentStatus
    failure_category: FailureCategory | None
    failure_code: str | None
    attempt_number: int
    amount: Decimal | None
    customer_present: bool
    existing_case_status: RecoveryCaseStatus | None


@dataclass(frozen=True)
class EligibilityResult:
    eligibility: RecoveryEligibility
    suggested_action: SuggestedAction
    reason: str


def evaluate_eligibility(payload: EligibilityInput) -> EligibilityResult:
    """Deterministic eligibility and baseline suggested action.

    This deterministic strategy is the baseline that will later be compared
    against R.AI's AI strategy. It is not an AI recommendation.
    """

    if payload.existing_case_status == RecoveryCaseStatus.RECOVERED:
        return EligibilityResult(
            RecoveryEligibility.INELIGIBLE,
            SuggestedAction.DO_NOTHING,
            "already recovered",
        )
    if payload.existing_case_status == RecoveryCaseStatus.RESOLVED:
        return EligibilityResult(
            RecoveryEligibility.INELIGIBLE,
            SuggestedAction.DO_NOTHING,
            "recovery case already resolved",
        )

    if payload.payment_status == PaymentStatus.SUCCEEDED:
        return EligibilityResult(
            RecoveryEligibility.INELIGIBLE,
            SuggestedAction.DO_NOTHING,
            "payment already succeeded",
        )

    if payload.payment_status not in {PaymentStatus.FAILED, PaymentStatus.ABANDONED}:
        return EligibilityResult(
            RecoveryEligibility.INELIGIBLE,
            SuggestedAction.DO_NOTHING,
            "payment is not in a recoverable failed or abandoned state",
        )

    if payload.failure_code in NON_RECOVERABLE_FAILURE_CODES:
        return EligibilityResult(
            RecoveryEligibility.INELIGIBLE,
            SuggestedAction.DO_NOTHING,
            "clearly non-recoverable failure code",
        )

    if payload.failure_category == FailureCategory.NON_RECOVERABLE:
        return EligibilityResult(
            RecoveryEligibility.INELIGIBLE,
            SuggestedAction.DO_NOTHING,
            "clearly non-recoverable condition",
        )

    if payload.attempt_number > MAX_RETRY_ATTEMPTS:
        return EligibilityResult(
            RecoveryEligibility.INELIGIBLE,
            SuggestedAction.DO_NOTHING,
            "retry limit exceeded",
        )

    if not payload.customer_present or payload.amount is None:
        return EligibilityResult(
            RecoveryEligibility.REVIEW,
            SuggestedAction.HUMAN_REVIEW,
            "missing required information",
        )

    if payload.amount >= REVIEW_VALUE_THRESHOLD:
        return EligibilityResult(
            RecoveryEligibility.REVIEW,
            SuggestedAction.HUMAN_REVIEW,
            "high-value payment requires human review",
        )

    category = payload.failure_category or FailureCategory.OTHER
    action = DEFAULT_ACTION_BY_CATEGORY[category]
    if category == FailureCategory.DECLINED and payload.attempt_number > 1:
        action = SuggestedAction.HUMAN_REVIEW

    return EligibilityResult(
        RecoveryEligibility.ELIGIBLE,
        action,
        "failed payment is potentially recoverable",
    )
