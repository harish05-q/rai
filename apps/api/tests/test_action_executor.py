from decimal import Decimal

from app.actions.executor import ActionExecutor
from app.agents.orchestrator import AgentOrchestrator
from app.models.enums import ExecutionStatus, PolicyOutcome
from app.payment_providers.mock import MockPaymentProvider
from app.policies.service import get_or_create_merchant_policy
from app.recovery.service import RecoveryAnalysisService
from tests.helpers import make_session, seed_failed_payment


def _prepare(session, **seed_kwargs):
    payment = seed_failed_payment(session, **seed_kwargs)
    RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    session.refresh(payment)
    case = payment.recovery_case
    AgentOrchestrator(session).analyze_case(case.id)
    policy = get_or_create_merchant_policy(session, payment.merchant_id)
    policy.autonomous_execution = True
    policy.require_approval_for_uncertain = False
    session.commit()
    return session, payment, case, policy


def test_allowed_execution_succeeds() -> None:
    session, payment, case, _policy = _prepare(session=make_session(), email="exec-allow@example.invalid")
    result = ActionExecutor(session, provider=MockPaymentProvider()).execute(case.id)
    assert result["policy_decision"] == PolicyOutcome.ALLOW.value
    assert result["execution_status"] == ExecutionStatus.SUCCEEDED.value
    assert result["provider"] == "mock"
    assert result["provider_reference"]
    assert result["payment_link"]
    assert result["recommendation_only"] is False


def test_blocked_execution() -> None:
    session, payment, case, policy = _prepare(session=make_session(), email="exec-block@example.invalid")
    policy.payment_link_creation_allowed = False
    session.commit()
    result = ActionExecutor(session, provider=MockPaymentProvider()).execute(case.id)
    assert result["policy_decision"] == PolicyOutcome.BLOCK.value
    assert result["execution_status"] == ExecutionStatus.BLOCKED.value
    assert result["recommendation_only"] is True


def test_approval_path() -> None:
    session, payment, case, policy = _prepare(
        session=make_session(),
        email="exec-approve@example.invalid",
        amount=Decimal("75000.00"),
    )
    result = ActionExecutor(session, provider=MockPaymentProvider()).execute(case.id)
    assert result["policy_decision"] == PolicyOutcome.REQUIRE_APPROVAL.value
    assert result["execution_status"] == ExecutionStatus.PENDING_APPROVAL.value
    assert result["approval_id"]
    assert result["payment_link"] is None


def test_successful_execution_after_approval() -> None:
    session, payment, case, policy = _prepare(
        session=make_session(),
        email="exec-after@example.invalid",
        amount=Decimal("75000.00"),
    )
    executor = ActionExecutor(session, provider=MockPaymentProvider())
    pending = executor.execute(case.id)
    approved = executor.approve(pending["approval_id"])
    assert approved["execution_status"] == ExecutionStatus.SUCCEEDED.value
    assert approved["provider_reference"]


def test_failed_execution() -> None:
    session, payment, case, _policy = _prepare(session=make_session(), email="exec-fail@example.invalid")
    result = ActionExecutor(session, provider=MockPaymentProvider(force_error=True)).execute(case.id)
    assert result["execution_status"] == ExecutionStatus.FAILED.value
    assert result["provider_reference"] is None


def test_idempotent_rerun() -> None:
    session, payment, case, _policy = _prepare(session=make_session(), email="exec-dup@example.invalid")
    executor = ActionExecutor(session, provider=MockPaymentProvider())
    first = executor.execute(case.id)
    second = executor.execute(case.id)
    assert first["execution_status"] == ExecutionStatus.SUCCEEDED.value
    assert second["execution_status"] == ExecutionStatus.DUPLICATE.value
    assert second["execution_id"] == first["execution_id"]
    assert second["provider_reference"] == first["provider_reference"]
