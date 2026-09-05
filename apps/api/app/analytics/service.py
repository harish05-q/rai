from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.evaluation.service import EvaluationService
from app.models.action_execution import ActionExecution
from app.models.approval_request import ApprovalRequest
from app.models.enums import ApprovalStatus, ExecutionStatus, OutcomeStatus, RecoveryCaseStatus, RecoveryEligibility
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase
from app.models.recovery_outcome import RecoveryOutcome
from app.payment_providers.factory import get_payment_provider
from app.recovery.service import RecoveryAnalysisService


class AnalyticsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def overview(self) -> dict:
        recovery = RecoveryAnalysisService(self.session).summary()
        recovered_from_outcomes = self._paid_amount()
        recovered_cases = self.session.scalar(
            select(func.count(RecoveryCase.id)).where(RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
        ) or 0
        at_risk = Decimal(str(recovery["revenue_at_risk"]))
        recovered = recovered_from_outcomes
        eligible = int(recovery["recoverable_payments"])
        pending_approvals = self.session.scalar(
            select(func.count(ApprovalRequest.id)).where(ApprovalRequest.status == ApprovalStatus.PENDING.value)
        ) or 0
        succeeded = self.session.scalar(
            select(func.count(ActionExecution.id)).where(ActionExecution.status == ExecutionStatus.SUCCEEDED.value)
        ) or 0
        return {
            "generated_at": _now(),
            "data_source": "database",
            "synthetic": False,
            "payments_at_risk": int(recovery["total_failed_payments"]),
            "recoverable_cases": eligible,
            "revenue_at_risk": _money(at_risk),
            "recovered_revenue": _money(recovered),
            "recovered_cases": int(recovered_cases),
            "recovery_rate": _safe_div(recovered, at_risk + recovered),
            "successful_actions": int(succeeded),
            "approvals_pending": int(pending_approvals),
            "open_recovery_cases": int(recovery["open_recovery_cases"]),
        }

    def recovery(self) -> dict:
        cases = self.session.scalars(select(RecoveryCase)).all()
        funnel = {
            "open": 0,
            "recommended": 0,
            "blocked": 0,
            "approved": 0,
            "executing": 0,
            "executed": 0,
            "pending": 0,
            "recovered": 0,
            "failed": 0,
            "expired": 0,
            "cancelled": 0,
        }
        for case in cases:
            key = case.lifecycle_status or case.status
            if key in funnel:
                funnel[key] += 1
            elif case.status == RecoveryCaseStatus.RECOVERED.value:
                funnel["recovered"] += 1
            elif case.status == RecoveryCaseStatus.BLOCKED.value:
                funnel["blocked"] += 1
            else:
                funnel["open"] += 1
        recent = self.session.scalars(
            select(RecoveryCase)
            .where(RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
            .options(selectinload(RecoveryCase.payment).selectinload(Payment.customer))
            .order_by(RecoveryCase.resolved_at.desc().nullslast(), RecoveryCase.updated_at.desc())
            .limit(10)
        ).all()
        return {
            "generated_at": _now(),
            "data_source": "database",
            "synthetic": False,
            "funnel": funnel,
            "recent_recovered": [
                {
                    "id": str(case.id),
                    "external_payment_id": case.payment.external_payment_id,
                    "customer_name": case.payment.customer.name if case.payment.customer else None,
                    "recovered_amount": _money(case.recovered_amount or Decimal("0")),
                    "outcome_status": case.latest_outcome_status,
                    "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
                }
                for case in recent
            ],
        }

    def actions(self) -> dict:
        items = self.session.scalars(select(ActionExecution)).all()
        by_status = Counter(item.status for item in items)
        by_workflow = Counter(item.workflow for item in items)
        by_action = Counter(item.action for item in items)
        succeeded = [item for item in items if item.status == ExecutionStatus.SUCCEEDED.value]
        failed = [item for item in items if item.status == ExecutionStatus.FAILED.value]
        blocked = [item for item in items if item.status == ExecutionStatus.BLOCKED.value]
        attempted = len(succeeded) + len(failed)
        return {
            "generated_at": _now(),
            "data_source": "database",
            "synthetic": False,
            "provider": get_payment_provider().name,
            "total": len(items),
            "by_status": dict(by_status),
            "by_workflow": dict(by_workflow),
            "by_action": dict(by_action),
            "execution_success_rate": _safe_div(len(succeeded), attempted),
            "policy_block_rate": _safe_div(len(blocked), len(items)),
        }

    def outcomes(self) -> dict:
        items = self.session.scalars(select(RecoveryOutcome)).all()
        by_status = Counter(item.outcome_status for item in items)
        paid = [item for item in items if item.outcome_status == OutcomeStatus.PAID.value]
        return {
            "generated_at": _now(),
            "data_source": "database",
            "synthetic": False,
            "total": len(items),
            "by_status": dict(by_status),
            "amount_recovered": _money(_sum_decimal(item.amount_recovered for item in paid)),
            "latest": [
                {
                    "id": str(item.id),
                    "recovery_case_id": str(item.recovery_case_id),
                    "outcome_status": item.outcome_status,
                    "provider": item.provider,
                    "provider_reference": item.provider_reference,
                    "amount_recovered": _money(item.amount_recovered) if item.amount_recovered is not None else None,
                    "observed_at": item.observed_at.isoformat(),
                    "source": item.source,
                }
                for item in sorted(items, key=lambda row: row.observed_at, reverse=True)[:15]
            ],
        }

    def evaluation(self, *, persist: bool = False) -> dict:
        return EvaluationService(self.session).run(persist=persist)

    def _paid_amount(self) -> Decimal:
        paid = self.session.scalars(
            select(RecoveryOutcome).where(RecoveryOutcome.outcome_status == OutcomeStatus.PAID.value)
        ).all()
        return _sum_decimal(item.amount_recovered for item in paid)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _money(value: Decimal | None) -> str:
    if value is None:
        return "0.00"
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


def _sum_decimal(values) -> Decimal:
    total = Decimal("0.00")
    for value in values:
        if value is None:
            continue
        total += Decimal(str(value))
    return total


def _safe_div(numerator, denominator) -> float | None:
    if not denominator:
        return None
    return float(Decimal(str(numerator)) / Decimal(str(denominator)))
