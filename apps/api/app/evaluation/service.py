from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.evaluation.synthetic import hypothetical_recovered_amount
from app.models.action_execution import ActionExecution
from app.models.customer import Customer
from app.models.enums import ExecutionStatus, OutcomeStatus, PolicyOutcome, RecoveryEligibility
from app.models.evaluation_run import EvaluationRun
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase
from app.models.recovery_outcome import RecoveryOutcome
from app.policies.engine import PolicyEvaluationInput, evaluate_policy
from app.policies.mapping import has_recoverable_subscription
from app.policies.service import get_or_create_merchant_policy, policy_snapshot


LIFT_EXPLANATION = (
    "Recovery Lift is (R.AI recoverable revenue − baseline recoverable revenue) / baseline "
    "recoverable revenue. It is undefined when baseline recoverable revenue is zero. "
    "Hypothetical recovery uses a deterministic synthetic model and is not live settlement."
)


class EvaluationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run(self, *, persist: bool = False, limit: int | None = 200) -> dict:
        cases = self._select_cases(limit=limit)
        rows: list[dict] = []
        for case in cases:
            rows.append(self._evaluate_case(case))

        metrics = self._aggregate(rows)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_source": "synthetic_evaluation_on_stored_cases",
            "synthetic": True,
            "disclaimer": (
                "Evaluation compares baseline vs R.AI on the same cases using a deterministic "
                "synthetic recoverability model. It is not live financial performance."
            ),
            "lift_definition": LIFT_EXPLANATION,
            "metrics": metrics,
            "cases_evaluated": len(rows),
        }
        if persist:
            run = EvaluationRun(
                data_source=payload["data_source"],
                synthetic=True,
                cases_evaluated=len(rows),
                metrics=metrics,
                notes=payload["disclaimer"],
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(run)
            self.session.commit()
            payload["evaluation_run_id"] = str(run.id)
        return payload

    def _select_cases(self, limit: int | None) -> list[RecoveryCase]:
        query = (
            select(RecoveryCase)
            .options(
                selectinload(RecoveryCase.payment).selectinload(Payment.customer).selectinload(Customer.subscriptions),
                selectinload(RecoveryCase.payment).selectinload(Payment.failures),
                selectinload(RecoveryCase.ai_decisions),
            )
            .order_by(RecoveryCase.created_at.asc())
        )
        if limit is not None:
            query = query.limit(limit)
        return list(self.session.scalars(query).unique().all())

    def _evaluate_case(self, case: RecoveryCase) -> dict:
        payment = case.payment
        latest_failure = max(payment.failures, key=lambda item: item.occurred_at) if payment.failures else None
        subscriptions = payment.customer.subscriptions if payment.customer else []
        policy = get_or_create_merchant_policy(self.session, case.merchant_id)
        decision = None
        if case.ai_decisions:
            decision = max(case.ai_decisions, key=lambda item: item.created_at)

        baseline_action = case.suggested_action
        rai_action = decision.recommended_action if decision else baseline_action
        diagnosis = decision.diagnosis if decision and isinstance(decision.diagnosis, dict) else {}

        baseline_policy = evaluate_policy(
            PolicyEvaluationInput(
                action=baseline_action,
                amount=payment.amount,
                attempt_number=payment.attempt_number,
                prior_recovery_attempts=0,
                has_recoverable_subscription=has_recoverable_subscription(list(subscriptions)),
                eligibility=case.eligibility,
                recoverability_assessment=diagnosis.get("recoverability_assessment"),
                confidence=float(decision.confidence) if decision else None,
                concerns=list(decision.concerns or []) if decision else [],
                failure_category=latest_failure.failure_category if latest_failure else None,
                failure_code=latest_failure.failure_code if latest_failure else None,
                policy=policy_snapshot(policy),
            )
        )
        rai_policy = evaluate_policy(
            PolicyEvaluationInput(
                action=rai_action,
                amount=payment.amount,
                attempt_number=payment.attempt_number,
                prior_recovery_attempts=0,
                has_recoverable_subscription=has_recoverable_subscription(list(subscriptions)),
                eligibility=case.eligibility,
                recoverability_assessment=diagnosis.get("recoverability_assessment"),
                confidence=float(decision.confidence) if decision else None,
                concerns=list(decision.concerns or []) if decision else [],
                failure_category=latest_failure.failure_category if latest_failure else None,
                failure_code=latest_failure.failure_code if latest_failure else None,
                policy=policy_snapshot(policy),
            )
        )

        eligible = case.eligibility == RecoveryEligibility.ELIGIBLE.value
        baseline_amount = hypothetical_recovered_amount(
            revenue_at_risk=case.revenue_at_risk,
            recoverability_score=case.recoverability_score,
            action=baseline_action,
            eligibility=case.eligibility,
            policy_decision=baseline_policy.decision.value,
        )
        rai_amount = hypothetical_recovered_amount(
            revenue_at_risk=case.revenue_at_risk,
            recoverability_score=case.recoverability_score,
            action=rai_action,
            eligibility=case.eligibility,
            policy_decision=rai_policy.decision.value,
        )
        return {
            "eligible": eligible,
            "revenue_at_risk": case.revenue_at_risk,
            "baseline_action": baseline_action,
            "rai_action": rai_action,
            "agree": baseline_action == rai_action,
            "baseline_policy": baseline_policy.decision.value,
            "rai_policy": rai_policy.decision.value,
            "baseline_amount": baseline_amount,
            "rai_amount": rai_amount,
        }

    def _aggregate(self, rows: list[dict]) -> dict:
        cases_evaluated = len(rows)
        eligible = sum(1 for row in rows if row["eligible"])
        revenue_at_risk = _sum_decimal(row["revenue_at_risk"] for row in rows if row["eligible"])
        baseline_recoverable = _sum_decimal(row["baseline_amount"] for row in rows)
        rai_recoverable = _sum_decimal(row["rai_amount"] for row in rows)
        baseline_rate = _safe_div(baseline_recoverable, revenue_at_risk)
        rai_rate = _safe_div(rai_recoverable, revenue_at_risk)
        lift = _safe_div(rai_recoverable - baseline_recoverable, baseline_recoverable)
        agreement = _safe_div(sum(1 for row in rows if row["agree"]), cases_evaluated)
        rai_blocks = sum(1 for row in rows if row["rai_policy"] == PolicyOutcome.BLOCK.value)
        rai_approvals = sum(1 for row in rows if row["rai_policy"] == PolicyOutcome.REQUIRE_APPROVAL.value)
        policy_block_rate = _safe_div(rai_blocks, cases_evaluated)
        approval_rate = _safe_div(rai_approvals, cases_evaluated)

        executed = self.session.scalars(
            select(ActionExecution).where(
                ActionExecution.status.in_(
                    [
                        ExecutionStatus.SUCCEEDED.value,
                        ExecutionStatus.FAILED.value,
                    ]
                )
            )
        ).all()
        success_count = sum(1 for item in executed if item.status == ExecutionStatus.SUCCEEDED.value)
        execution_success_rate = _safe_div(success_count, len(executed))
        paid = self.session.scalars(
            select(RecoveryOutcome).where(RecoveryOutcome.outcome_status == OutcomeStatus.PAID.value)
        ).all()
        actual = _sum_decimal(item.amount_recovered or Decimal("0") for item in paid)

        return {
            "cases_evaluated": cases_evaluated,
            "eligible_cases": eligible,
            "revenue_at_risk": _money(revenue_at_risk),
            "baseline_recoverable_revenue": _money(baseline_recoverable),
            "rai_recoverable_revenue": _money(rai_recoverable),
            "baseline_recovery_rate": baseline_rate,
            "rai_recovery_rate": rai_rate,
            "recovery_lift": lift,
            "recovery_lift_amount": _money(rai_recoverable - baseline_recoverable),
            "ai_baseline_agreement": agreement,
            "policy_block_rate": policy_block_rate,
            "approval_rate": approval_rate,
            "execution_success_rate": execution_success_rate,
            "revenue_actually_recovered": _money(actual),
            "revenue_actually_recovered_data_source": "database_outcomes",
        }


def _sum_decimal(values) -> Decimal:
    total = Decimal("0.00")
    for value in values:
        if value is None:
            continue
        total += Decimal(str(value))
    return total


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _safe_div(numerator, denominator) -> float | None:
    if denominator is None:
        return None
    den = Decimal(str(denominator))
    if den == 0:
        return None
    return float(Decimal(str(numerator)) / den)
