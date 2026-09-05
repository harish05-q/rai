from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PolicyOutcome, RecoveryWorkflow, SuggestedAction
from app.policies.constants import (
    BLOCKED_OPERATIONS,
    MIN_CONFIDENCE_AUTONOMOUS,
    NOOP_ACTIONS,
    POLICY_VERSION,
    PROVIDER_ACTIONS,
    SUPPORTED_ACTIONS,
    SUSPICIOUS_TOKENS,
)
from app.policies.mapping import map_recovery_workflow


class PolicySnapshot(BaseModel):
    autonomous_execution: bool
    max_autonomous_action_amount: Decimal
    high_value_threshold: Decimal
    max_recovery_attempts: int
    payment_link_creation_allowed: bool
    notifications_allowed: bool
    subscription_recovery_allowed: bool
    require_approval_for_high_value: bool
    require_approval_for_uncertain: bool
    policy_version: str = POLICY_VERSION


class PolicyEvaluationInput(BaseModel):
    action: str
    amount: Decimal
    attempt_number: int
    prior_recovery_attempts: int
    has_recoverable_subscription: bool
    eligibility: str
    recoverability_assessment: str | None = None
    confidence: float | None = None
    concerns: list[str] = Field(default_factory=list)
    failure_category: str | None = None
    failure_code: str | None = None
    policy: PolicySnapshot


class PolicyDecision(BaseModel):
    decision: PolicyOutcome
    reason: str
    required_approval: bool
    action: str
    workflow: str
    policy_version: str
    limits_checked: list[str]
    created_at: datetime


def evaluate_policy(payload: PolicyEvaluationInput) -> PolicyDecision:
    """Deterministic authorization. The LLM never calls this."""
    now = datetime.now(timezone.utc)
    checked: list[str] = []
    action = (payload.action or "").strip().lower()
    workflow = map_recovery_workflow(
        action,
        has_recoverable_subscription=payload.has_recoverable_subscription,
    )
    policy = payload.policy

    def result(decision: PolicyOutcome, reason: str, extra: list[str] | None = None) -> PolicyDecision:
        limits = checked + (extra or [])
        return PolicyDecision(
            decision=decision,
            reason=reason,
            required_approval=decision == PolicyOutcome.REQUIRE_APPROVAL,
            action=action,
            workflow=workflow.value,
            policy_version=policy.policy_version or POLICY_VERSION,
            limits_checked=limits,
            created_at=now,
        )

    checked.append("supported_operation")
    if action in BLOCKED_OPERATIONS:
        return result(PolicyOutcome.BLOCK, "Unsupported payment operation is blocked by policy.")
    try:
        suggested = SuggestedAction(action)
    except ValueError:
        return result(PolicyOutcome.BLOCK, "Unknown recovery action is blocked.")
    if suggested not in SUPPORTED_ACTIONS:
        return result(PolicyOutcome.BLOCK, "Unknown recovery action is blocked.")

    if suggested == SuggestedAction.HUMAN_REVIEW or workflow == RecoveryWorkflow.APPROVAL_CASE:
        checked.append("human_review")
        return result(PolicyOutcome.REQUIRE_APPROVAL, "Human review is required before any recovery action.")

    if suggested in NOOP_ACTIONS:
        checked.append("noop_action")
        return result(PolicyOutcome.ALLOW, "No provider operation is required for this recommendation.")

    if workflow == RecoveryWorkflow.PAYMENT_LINK:
        checked.append("payment_link_creation_allowed")
        if not policy.payment_link_creation_allowed:
            return result(PolicyOutcome.BLOCK, "Payment Link recovery is disabled for this merchant.")

    if workflow == RecoveryWorkflow.SUBSCRIPTION_PROVIDER_MANAGED:
        checked.append("subscription_recovery_allowed")
        if not policy.subscription_recovery_allowed:
            return result(PolicyOutcome.BLOCK, "Subscription recovery is disabled for this merchant.")

    checked.append("max_recovery_attempts")
    if (
        payload.prior_recovery_attempts >= policy.max_recovery_attempts
        or payload.attempt_number > policy.max_recovery_attempts
    ):
        return result(
            PolicyOutcome.BLOCK,
            "Recovery attempt limit has been reached.",
        )

    uncertain = _is_uncertain(payload)
    if policy.require_approval_for_uncertain and uncertain:
        checked.append("require_approval_for_uncertain")
        return result(
            PolicyOutcome.REQUIRE_APPROVAL,
            "Uncertain or suspicious recovery context requires merchant approval.",
        )

    checked.append("high_value_threshold")
    if policy.require_approval_for_high_value and payload.amount >= policy.high_value_threshold:
        return result(
            PolicyOutcome.REQUIRE_APPROVAL,
            "Amount meets the high-value threshold and requires merchant approval.",
        )

    checked.append("max_autonomous_action_amount")
    if payload.amount > policy.max_autonomous_action_amount:
        return result(
            PolicyOutcome.REQUIRE_APPROVAL,
            "Amount exceeds the autonomous execution limit.",
        )

    checked.append("autonomous_execution")
    if suggested in PROVIDER_ACTIONS and not policy.autonomous_execution:
        return result(
            PolicyOutcome.REQUIRE_APPROVAL,
            "Autonomous execution is disabled; merchant approval is required.",
        )

    return result(PolicyOutcome.ALLOW, "Policy allows bounded execution of the mapped provider workflow.")


def _is_uncertain(payload: PolicyEvaluationInput) -> bool:
    if payload.eligibility == "review":
        return True
    if (payload.recoverability_assessment or "").lower() in {"uncertain", "none"}:
        return True
    if payload.confidence is not None and payload.confidence < MIN_CONFIDENCE_AUTONOMOUS:
        return True
    haystack = " ".join(
        [
            payload.failure_category or "",
            payload.failure_code or "",
            *payload.concerns,
        ]
    ).lower()
    return any(token in haystack for token in SUSPICIOUS_TOKENS)
