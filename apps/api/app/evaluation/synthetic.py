from decimal import Decimal

from app.models.enums import PolicyOutcome, RecoveryEligibility, SuggestedAction

RECOVERY_ACTIONS = {
    SuggestedAction.SMART_RETRY.value,
    SuggestedAction.PAYMENT_REMINDER.value,
    SuggestedAction.ALTERNATE_PAYMENT_METHOD.value,
}


def hypothetical_recovered_amount(
    *,
    revenue_at_risk: Decimal,
    recoverability_score: Decimal,
    action: str,
    eligibility: str,
    policy_decision: str,
) -> Decimal:
    """Deterministic synthetic collection model. Not a production forecast."""

    if eligibility != RecoveryEligibility.ELIGIBLE.value:
        return Decimal("0.00")
    if policy_decision == PolicyOutcome.BLOCK.value:
        return Decimal("0.00")
    if action not in RECOVERY_ACTIONS:
        return Decimal("0.00")

    score = float(recoverability_score)
    if action == SuggestedAction.PAYMENT_REMINDER.value:
        threshold = 0.45
        weight = 0.90
    elif action == SuggestedAction.ALTERNATE_PAYMENT_METHOD.value:
        threshold = 0.40
        weight = 0.95
    else:
        threshold = 0.35
        weight = 1.00

    if score * weight >= threshold:
        return revenue_at_risk.quantize(Decimal("0.01"))
    return Decimal("0.00")
