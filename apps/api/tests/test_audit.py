from sqlalchemy import select

from app.actions.executor import ActionExecutor
from app.agents.orchestrator import AgentOrchestrator
from app.models.audit_log import AuditLog
from app.payment_providers.mock import MockPaymentProvider
from app.policies.service import get_or_create_merchant_policy
from app.recovery.service import RecoveryAnalysisService
from tests.helpers import make_session, seed_failed_payment


def test_audit_records_recommendation_policy_and_provider() -> None:
    session = make_session()
    payment = seed_failed_payment(session, email="audit@example.invalid")
    RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    session.refresh(payment)
    case = payment.recovery_case
    AgentOrchestrator(session).analyze_case(case.id)
    policy = get_or_create_merchant_policy(session, payment.merchant_id)
    policy.autonomous_execution = True
    policy.require_approval_for_uncertain = False
    session.commit()

    ActionExecutor(session, provider=MockPaymentProvider()).execute(case.id)
    rows = list(session.scalars(select(AuditLog).order_by(AuditLog.created_at.asc())).all())
    sources = [row.source for row in rows]
    assert "recommendation" in sources
    assert "policy" in sources
    assert "provider" in sources
    assert any(row.status == "succeeded" for row in rows)
    assert all("secret" not in (row.reason or "").lower() for row in rows)


def test_audit_records_approval_transition() -> None:
    session = make_session()
    payment = seed_failed_payment(session, email="audit-appr@example.invalid", amount=__import__("decimal").Decimal("75000.00"))
    RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    session.refresh(payment)
    case = payment.recovery_case
    AgentOrchestrator(session).analyze_case(case.id)
    policy = get_or_create_merchant_policy(session, payment.merchant_id)
    policy.autonomous_execution = True
    policy.require_approval_for_uncertain = False
    session.commit()
    executor = ActionExecutor(session, provider=MockPaymentProvider())
    pending = executor.execute(case.id)
    executor.approve(pending["approval_id"], note="Approved for demo")
    statuses = [row.status for row in session.scalars(select(AuditLog)).all()]
    assert "pending" in statuses
    assert "approved" in statuses
    assert "succeeded" in statuses
