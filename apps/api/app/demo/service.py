from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.actions.executor import ActionError, ActionExecutor
from app.agents.orchestrator import AgentOrchestrator
from app.models.action_execution import ActionExecution
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.enums import ExecutionStatus, OutcomeStatus, PolicyOutcome, RecoveryEligibility, RecoveryWorkflow
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase
from app.outcomes.service import OutcomeService
from app.payment_providers.mock import MockPaymentProvider
from app.policies.service import get_or_create_merchant_policy
from app.recovery.service import RecoveryAnalysisService


class DemoError(Exception):
    code = "demo_error"
    status_code = 400

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class DemoService:
    """Deterministic mock-only recovery journey. Never uses live Razorpay credentials."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.provider = MockPaymentProvider(force_paid=True)

    def run(self) -> dict:
        steps: list[dict] = []
        case = self._select_case()
        payment = case.payment
        steps.append(
            {
                "stage": "failed_payment",
                "label": "Failed payment selected",
                "detail": f"{payment.external_payment_id} · {payment.amount} {payment.currency}",
            }
        )

        RecoveryAnalysisService(self.session).analyze_failed_payments(payment_id=payment.id)
        self.session.refresh(case)
        steps.append(
            {
                "stage": "diagnosed",
                "label": "Baseline diagnosis",
                "detail": f"{case.suggested_action} · score {case.recoverability_score}",
            }
        )

        analysis = AgentOrchestrator(self.session).analyze_case(case.id)
        steps.append(
            {
                "stage": "recommended",
                "label": "R.AI recommendation",
                "detail": f"{analysis.strategy.recommended_action.value} · confidence {analysis.ai_confidence}",
            }
        )

        policy = get_or_create_merchant_policy(self.session, case.merchant_id)
        policy.autonomous_execution = True
        policy.require_approval_for_uncertain = False
        policy.require_approval_for_high_value = True
        if payment.amount > policy.max_autonomous_action_amount:
            policy.max_autonomous_action_amount = payment.amount
        self.session.commit()

        executor = ActionExecutor(self.session, provider=self.provider)
        preview = executor.preview(case.id)
        steps.append(
            {
                "stage": "policy_checked",
                "label": "Policy decision",
                "detail": f"{preview['policy_decision']} · {preview['workflow']}",
            }
        )
        if preview["policy_decision"] == PolicyOutcome.BLOCK.value:
            raise DemoError("Selected demo case is blocked by policy", code="demo_blocked", status_code=409)

        if preview["policy_decision"] == PolicyOutcome.REQUIRE_APPROVAL.value:
            pending = executor.execute(case.id)
            if not pending.get("approval_id"):
                raise DemoError("Approval was required but not created", code="demo_approval_missing")
            executed = executor.approve(pending["approval_id"], note="Demo operator approval (mock only).")
        else:
            executed = executor.execute(case.id)

        steps.append(
            {
                "stage": "executed",
                "label": "Action executed",
                "detail": f"{executed['execution_status']} · {executed.get('provider_reference')}",
            }
        )

        outcomes = OutcomeService(self.session, provider=self.provider)
        observed = None
        if executed.get("execution_id") and executed.get("workflow") == RecoveryWorkflow.PAYMENT_LINK.value:
            observed = outcomes.observe_case(case.id, simulate=True, until_terminal=True)
            steps.append(
                {
                    "stage": "observed",
                    "label": "Provider outcome observed",
                    "detail": f"{observed.outcome_status} · {observed.provider_reference}",
                }
            )
        else:
            steps.append(
                {
                    "stage": "observed",
                    "label": "No Payment Link to observe",
                    "detail": executed.get("reason") or "Workflow did not create a Payment Link.",
                }
            )

        self.session.refresh(case)
        recovered = case.status == "recovered" and case.latest_outcome_status == OutcomeStatus.PAID.value
        steps.append(
            {
                "stage": "recovered",
                "label": "Revenue recovered" if recovered else "Revenue not recovered",
                "detail": (
                    f"{case.recovered_amount} {payment.currency}"
                    if recovered
                    else "Execution success is not treated as recovered revenue."
                ),
            }
        )

        audit = self.session.scalars(
            select(AuditLog).where(AuditLog.recovery_case_id == case.id).order_by(AuditLog.created_at.asc())
        ).all()
        return {
            "demo": True,
            "mock": True,
            "charges_real_customer": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "Mock/demo only. No live Razorpay charge, notification, or production mutation.",
            "case_id": str(case.id),
            "external_payment_id": payment.external_payment_id,
            "diagnosis": case.suggested_action,
            "recommendation": analysis.strategy.recommended_action.value,
            "confidence": analysis.ai_confidence,
            "policy_decision": preview["policy_decision"],
            "execution_status": executed.get("execution_status"),
            "workflow": executed.get("workflow"),
            "provider": executed.get("provider"),
            "provider_reference": executed.get("provider_reference"),
            "payment_link": executed.get("payment_link"),
            "outcome_status": observed.outcome_status if observed else case.latest_outcome_status,
            "recovered": recovered,
            "recovered_amount": str(case.recovered_amount) if case.recovered_amount is not None else None,
            "steps": steps,
            "audit": [
                {
                    "id": str(item.id),
                    "source": item.source,
                    "status": item.status,
                    "reason": item.reason,
                    "provider_reference": item.provider_reference,
                    "created_at": item.created_at.isoformat(),
                }
                for item in audit
            ],
        }

    def _select_case(self) -> RecoveryCase:
        cases = self.session.scalars(
            select(RecoveryCase)
            .where(
                RecoveryCase.status == "open",
                RecoveryCase.eligibility == RecoveryEligibility.ELIGIBLE.value,
            )
            .options(
                selectinload(RecoveryCase.payment).selectinload(Payment.customer).selectinload(Customer.subscriptions),
                selectinload(RecoveryCase.payment).selectinload(Payment.failures),
                selectinload(RecoveryCase.action_executions),
            )
            .order_by(RecoveryCase.revenue_at_risk.asc(), RecoveryCase.created_at.asc())
        ).unique().all()
        for case in cases:
            if case.payment.amount > Decimal("50000.00"):
                continue
            if any(item.status == ExecutionStatus.SUCCEEDED.value for item in case.action_executions):
                continue
            if case.suggested_action in {"smart_retry", "payment_reminder", "alternate_payment_method"}:
                subscriptions = case.payment.customer.subscriptions if case.payment.customer else []
                if subscriptions and case.suggested_action == "smart_retry":
                    continue
                return case
        if cases:
            return cases[0]
        raise DemoError(
            "No eligible open recovery case is available for the mock demo. Seed data first.",
            code="demo_no_case",
            status_code=409,
        )
