from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.merchant_policy import MerchantPolicy
from app.policies.constants import (
    DEFAULT_AUTONOMOUS_EXECUTION,
    DEFAULT_HIGH_VALUE_THRESHOLD,
    DEFAULT_MAX_AUTONOMOUS_ACTION_AMOUNT,
    DEFAULT_MAX_RECOVERY_ATTEMPTS,
    DEFAULT_NOTIFICATIONS_ALLOWED,
    DEFAULT_PAYMENT_LINK_CREATION_ALLOWED,
    DEFAULT_REQUIRE_APPROVAL_HIGH_VALUE,
    DEFAULT_REQUIRE_APPROVAL_UNCERTAIN,
    DEFAULT_SUBSCRIPTION_RECOVERY_ALLOWED,
    POLICY_VERSION,
)
from app.policies.engine import PolicySnapshot


def get_or_create_merchant_policy(session: Session, merchant_id) -> MerchantPolicy:
    policy = session.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id == merchant_id))
    if policy is not None:
        return policy
    policy = MerchantPolicy(
        merchant_id=merchant_id,
        autonomous_execution=DEFAULT_AUTONOMOUS_EXECUTION,
        max_autonomous_action_amount=DEFAULT_MAX_AUTONOMOUS_ACTION_AMOUNT,
        high_value_threshold=DEFAULT_HIGH_VALUE_THRESHOLD,
        max_recovery_attempts=DEFAULT_MAX_RECOVERY_ATTEMPTS,
        payment_link_creation_allowed=DEFAULT_PAYMENT_LINK_CREATION_ALLOWED,
        notifications_allowed=DEFAULT_NOTIFICATIONS_ALLOWED,
        subscription_recovery_allowed=DEFAULT_SUBSCRIPTION_RECOVERY_ALLOWED,
        require_approval_for_high_value=DEFAULT_REQUIRE_APPROVAL_HIGH_VALUE,
        require_approval_for_uncertain=DEFAULT_REQUIRE_APPROVAL_UNCERTAIN,
        policy_version=POLICY_VERSION,
    )
    session.add(policy)
    session.flush()
    return policy


def policy_snapshot(policy: MerchantPolicy) -> PolicySnapshot:
    return PolicySnapshot(
        autonomous_execution=policy.autonomous_execution,
        max_autonomous_action_amount=policy.max_autonomous_action_amount,
        high_value_threshold=policy.high_value_threshold,
        max_recovery_attempts=policy.max_recovery_attempts,
        payment_link_creation_allowed=policy.payment_link_creation_allowed,
        notifications_allowed=policy.notifications_allowed,
        subscription_recovery_allowed=policy.subscription_recovery_allowed,
        require_approval_for_high_value=policy.require_approval_for_high_value,
        require_approval_for_uncertain=policy.require_approval_for_uncertain,
        policy_version=policy.policy_version,
    )


def apply_demo_guardrails(policy: MerchantPolicy) -> None:
    """Tightly scoped autonomous execution for local mock demos."""
    policy.autonomous_execution = True
    policy.max_autonomous_action_amount = DEFAULT_MAX_AUTONOMOUS_ACTION_AMOUNT
    policy.high_value_threshold = DEFAULT_HIGH_VALUE_THRESHOLD
    policy.require_approval_for_high_value = True
    policy.require_approval_for_uncertain = True
    policy.policy_version = POLICY_VERSION
