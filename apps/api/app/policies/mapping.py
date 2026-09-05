from app.models.enums import RecoveryWorkflow, SubscriptionStatus, SuggestedAction
from app.models.subscription import Subscription


def map_recovery_workflow(
    action: str,
    *,
    has_recoverable_subscription: bool,
) -> RecoveryWorkflow:
    """Map a recommended action to a documented provider workflow.

    smart_retry never maps to a direct charge. One-time recovery uses a
    Payment Link. Subscription recovery is provider-managed/deferred.
    """
    try:
        suggested = SuggestedAction(action)
    except ValueError:
        return RecoveryWorkflow.NONE

    if suggested in {SuggestedAction.WAIT, SuggestedAction.DO_NOTHING}:
        return RecoveryWorkflow.NONE
    if suggested == SuggestedAction.HUMAN_REVIEW:
        return RecoveryWorkflow.APPROVAL_CASE
    if suggested == SuggestedAction.SMART_RETRY and has_recoverable_subscription:
        return RecoveryWorkflow.SUBSCRIPTION_PROVIDER_MANAGED
    if suggested in {
        SuggestedAction.SMART_RETRY,
        SuggestedAction.PAYMENT_REMINDER,
        SuggestedAction.ALTERNATE_PAYMENT_METHOD,
    }:
        return RecoveryWorkflow.PAYMENT_LINK
    return RecoveryWorkflow.NONE


def has_recoverable_subscription(subscriptions: list[Subscription] | None) -> bool:
    if not subscriptions:
        return False
    recoverable = {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.PAUSED,
    }
    return any(item.status in recoverable for item in subscriptions)
