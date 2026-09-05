from app.agents.exceptions import InvalidModelOutputError, ProviderUnavailableError
from app.agents.schemas import LLMStructuredOutput, RecoveryAgentContext
from app.models.enums import (
    FailureCategory,
    FailureSeverity,
    RecoverabilityAssessment,
    RecoveryEligibility,
    StrategyTiming,
    SuggestedAction,
)


class MockLLMProvider:
    """Deterministic context-driven provider for local development and tests."""

    name = "mock"
    model_name = "rai-mock-v1"
    available = True

    def generate(self, context: RecoveryAgentContext) -> LLMStructuredOutput:
        if context.payment is None:
            raise ProviderUnavailableError("Mock provider received incomplete payment context")
        payload = _decision_from_context(context)
        try:
            return LLMStructuredOutput.model_validate(payload)
        except Exception as exc:
            raise InvalidModelOutputError("Mock provider produced invalid structured output") from exc


def _decision_from_context(context: RecoveryAgentContext) -> dict:
    eligibility = context.deterministic.eligibility
    category = _category(context)
    attempt = context.payment.attempt_number
    score = float(context.deterministic.recoverability_score)
    success = context.customer.successful_payments if context.customer else 0
    failed = context.customer.failed_payments if context.customer else 0

    action = SuggestedAction(context.deterministic.suggested_action)
    timing = StrategyTiming.DELAYED
    alternative = SuggestedAction.HUMAN_REVIEW
    severity = FailureSeverity.MEDIUM
    assessment = RecoverabilityAssessment.MEDIUM
    confidence = min(0.93, max(0.42, score + 0.04))

    if eligibility == RecoveryEligibility.INELIGIBLE or category == FailureCategory.NON_RECOVERABLE:
        action = SuggestedAction.DO_NOTHING
        alternative = None
        timing = StrategyTiming.NONE
        severity = FailureSeverity.HIGH
        assessment = RecoverabilityAssessment.NONE
        confidence = 0.91
        rationale = (
            "The failure looks non-recoverable or the case is ineligible, so R.AI recommends no recovery action."
        )
        concerns = ["Automated recovery is unlikely to succeed from the supplied context."]
    elif eligibility == RecoveryEligibility.REVIEW:
        action = SuggestedAction.HUMAN_REVIEW
        alternative = SuggestedAction.WAIT
        timing = StrategyTiming.NONE
        severity = FailureSeverity.HIGH
        assessment = RecoverabilityAssessment.UNCERTAIN
        confidence = 0.62
        rationale = (
            "High-value or incomplete context requires an operator review before any recovery attempt."
        )
        concerns = ["Uncertain recoverability until an operator inspects the case."]
    elif category == FailureCategory.EXPIRED_CARD:
        action = SuggestedAction.ALTERNATE_PAYMENT_METHOD
        alternative = SuggestedAction.PAYMENT_REMINDER
        timing = StrategyTiming.AFTER_CUSTOMER_ACTION
        assessment = RecoverabilityAssessment.MEDIUM
        rationale = (
            "The instrument appears expired, so another charge on the same method is unlikely to recover the payment."
        )
        concerns = ["Customer action is required to present a valid instrument."]
    elif category == FailureCategory.INSUFFICIENT_FUNDS:
        action = SuggestedAction.WAIT
        alternative = SuggestedAction.PAYMENT_REMINDER
        timing = StrategyTiming.DELAYED
        severity = FailureSeverity.LOW
        assessment = RecoverabilityAssessment.MEDIUM
        rationale = (
            "Insufficient funds is typically temporary. Waiting is safer than an immediate retry."
        )
        concerns = ["An immediate retry may fail again before the balance recovers."]
    elif category == FailureCategory.ABANDONED_CHECKOUT:
        action = SuggestedAction.PAYMENT_REMINDER
        alternative = SuggestedAction.WAIT
        timing = StrategyTiming.AFTER_CUSTOMER_ACTION
        severity = FailureSeverity.LOW
        rationale = (
            "Checkout was not completed. A reminder is more appropriate than retrying an unfinished payment."
        )
        concerns = []
    elif category == FailureCategory.TEMPORARY_TIMEOUT:
        action = SuggestedAction.SMART_RETRY
        alternative = SuggestedAction.WAIT
        timing = StrategyTiming.IMMEDIATE
        severity = FailureSeverity.LOW
        assessment = RecoverabilityAssessment.HIGH
        rationale = (
            "A temporary processor or bank timeout is often recoverable with a bounded retry."
        )
        concerns = ["Retry limits still apply; this recommendation does not execute a charge."]
    elif (
        category == FailureCategory.DECLINED
        and context.payment.payment_method == "card"
        and success >= 8
        and attempt <= 2
    ):
        action = SuggestedAction.ALTERNATE_PAYMENT_METHOD
        alternative = SuggestedAction.SMART_RETRY
        timing = StrategyTiming.AFTER_CUSTOMER_ACTION
        assessment = RecoverabilityAssessment.MEDIUM
        confidence = min(0.91, max(0.7, score + 0.08))
        rationale = (
            "The payment instrument appears unsuitable for another immediate retry, while the customer's "
            "payment history indicates strong willingness to pay."
        )
        concerns = ["A same-instrument retry may repeat the decline."]
    elif attempt >= 3:
        action = SuggestedAction.WAIT
        alternative = SuggestedAction.HUMAN_REVIEW
        timing = StrategyTiming.DELAYED
        assessment = RecoverabilityAssessment.LOW
        rationale = (
            "Multiple attempts have already been made. Waiting is safer than another immediate retry."
        )
        concerns = ["Retry exhaustion risk is elevated."]
    elif failed >= 5:
        action = SuggestedAction.HUMAN_REVIEW
        alternative = SuggestedAction.DO_NOTHING
        timing = StrategyTiming.NONE
        assessment = RecoverabilityAssessment.UNCERTAIN
        rationale = (
            "Repeated historical failures add uncertainty. An operator should review before further recovery."
        )
        concerns = ["Customer failure history is elevated."]
    else:
        rationale = (
            f"The supplied failure category ({category.value}) and deterministic eligibility "
            f"({eligibility}) support a conservative {action.value} recommendation."
        )
        concerns = []

    factors = list(context.deterministic.explanation_factors[:4])
    if context.failure:
        factors.insert(0, f"failure category {category.value}")
    if context.customer:
        factors.append(f"{success} previous successful payments")
    if not factors:
        factors = ["supplied recovery context"]

    return {
        "diagnosis": {
            "failure_category": category.value,
            "failure_severity": severity.value,
            "recoverability_assessment": assessment.value,
            "key_context_factors": factors[:8],
        },
        "strategy": {
            "recommended_action": action.value,
            "rationale": rationale,
            "confidence": round(confidence, 4),
            "timing": timing.value,
            "alternative_action": alternative.value if alternative else None,
            "concerns": concerns,
        },
    }


def _category(context: RecoveryAgentContext) -> FailureCategory:
    if context.failure is None:
        return FailureCategory.OTHER
    try:
        return FailureCategory(context.failure.failure_category)
    except ValueError:
        return FailureCategory.OTHER
