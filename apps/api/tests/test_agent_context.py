from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.agents.context import build_recovery_context
from app.agents.schemas import LLMStructuredOutput
from app.models.enums import FailureCategory, PaymentStatus, SuggestedAction
from app.recovery.service import RecoveryAnalysisService
from tests.helpers import make_session, seed_failed_payment


def _case_context(**kwargs):
    session = make_session()
    payment = seed_failed_payment(session, **kwargs)
    RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    session.refresh(payment)
    context = build_recovery_context(payment.recovery_case)
    session.close()
    return context


def test_context_includes_payment_customer_failure_and_signals() -> None:
    context = _case_context(subscription=True)
    assert context.payment.amount == Decimal("1299.00")
    assert context.payment.payment_method == "card"
    assert context.payment.attempt_number == 1
    assert context.failure is not None
    assert context.failure.failure_category == FailureCategory.TEMPORARY_TIMEOUT
    assert context.customer is not None
    assert context.customer.successful_payments == 8
    assert context.customer.total_amount_paid == Decimal("9000.00")
    assert context.subscription is not None
    assert context.subscription.plan_name == "Growth"
    assert context.deterministic.suggested_action == SuggestedAction.SMART_RETRY
    assert context.deterministic.explanation_factors
    payload = context.to_prompt_payload()
    assert "email" not in str(payload)
    assert "Test Customer" not in str(payload)


def test_valid_structured_output() -> None:
    parsed = LLMStructuredOutput.model_validate(
        {
            "diagnosis": {
                "failure_category": "temporary_timeout",
                "failure_severity": "low",
                "recoverability_assessment": "high",
                "key_context_factors": ["temporary bank failure"],
            },
            "strategy": {
                "recommended_action": "smart_retry",
                "rationale": "Timeouts are often recoverable with a bounded retry.",
                "confidence": 0.84,
                "timing": "immediate",
                "alternative_action": "wait",
                "concerns": [],
            },
        }
    )
    assert parsed.strategy.recommended_action == SuggestedAction.SMART_RETRY
    assert parsed.strategy.confidence == 0.84


def test_structured_output_rejects_missing_fields() -> None:
    with pytest.raises(ValidationError):
        LLMStructuredOutput.model_validate({"diagnosis": {}, "strategy": {}})


def test_structured_output_rejects_invalid_action() -> None:
    with pytest.raises(ValidationError):
        LLMStructuredOutput.model_validate(
            {
                "diagnosis": {
                    "failure_category": "temporary_timeout",
                    "failure_severity": "low",
                    "recoverability_assessment": "high",
                    "key_context_factors": ["timeout"],
                },
                "strategy": {
                    "recommended_action": "refund",
                    "rationale": "Do not allow refunds from the model.",
                    "confidence": 0.9,
                    "timing": "immediate",
                    "alternative_action": None,
                    "concerns": [],
                },
            }
        )


def test_structured_output_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        LLMStructuredOutput.model_validate(
            {
                "diagnosis": {
                    "failure_category": "temporary_timeout",
                    "failure_severity": "low",
                    "recoverability_assessment": "high",
                    "key_context_factors": ["timeout"],
                },
                "strategy": {
                    "recommended_action": "smart_retry",
                    "rationale": "Confidence must be a probability.",
                    "confidence": 1.4,
                    "timing": "immediate",
                    "alternative_action": None,
                    "concerns": [],
                },
            }
        )


def test_abandoned_context_uses_checkout_state() -> None:
    context = _case_context(status=PaymentStatus.ABANDONED, category=FailureCategory.ABANDONED_CHECKOUT)
    assert context.payment.checkout_completed is False
    assert context.payment.status == PaymentStatus.ABANDONED
    assert context.deterministic.suggested_action == SuggestedAction.PAYMENT_REMINDER
