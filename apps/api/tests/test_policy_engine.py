from decimal import Decimal

from app.models.enums import PolicyOutcome
from app.policies.engine import PolicyEvaluationInput, PolicySnapshot, evaluate_policy
from app.policies.constants import POLICY_VERSION


def _policy(**overrides) -> PolicySnapshot:
    data = dict(
        autonomous_execution=True,
        max_autonomous_action_amount=Decimal("25000.00"),
        high_value_threshold=Decimal("50000.00"),
        max_recovery_attempts=3,
        payment_link_creation_allowed=True,
        notifications_allowed=True,
        subscription_recovery_allowed=True,
        require_approval_for_high_value=True,
        require_approval_for_uncertain=True,
        policy_version=POLICY_VERSION,
    )
    data.update(overrides)
    return PolicySnapshot(**data)


def _input(**overrides) -> PolicyEvaluationInput:
    data = dict(
        action="payment_reminder",
        amount=Decimal("1299.00"),
        attempt_number=1,
        prior_recovery_attempts=0,
        has_recoverable_subscription=False,
        eligibility="eligible",
        recoverability_assessment="high",
        confidence=0.88,
        concerns=[],
        failure_category="temporary_timeout",
        failure_code="bank_timeout",
        policy=_policy(),
    )
    data.update(overrides)
    return PolicyEvaluationInput(**data)


def test_low_value_allowed_action() -> None:
    decision = evaluate_policy(_input())
    assert decision.decision == PolicyOutcome.ALLOW
    assert decision.workflow == "payment_link"
    assert decision.required_approval is False


def test_high_value_requires_approval() -> None:
    decision = evaluate_policy(_input(amount=Decimal("75000.00")))
    assert decision.decision == PolicyOutcome.REQUIRE_APPROVAL
    assert "high-value" in decision.reason.lower()


def test_unsupported_action_blocked() -> None:
    decision = evaluate_policy(_input(action="refund"))
    assert decision.decision == PolicyOutcome.BLOCK


def test_autonomous_execution_disabled_requires_approval() -> None:
    decision = evaluate_policy(_input(policy=_policy(autonomous_execution=False)))
    assert decision.decision == PolicyOutcome.REQUIRE_APPROVAL
    assert "autonomous" in decision.reason.lower()


def test_retry_limit_blocked() -> None:
    decision = evaluate_policy(_input(prior_recovery_attempts=3))
    assert decision.decision == PolicyOutcome.BLOCK
    assert "attempt limit" in decision.reason.lower()


def test_wait_allowed_without_provider() -> None:
    decision = evaluate_policy(_input(action="wait", policy=_policy(autonomous_execution=False)))
    assert decision.decision == PolicyOutcome.ALLOW
    assert decision.workflow == "none"


def test_human_review_requires_approval() -> None:
    decision = evaluate_policy(_input(action="human_review"))
    assert decision.decision == PolicyOutcome.REQUIRE_APPROVAL


def test_payment_link_disabled_blocked() -> None:
    decision = evaluate_policy(_input(policy=_policy(payment_link_creation_allowed=False)))
    assert decision.decision == PolicyOutcome.BLOCK


def test_subscription_smart_retry_maps_to_provider_managed() -> None:
    decision = evaluate_policy(_input(action="smart_retry", has_recoverable_subscription=True))
    assert decision.workflow == "subscription_provider_managed"
    assert decision.decision == PolicyOutcome.ALLOW
