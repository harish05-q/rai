import json

import httpx
import pytest

from app.agents.exceptions import InvalidModelOutputError, ProviderUnavailableError
from app.agents.providers.factory import UnavailableLLMProvider, get_llm_provider
from app.agents.providers.mock import MockLLMProvider
from app.agents.providers.openai_compatible import OpenAICompatibleProvider
from app.agents.schemas import LLMStructuredOutput, RecoveryAgentContext
from app.core.config import Settings
from app.models.enums import FailureCategory, SuggestedAction
from app.recovery.service import RecoveryAnalysisService
from tests.helpers import make_session, seed_failed_payment


def _context(**kwargs) -> RecoveryAgentContext:
    session = make_session()
    payment = seed_failed_payment(session, **kwargs)
    RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    session.refresh(payment)
    from app.agents.context import build_recovery_context

    context = build_recovery_context(payment.recovery_case)
    session.close()
    return context


def test_mock_provider_is_deterministic() -> None:
    context = _context()
    first = MockLLMProvider().generate(context)
    second = MockLLMProvider().generate(context)
    assert first == second
    assert first.strategy.recommended_action == SuggestedAction.SMART_RETRY


def test_mock_provider_uses_failure_category() -> None:
    context = _context(category=FailureCategory.INSUFFICIENT_FUNDS)
    result = MockLLMProvider().generate(context)
    assert result.strategy.recommended_action == SuggestedAction.WAIT
    assert result.diagnosis.failure_category == FailureCategory.INSUFFICIENT_FUNDS


def test_factory_defaults_to_mock() -> None:
    provider = get_llm_provider(Settings(ai_mode="mock", llm_provider="openai", llm_api_key="secret"))
    assert isinstance(provider, MockLLMProvider)


def test_factory_live_without_key_is_unavailable() -> None:
    provider = get_llm_provider(Settings(ai_mode="live", llm_provider="openai", llm_api_key="", llm_model="gpt-4o-mini"))
    assert isinstance(provider, UnavailableLLMProvider)
    with pytest.raises(ProviderUnavailableError):
        provider.generate(_context())


def test_openai_provider_malformed_response(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        base_url="https://example.invalid/v1",
        timeout_seconds=1,
    )

    def fake_post(*_args, **_kwargs):
        return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(InvalidModelOutputError):
        provider.generate(_context())


def test_openai_provider_validates_structured_json(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        base_url="https://example.invalid/v1",
        timeout_seconds=1,
    )
    payload = {
        "diagnosis": {
            "failure_category": "temporary_timeout",
            "failure_severity": "low",
            "recoverability_assessment": "high",
            "key_context_factors": ["timeout"],
        },
        "strategy": {
            "recommended_action": "smart_retry",
            "rationale": "Temporary timeout is often recoverable.",
            "confidence": 0.8,
            "timing": "immediate",
            "alternative_action": "wait",
            "concerns": [],
        },
    }

    def fake_post(*_args, **_kwargs):
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(payload)}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    result = provider.generate(_context())
    assert isinstance(result, LLMStructuredOutput)
    assert result.strategy.recommended_action == SuggestedAction.SMART_RETRY


def test_openai_provider_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        base_url="https://example.invalid/v1",
        timeout_seconds=1,
    )

    def fake_post(*_args, **_kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(ProviderUnavailableError):
        provider.generate(_context())
