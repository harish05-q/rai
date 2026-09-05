from uuid import uuid4

import pytest

from app.agents.exceptions import CaseNotFoundError, ProviderUnavailableError
from app.agents.orchestrator import AgentOrchestrator
from app.agents.providers.factory import UnavailableLLMProvider
from app.models.enums import ComparisonStatus, FailureCategory, SuggestedAction
from app.recovery.service import RecoveryAnalysisService
from tests.helpers import make_session, seed_failed_payment


def test_orchestrator_analyzes_and_compares_baseline() -> None:
    session = make_session()
    payment = seed_failed_payment(session)
    RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    session.refresh(payment)

    decision = AgentOrchestrator(session).analyze_case(payment.recovery_case.id)
    assert decision.recommendation_only is True
    assert decision.baseline_action == SuggestedAction.SMART_RETRY
    assert decision.strategy.recommended_action == SuggestedAction.SMART_RETRY
    assert decision.comparison.status == ComparisonStatus.ALIGNED
    assert decision.ai_mode == "mock"
    session.close()


def test_orchestrator_records_disagreement_for_declined_card() -> None:
    session = make_session()
    payment = seed_failed_payment(session, category=FailureCategory.DECLINED, successful_payments=10)
    RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    session.refresh(payment)

    decision = AgentOrchestrator(session).analyze_case(payment.recovery_case.id)
    assert decision.baseline_action == SuggestedAction.SMART_RETRY
    assert decision.strategy.recommended_action == SuggestedAction.ALTERNATE_PAYMENT_METHOD
    assert decision.comparison.status == ComparisonStatus.DIFFERS
    assert "better" not in decision.comparison.reason.lower()
    session.close()


def test_orchestrator_preserves_history_on_rerun() -> None:
    session = make_session()
    payment = seed_failed_payment(session)
    RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    session.refresh(payment)
    orchestrator = AgentOrchestrator(session)
    first = orchestrator.analyze_case(payment.recovery_case.id)
    second = orchestrator.analyze_case(payment.recovery_case.id)
    assert first.id != second.id
    payload = orchestrator.get_case_analysis(payment.recovery_case.id)
    assert payload.history_count == 2
    assert payload.analysis is not None
    assert payload.analysis.id == second.id
    session.close()


def test_orchestrator_missing_case() -> None:
    session = make_session()
    with pytest.raises(CaseNotFoundError):
        AgentOrchestrator(session).analyze_case(uuid4())
    session.close()


def test_orchestrator_provider_failure() -> None:
    session = make_session()
    payment = seed_failed_payment(session)
    RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    session.refresh(payment)
    orchestrator = AgentOrchestrator(
        session,
        provider=UnavailableLLMProvider("LLM provider is unavailable"),
    )
    with pytest.raises(ProviderUnavailableError):
        orchestrator.analyze_case(payment.recovery_case.id)
    session.close()
