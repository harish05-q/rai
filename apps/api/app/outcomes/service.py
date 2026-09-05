from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit.service import AuditService
from app.models.action_execution import ActionExecution
from app.models.enums import (
    AuditActor,
    ExecutionStatus,
    OutcomeSource,
    OutcomeStatus,
    RecoveryCaseStatus,
    RecoveryLifecycle,
    RecoveryWorkflow,
)
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase
from app.models.recovery_outcome import RecoveryOutcome
from app.outcomes.normalize import amount_recovered_for_status, normalize_provider_status, outcome_fingerprint
from app.payment_providers.factory import get_payment_provider
from app.payment_providers.types import ProviderResult


class OutcomeError(Exception):
    code = "outcome_error"
    status_code = 400

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class OutcomeService:
    def __init__(self, session: Session, provider=None) -> None:
        self.session = session
        self.provider = provider or get_payment_provider()
        self.audit = AuditService(session)

    def record(
        self,
        *,
        recovery_case_id: UUID,
        outcome_status: OutcomeStatus | str,
        provider: str,
        workflow: str,
        source: OutcomeSource | str,
        action_execution_id: UUID | None = None,
        provider_reference: str | None = None,
        amount_attempted: Decimal | None = None,
        currency: str = "INR",
        extra: dict | None = None,
        commit: bool = False,
    ) -> tuple[RecoveryOutcome, bool]:
        status = OutcomeStatus(outcome_status) if not isinstance(outcome_status, OutcomeStatus) else outcome_status
        source_value = source.value if isinstance(source, OutcomeSource) else source
        fingerprint = outcome_fingerprint(
            provider=provider,
            provider_reference=provider_reference,
            outcome_status=status.value,
            action_execution_id=str(action_execution_id) if action_execution_id else None,
        )
        existing = self.session.scalar(select(RecoveryOutcome).where(RecoveryOutcome.fingerprint == fingerprint))
        if existing is not None:
            return existing, False

        recovered = amount_recovered_for_status(status, amount_attempted)
        outcome = RecoveryOutcome(
            recovery_case_id=recovery_case_id,
            action_execution_id=action_execution_id,
            provider=provider,
            provider_reference=provider_reference,
            workflow=workflow,
            outcome_status=status.value,
            amount_attempted=amount_attempted,
            amount_recovered=recovered if isinstance(recovered, Decimal) else None,
            currency=currency,
            observed_at=datetime.now(timezone.utc),
            source=source_value,
            fingerprint=fingerprint,
            extra=extra or {},
        )
        self.session.add(outcome)
        self.session.flush()
        self._apply_to_case(outcome)
        self.audit.record(
            actor=AuditActor.SYSTEM if provider != "razorpay" else AuditActor.RAZORPAY,
            source="outcome",
            status=status.value,
            reason=self._audit_reason(status, recovered if isinstance(recovered, Decimal) else None),
            recovery_case_id=recovery_case_id,
            action_execution_id=action_execution_id,
            provider=provider,
            provider_reference=provider_reference,
            details={
                "workflow": workflow,
                "amount_recovered": str(recovered) if recovered is not None else None,
                "source": source_value,
                "created": True,
            },
        )
        if commit:
            self.session.commit()
            self.session.refresh(outcome)
        return outcome, True

    def record_from_provider_result(
        self,
        *,
        case: RecoveryCase,
        execution: ActionExecution | None,
        result: ProviderResult,
        source: OutcomeSource,
        commit: bool = False,
    ) -> tuple[RecoveryOutcome, bool]:
        amount = case.payment.amount if case.payment else case.revenue_at_risk
        return self.record(
            recovery_case_id=case.id,
            outcome_status=normalize_provider_status(result.status),
            provider=result.provider,
            workflow=execution.workflow if execution else RecoveryWorkflow.PAYMENT_LINK.value,
            source=source,
            action_execution_id=execution.id if execution else None,
            provider_reference=result.provider_reference,
            amount_attempted=amount,
            currency=case.payment.currency if case.payment else "INR",
            extra={"operation": result.operation, "mock": result.mock, "message": result.message},
            commit=commit,
        )

    def observe_execution(self, execution_id: UUID, *, simulate: bool = False, commit: bool = True) -> RecoveryOutcome:
        execution = self.session.get(ActionExecution, execution_id)
        if execution is None:
            raise OutcomeError("Action execution was not found", code="execution_not_found", status_code=404)
        case = self._load_case(execution.recovery_case_id)
        if execution.workflow != RecoveryWorkflow.PAYMENT_LINK.value:
            outcome, _ = self.record(
                recovery_case_id=case.id,
                outcome_status=OutcomeStatus.PENDING,
                provider=execution.provider,
                workflow=execution.workflow,
                source=OutcomeSource.PROVIDER_OBSERVATION,
                action_execution_id=execution.id,
                provider_reference=execution.provider_reference,
                amount_attempted=case.payment.amount if case.payment else case.revenue_at_risk,
                currency=case.payment.currency if case.payment else "INR",
                extra={"note": "Non-Payment-Link workflows are recorded as pending observation."},
                commit=commit,
            )
            return outcome
        if not execution.provider_reference:
            raise OutcomeError("Execution has no provider reference to observe", code="missing_provider_reference")
        if simulate and not getattr(self.provider, "mock", False):
            raise OutcomeError(
                "Outcome simulation is only available on the mock provider",
                code="simulation_not_available",
                status_code=409,
            )
        if simulate:
            result = self.provider.simulate_payment_link_outcome(execution.provider_reference)
            source = OutcomeSource.MOCK_SIMULATION
        elif hasattr(self.provider, "observe_payment_link"):
            result = self.provider.observe_payment_link(execution.provider_reference)
            source = OutcomeSource.MOCK_SIMULATION if result.mock else OutcomeSource.PROVIDER_OBSERVATION
        else:
            raise OutcomeError("Provider does not support Payment Link observation", code="observation_unsupported")
        outcome, _ = self.record_from_provider_result(
            case=case,
            execution=execution,
            result=result,
            source=source,
            commit=commit,
        )
        return outcome

    def observe_case(self, case_id: UUID, *, simulate: bool = False, until_terminal: bool = False) -> RecoveryOutcome | None:
        case = self._load_case(case_id)
        execution = self.session.scalar(
            select(ActionExecution)
            .where(
                ActionExecution.recovery_case_id == case.id,
                ActionExecution.status == ExecutionStatus.SUCCEEDED.value,
                ActionExecution.workflow == RecoveryWorkflow.PAYMENT_LINK.value,
            )
            .order_by(ActionExecution.created_at.desc())
            .limit(1)
        )
        if execution is None:
            raise OutcomeError("No succeeded Payment Link execution to observe", code="no_observable_execution", status_code=409)
        if until_terminal:
            last: RecoveryOutcome | None = None
            for _ in range(8):
                last = self.observe_execution(execution.id, simulate=simulate or getattr(self.provider, "mock", False), commit=True)
                if last.outcome_status in {
                    OutcomeStatus.PAID.value,
                    OutcomeStatus.EXPIRED.value,
                    OutcomeStatus.CANCELLED.value,
                    OutcomeStatus.FAILED.value,
                }:
                    return last
            return last
        return self.observe_execution(
            execution.id,
            simulate=simulate or getattr(self.provider, "mock", False),
            commit=True,
        )

    def latest_for_case(self, case_id: UUID) -> RecoveryOutcome | None:
        return self.session.scalar(
            select(RecoveryOutcome)
            .where(RecoveryOutcome.recovery_case_id == case_id)
            .order_by(RecoveryOutcome.observed_at.desc())
            .limit(1)
        )

    def ingest_verified_provider_state(
        self,
        *,
        recovery_case_id: UUID,
        provider: str,
        provider_reference: str,
        raw_status: str,
        workflow: str,
        amount_attempted: Decimal | None,
        currency: str,
        extra: dict | None = None,
    ) -> tuple[RecoveryOutcome, bool]:
        """Entry point for a future verified Razorpay webhook/event adapter.

        This method does not parse undocumented event names. Callers must first
        verify the webhook using Razorpay's documented signature process, then
        pass a normalized Payment Link status from a documented fetch or payload.
        """

        return self.record(
            recovery_case_id=recovery_case_id,
            outcome_status=normalize_provider_status(raw_status),
            provider=provider,
            workflow=workflow,
            source=OutcomeSource.PROVIDER_OBSERVATION,
            provider_reference=provider_reference,
            amount_attempted=amount_attempted,
            currency=currency,
            extra=extra or {"ingestion": "verified_provider_state"},
            commit=True,
        )

    def _apply_to_case(self, outcome: RecoveryOutcome) -> None:
        case = self.session.get(RecoveryCase, outcome.recovery_case_id)
        if case is None:
            return
        case.latest_outcome_status = outcome.outcome_status
        case.updated_at = datetime.now(timezone.utc)
        status = OutcomeStatus(outcome.outcome_status)
        if status == OutcomeStatus.PAID:
            recovered = outcome.amount_recovered if outcome.amount_recovered is not None else outcome.amount_attempted
            case.status = RecoveryCaseStatus.RECOVERED.value
            case.lifecycle_status = RecoveryLifecycle.RECOVERED.value
            case.recovered_amount = recovered
            case.resolved_at = outcome.observed_at
            return
        if case.lifecycle_status == RecoveryLifecycle.RECOVERED.value:
            return
        if status == OutcomeStatus.EXPIRED:
            case.lifecycle_status = RecoveryLifecycle.EXPIRED.value
            return
        if status == OutcomeStatus.CANCELLED:
            case.lifecycle_status = RecoveryLifecycle.CANCELLED.value
            return
        if status == OutcomeStatus.FAILED:
            case.lifecycle_status = RecoveryLifecycle.FAILED.value
            return
        if status in {OutcomeStatus.CREATED, OutcomeStatus.SENT, OutcomeStatus.OPENED, OutcomeStatus.PENDING}:
            if case.lifecycle_status == RecoveryLifecycle.EXECUTED.value:
                case.lifecycle_status = RecoveryLifecycle.PENDING.value

    def _load_case(self, case_id: UUID) -> RecoveryCase:
        case = self.session.scalar(
            select(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .options(selectinload(RecoveryCase.payment).selectinload(Payment.customer))
        )
        if case is None:
            raise OutcomeError("Recovery case was not found", code="case_not_found", status_code=404)
        return case

    def _audit_reason(self, status: OutcomeStatus, recovered: Decimal | None) -> str:
        if status == OutcomeStatus.PAID:
            amount = f" {recovered}" if recovered is not None else ""
            return f"Observed paid outcome. Recovered amount{amount} recorded. Execution success is not claimed as recovery until this observation."
        return f"Observed provider outcome status {status.value}."
