from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.actions.fingerprint import execution_fingerprint, payment_link_reference_id
from app.audit.service import AuditService
from app.core.logging import log_event
from app.models.action_execution import ActionExecution
from app.models.ai_decision import AIDecision
from app.models.approval_request import ApprovalRequest
from app.models.customer import Customer
from app.models.enums import (
    ApprovalStatus,
    AuditActor,
    ExecutionStatus,
    OutcomeSource,
    PolicyOutcome,
    RecoveryLifecycle,
    RecoveryWorkflow,
    SuggestedAction,
)
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase
from app.payment_providers.exceptions import PaymentProviderError, ProviderTimeoutError
from app.payment_providers.factory import get_payment_provider
from app.payment_providers.types import PaymentLinkRequest, ProviderResult
from app.policies.constants import APPROVAL_TTL_HOURS
from app.policies.engine import PolicyDecision, PolicyEvaluationInput, evaluate_policy
from app.policies.mapping import has_recoverable_subscription, map_recovery_workflow
from app.policies.service import get_or_create_merchant_policy, policy_snapshot
from app.outcomes.service import OutcomeService

ACTIVE_EXECUTION_STATUSES = {
    ExecutionStatus.SUCCEEDED,
    ExecutionStatus.PENDING_APPROVAL,
    ExecutionStatus.EXECUTING,
    ExecutionStatus.APPROVED,
}

COUNTED_ATTEMPT_STATUSES = {
    ExecutionStatus.SUCCEEDED,
    ExecutionStatus.PENDING_APPROVAL,
    ExecutionStatus.EXECUTING,
    ExecutionStatus.APPROVED,
}


class ActionError(Exception):
    code = "action_error"
    status_code = 400

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class ActionExecutor:
    def __init__(self, session: Session, provider=None) -> None:
        self.session = session
        self.provider = provider or get_payment_provider()
        self.audit = AuditService(session)
        self.outcomes = OutcomeService(session, provider=self.provider)

    def preview(self, case_id: UUID) -> dict:
        case, decision, policy, evaluation = self._prepare(case_id)
        return {
            "case_id": case.id,
            "requested_action": evaluation.action,
            "policy_decision": evaluation.decision.value,
            "reason": evaluation.reason,
            "required_approval": evaluation.required_approval,
            "workflow": evaluation.workflow,
            "policy_version": evaluation.policy_version,
            "limits_checked": evaluation.limits_checked,
            "can_execute": evaluation.decision == PolicyOutcome.ALLOW,
            "can_request_approval": evaluation.decision == PolicyOutcome.REQUIRE_APPROVAL,
            "blocked": evaluation.decision == PolicyOutcome.BLOCK,
            "recommendation_only": evaluation.decision != PolicyOutcome.ALLOW,
            "ai_decision_id": decision.id if decision else None,
        }

    def execute(self, case_id: UUID, *, actor: str = AuditActor.MERCHANT.value) -> dict:
        case, decision, policy, evaluation = self._prepare(case_id)
        payment = case.payment
        fingerprint = execution_fingerprint(
            case_id=case.id,
            action=evaluation.action,
            workflow=evaluation.workflow,
            amount=payment.amount,
            currency=payment.currency,
        )
        log_event(
            "action_execute_requested",
            case_id=case.id,
            action=evaluation.action,
            policy_result=evaluation.decision.value,
        )
        rec_audit = self.audit.record(
            actor=AuditActor.AI,
            source="recommendation",
            status="recorded",
            reason=decision.rationale if decision else "Baseline recommendation used.",
            recovery_case_id=case.id,
            ai_decision_id=decision.id if decision else None,
            requested_action=evaluation.action,
            details={"source": "ai" if decision else "baseline"},
        )
        policy_audit = self.audit.record(
            actor=AuditActor.SYSTEM,
            source="policy",
            status=evaluation.decision.value,
            reason=evaluation.reason,
            recovery_case_id=case.id,
            ai_decision_id=decision.id if decision else None,
            policy_decision=evaluation.decision.value,
            requested_action=evaluation.action,
            details={"workflow": evaluation.workflow, "limits_checked": evaluation.limits_checked},
        )

        duplicate = self._find_duplicate(fingerprint)
        if duplicate is not None:
            dup_audit = self.audit.record(
                actor=AuditActor.SYSTEM,
                source="idempotency",
                status=ExecutionStatus.DUPLICATE.value,
                reason="An active or completed execution already exists for this request fingerprint.",
                recovery_case_id=case.id,
                ai_decision_id=decision.id if decision else None,
                action_execution_id=duplicate.id,
                policy_decision=evaluation.decision.value,
                requested_action=evaluation.action,
                executed_action=duplicate.action,
                provider=duplicate.provider,
                provider_reference=duplicate.provider_reference,
            )
            self.session.commit()
            return self._response(
                case=case,
                evaluation=evaluation,
                execution=duplicate,
                execution_status=ExecutionStatus.DUPLICATE,
                audit_id=dup_audit.id,
                approval_id=duplicate.approval_id,
            )

        if evaluation.decision == PolicyOutcome.BLOCK:
            execution = self._new_execution(
                case=case,
                decision=decision,
                evaluation=evaluation,
                fingerprint=fingerprint,
                status=ExecutionStatus.BLOCKED,
            )
            self.session.flush()
            case.lifecycle_status = RecoveryLifecycle.BLOCKED.value
            blocked_audit = self.audit.record(
                actor=AuditActor.SYSTEM,
                source="policy",
                status=ExecutionStatus.BLOCKED.value,
                reason=evaluation.reason,
                recovery_case_id=case.id,
                ai_decision_id=decision.id if decision else None,
                action_execution_id=execution.id,
                policy_decision=evaluation.decision.value,
                requested_action=evaluation.action,
            )
            self.session.commit()
            self.session.refresh(execution)
            return self._response(
                case=case,
                evaluation=evaluation,
                execution=execution,
                execution_status=ExecutionStatus.BLOCKED,
                audit_id=blocked_audit.id,
            )

        if evaluation.decision == PolicyOutcome.REQUIRE_APPROVAL:
            execution = self._new_execution(
                case=case,
                decision=decision,
                evaluation=evaluation,
                fingerprint=fingerprint,
                status=ExecutionStatus.PENDING_APPROVAL,
            )
            self.session.flush()
            approval = ApprovalRequest(
                recovery_case_id=case.id,
                action_execution_id=execution.id,
                reason=evaluation.reason,
                amount=payment.amount,
                requested_action=evaluation.action,
                status=ApprovalStatus.PENDING.value,
                requested_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=APPROVAL_TTL_HOURS),
            )
            self.session.add(approval)
            self.session.flush()
            execution.approval_id = approval.id
            approval_audit = self.audit.record(
                actor=AuditActor.SYSTEM,
                source="approval",
                status=ApprovalStatus.PENDING.value,
                reason=evaluation.reason,
                recovery_case_id=case.id,
                ai_decision_id=decision.id if decision else None,
                action_execution_id=execution.id,
                approval_id=approval.id,
                policy_decision=evaluation.decision.value,
                requested_action=evaluation.action,
            )
            log_event(
                "approval_requested",
                case_id=case.id,
                execution_id=execution.id,
                action=evaluation.action,
                policy_result=evaluation.decision.value,
            )
            self.session.commit()
            self.session.refresh(execution)
            return self._response(
                case=case,
                evaluation=evaluation,
                execution=execution,
                execution_status=ExecutionStatus.PENDING_APPROVAL,
                audit_id=approval_audit.id,
                approval_id=approval.id,
            )

        execution = self._new_execution(
            case=case,
            decision=decision,
            evaluation=evaluation,
            fingerprint=fingerprint,
            status=ExecutionStatus.EXECUTING,
        )
        self.session.flush()
        return self._run_provider(
            case=case,
            decision=decision,
            evaluation=evaluation,
            execution=execution,
            actor=actor,
        )

    def approve(self, approval_id: UUID, *, resolved_by: str = "merchant-operator", note: str | None = None) -> dict:
        approval = self._load_approval(approval_id)
        self._expire_if_needed(approval)
        if approval.status != ApprovalStatus.PENDING.value:
            raise ActionError("Approval is not pending", code="approval_not_pending", status_code=409)
        execution = self.session.get(ActionExecution, approval.action_execution_id)
        if execution is None:
            raise ActionError("Action execution was not found", code="execution_not_found", status_code=404)
        case = self._load_case(approval.recovery_case_id)
        decision = self._latest_decision(case.id)
        policy = get_or_create_merchant_policy(self.session, case.merchant_id)
        evaluation = self._evaluate(case, decision, policy)

        approval.status = ApprovalStatus.APPROVED.value
        approval.resolved_at = datetime.now(timezone.utc)
        approval.resolved_by = resolved_by
        approval.resolution_note = note
        execution.status = ExecutionStatus.APPROVED.value
        execution.approval_id = approval.id
        approval_audit = self.audit.record(
            actor=AuditActor.MERCHANT,
            source="approval",
            status=ApprovalStatus.APPROVED.value,
            reason=note or "Merchant approved the recovery review.",
            recovery_case_id=case.id,
            ai_decision_id=decision.id if decision else None,
            action_execution_id=execution.id,
            approval_id=approval.id,
            policy_decision=evaluation.decision.value,
            requested_action=execution.action,
            executed_action=None,
        )

        # human_review is a review workflow, not a provider-executable action.
        if evaluation.workflow in {RecoveryWorkflow.NONE.value, RecoveryWorkflow.APPROVAL_CASE.value}:
            execution.completed_at = datetime.now(timezone.utc)
            case.lifecycle_status = RecoveryLifecycle.APPROVED.value
            self.session.commit()
            self.session.refresh(execution)

            return self._response(
                case=case,
                evaluation=evaluation,
                execution=execution,
                execution_status=ExecutionStatus.APPROVED,
                audit_id=approval_audit.id,
                approval_id=approval.id,
                reason="Human review approved; no provider action was executed.",
            )
        execution.status = ExecutionStatus.EXECUTING.value
        return self._run_provider(
            case=case,
            decision=decision,
            evaluation=evaluation,
            execution=execution,
            actor=AuditActor.MERCHANT.value,
        )

    def reject(self, approval_id: UUID, *, resolved_by: str = "merchant-operator", note: str | None = None) -> dict:
        approval = self._load_approval(approval_id)
        self._expire_if_needed(approval)
        if approval.status != ApprovalStatus.PENDING.value:
            raise ActionError("Approval is not pending", code="approval_not_pending", status_code=409)
        execution = self.session.get(ActionExecution, approval.action_execution_id)
        if execution is None:
            raise ActionError("Action execution was not found", code="execution_not_found", status_code=404)
        approval.status = ApprovalStatus.REJECTED.value
        approval.resolved_at = datetime.now(timezone.utc)
        approval.resolved_by = resolved_by
        approval.resolution_note = note
        execution.status = ExecutionStatus.CANCELLED.value
        execution.completed_at = datetime.now(timezone.utc)
        case = self._load_case(approval.recovery_case_id)
        if case.lifecycle_status != RecoveryLifecycle.RECOVERED.value:
            case.lifecycle_status = RecoveryLifecycle.CANCELLED.value
        audit = self.audit.record(
            actor=AuditActor.MERCHANT,
            source="approval",
            status=ApprovalStatus.REJECTED.value,
            reason=note or "Merchant rejected the recovery action.",
            recovery_case_id=approval.recovery_case_id,
            action_execution_id=execution.id,
            approval_id=approval.id,
            requested_action=execution.action,
            executed_action=execution.action,
        )
        self.session.commit()
        case = self._load_case(approval.recovery_case_id)
        decision = PolicyDecision(
            decision=PolicyOutcome.REQUIRE_APPROVAL,
            reason=approval.reason,
            required_approval=True,
            action=execution.action,
            workflow=execution.workflow,
            policy_version="",
            limits_checked=[],
            created_at=datetime.now(timezone.utc),
        )
        return self._response(
            case=case,
            evaluation=decision,
            execution=execution,
            execution_status=ExecutionStatus.CANCELLED,
            audit_id=audit.id,
            approval_id=approval.id,
        )

    def _run_provider(
        self,
        *,
        case: RecoveryCase,
        decision: AIDecision | None,
        evaluation: PolicyDecision,
        execution: ActionExecution,
        actor: str,
    ) -> dict:
        payment = case.payment
        workflow = RecoveryWorkflow(evaluation.workflow)
        provider_name = self.provider.name if workflow != RecoveryWorkflow.NONE else "none"
        execution.provider = provider_name
        result: ProviderResult | None = None
        try:
            if workflow == RecoveryWorkflow.NONE:
                result = ProviderResult(
                    provider="none",
                    mock=True,
                    operation="noop",
                    status="skipped",
                    provider_reference=None,
                    payment_link_url=None,
                    notification_status=None,
                    message="No provider action is required.",
                    occurred_at=datetime.now(timezone.utc),
                )
            elif workflow == RecoveryWorkflow.SUBSCRIPTION_PROVIDER_MANAGED:
                subscriptions = payment.customer.subscriptions if payment.customer else []
                sub_id = subscriptions[0].external_subscription_id if subscriptions else None
                result = self.provider.create_subscription_recovery_workflow(
                    subscription_external_id=sub_id,
                    reference_id=payment_link_reference_id(execution.request_fingerprint),
                    amount_paise=_to_paise(payment.amount),
                    currency=payment.currency,
                )
            elif workflow == RecoveryWorkflow.PAYMENT_LINK:
                result = self._create_payment_link(case, evaluation, execution)
            else:
                raise ActionError("Workflow is not executable", code="unsupported_workflow")

            execution.status = ExecutionStatus.SUCCEEDED.value
            execution.provider_reference = result.provider_reference
            execution.result = result.as_safe_dict()
            execution.completed_at = datetime.now(timezone.utc)
            execution.provider = result.provider
            provider_actor = AuditActor.RAZORPAY if result.provider == "razorpay" else AuditActor.SYSTEM
            self.audit.record(
                actor=AuditActor.SYSTEM,
                source="executor",
                status=ExecutionStatus.EXECUTING.value,
                reason="Policy-approved action sent to payment provider.",
                recovery_case_id=case.id,
                ai_decision_id=decision.id if decision else None,
                action_execution_id=execution.id,
                approval_id=execution.approval_id,
                policy_decision=evaluation.decision.value,
                requested_action=evaluation.action,
                executed_action=evaluation.action,
                provider=result.provider,
            )
            result_audit = self.audit.record(
                actor=provider_actor,
                source="provider",
                status=ExecutionStatus.SUCCEEDED.value,
                reason=result.message,
                recovery_case_id=case.id,
                ai_decision_id=decision.id if decision else None,
                action_execution_id=execution.id,
                approval_id=execution.approval_id,
                policy_decision=evaluation.decision.value,
                requested_action=evaluation.action,
                executed_action=evaluation.action,
                provider=result.provider,
                provider_reference=result.provider_reference,
                details={"mock": result.mock, "operation": result.operation, "status": result.status},
            )
            log_event(
                "action_execute_succeeded",
                case_id=case.id,
                action=evaluation.action,
                execution_id=execution.id,
                provider=result.provider,
                status=execution.status,
                policy_result=evaluation.decision.value,
            )
            self.session.commit()
            self.session.refresh(execution)
            return self._response(
                case=case,
                evaluation=evaluation,
                execution=execution,
                execution_status=ExecutionStatus.SUCCEEDED,
                audit_id=result_audit.id,
                approval_id=execution.approval_id,
                provider_result=result,
            )
        except (PaymentProviderError, ProviderTimeoutError) as exc:
            execution.status = ExecutionStatus.FAILED.value
            execution.completed_at = datetime.now(timezone.utc)
            execution.result = {"error": exc.message, "code": getattr(exc, "code", "provider_error"), "mock": getattr(self.provider, "mock", False)}
            fail_audit = self.audit.record(
                actor=AuditActor.SYSTEM,
                source="provider",
                status=ExecutionStatus.FAILED.value,
                reason=exc.message,
                recovery_case_id=case.id,
                ai_decision_id=decision.id if decision else None,
                action_execution_id=execution.id,
                approval_id=execution.approval_id,
                policy_decision=evaluation.decision.value,
                requested_action=evaluation.action,
                executed_action=evaluation.action,
                provider=getattr(self.provider, "name", "unknown"),
            )
            log_event(
                "action_execute_failed",
                case_id=case.id,
                action=evaluation.action,
                execution_id=execution.id,
                provider=getattr(self.provider, "name", "unknown"),
                status=execution.status,
                policy_result=evaluation.decision.value,
            )
            self.session.commit()
            self.session.refresh(execution)
            return self._response(
                case=case,
                evaluation=evaluation,
                execution=execution,
                execution_status=ExecutionStatus.FAILED,
                audit_id=fail_audit.id,
                approval_id=execution.approval_id,
                reason=exc.message,
            )

    def _create_payment_link(
        self,
        case: RecoveryCase,
        evaluation: PolicyDecision,
        execution: ActionExecution,
    ) -> ProviderResult:
        payment = case.payment
        customer = payment.customer
        policy = get_or_create_merchant_policy(self.session, case.merchant_id)
        methods: tuple[str, ...] = ()
        if evaluation.action == SuggestedAction.ALTERNATE_PAYMENT_METHOD.value:
            methods = ("upi", "netbanking")
        created = self.provider.create_payment_link(
            PaymentLinkRequest(
                amount_paise=_to_paise(payment.amount),
                currency=payment.currency,
                reference_id=payment_link_reference_id(execution.request_fingerprint),
                description=f"R.AI recovery for {payment.external_payment_id}",
                customer_name=customer.name if customer else None,
                customer_email=customer.email if customer else None,
                expire_by=int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp()),
                notify_email=policy.notifications_allowed,
                reminder_enable=policy.notifications_allowed,
                preferred_methods=methods,
                notes={"case_id": str(case.id)},
            )
        )
        if policy.notifications_allowed and created.notification_status in {None, "not_requested"}:
            if created.provider_reference:
                notified = self.provider.send_payment_link_notification(created.provider_reference, "email")
                return ProviderResult(
                    provider=created.provider,
                    mock=created.mock,
                    operation="create_payment_link",
                    status=created.status,
                    provider_reference=created.provider_reference,
                    payment_link_url=created.payment_link_url,
                    notification_status=notified.notification_status,
                    message=created.message,
                    occurred_at=created.occurred_at,
                    details={**created.details, "notification": notified.details},
                )
        return created

    def _prepare(self, case_id: UUID):
        case = self._load_case(case_id)
        decision = self._latest_decision(case.id)
        if decision is None:
            raise ActionError(
                "Analyze the case with R.AI before executing a recovery action",
                code="recommendation_required",
                status_code=409,
            )
        policy = get_or_create_merchant_policy(self.session, case.merchant_id)
        evaluation = self._evaluate(case, decision, policy)
        return case, decision, policy, evaluation

    def _evaluate(self, case: RecoveryCase, decision: AIDecision | None, policy) -> PolicyDecision:
        payment = case.payment
        latest_failure = max(payment.failures, key=lambda item: item.occurred_at) if payment.failures else None
        subscriptions = payment.customer.subscriptions if payment.customer else []
        action = decision.recommended_action if decision else case.suggested_action
        diagnosis = decision.diagnosis if decision and isinstance(decision.diagnosis, dict) else {}
        return evaluate_policy(
            PolicyEvaluationInput(
                action=action,
                amount=payment.amount,
                attempt_number=payment.attempt_number,
                prior_recovery_attempts=self._prior_attempts(case.id),
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

    def _prior_attempts(self, case_id: UUID) -> int:
        count = self.session.scalar(
            select(func.count(ActionExecution.id)).where(
                ActionExecution.recovery_case_id == case_id,
                ActionExecution.status.in_([item.value for item in COUNTED_ATTEMPT_STATUSES]),
                ActionExecution.workflow.in_(
                    [
                        RecoveryWorkflow.PAYMENT_LINK.value,
                        RecoveryWorkflow.SUBSCRIPTION_PROVIDER_MANAGED.value,
                    ]
                ),
            )
        )
        return int(count or 0)

    def _find_duplicate(self, fingerprint: str) -> ActionExecution | None:
        return self.session.scalar(
            select(ActionExecution)
            .where(
                ActionExecution.request_fingerprint == fingerprint,
                ActionExecution.status.in_([item.value for item in ACTIVE_EXECUTION_STATUSES]),
            )
            .order_by(ActionExecution.created_at.desc())
            .limit(1)
        )

    def _new_execution(
        self,
        *,
        case: RecoveryCase,
        decision: AIDecision | None,
        evaluation: PolicyDecision,
        fingerprint: str,
        status: ExecutionStatus,
    ) -> ActionExecution:
        provider_name = "none" if evaluation.workflow == RecoveryWorkflow.NONE.value else self.provider.name
        execution = ActionExecution(
            recovery_case_id=case.id,
            ai_decision_id=decision.id if decision else None,
            action=evaluation.action,
            workflow=evaluation.workflow,
            provider=provider_name,
            request_fingerprint=fingerprint,
            status=status.value,
            policy_decision=evaluation.decision.value,
            result={},
        )
        if status in {ExecutionStatus.BLOCKED, ExecutionStatus.SUCCEEDED}:
            execution.completed_at = datetime.now(timezone.utc)
        self.session.add(execution)
        return execution

    def _load_case(self, case_id: UUID) -> RecoveryCase:
        case = self.session.scalar(
            select(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .options(
                selectinload(RecoveryCase.payment).selectinload(Payment.customer).selectinload(Customer.subscriptions),
                selectinload(RecoveryCase.payment).selectinload(Payment.failures),
            )
        )
        if case is None:
            raise ActionError("Recovery case was not found", code="case_not_found", status_code=404)
        return case

    def _latest_decision(self, case_id: UUID) -> AIDecision | None:
        return self.session.scalar(
            select(AIDecision)
            .where(AIDecision.recovery_case_id == case_id)
            .order_by(AIDecision.created_at.desc())
            .limit(1)
        )

    def _load_approval(self, approval_id: UUID) -> ApprovalRequest:
        approval = self.session.get(ApprovalRequest, approval_id)
        if approval is None:
            raise ActionError("Approval request was not found", code="approval_not_found", status_code=404)
        return approval

    def _expire_if_needed(self, approval: ApprovalRequest) -> None:
        if approval.status != ApprovalStatus.PENDING.value:
            return
        expires_at = _as_utc(approval.expires_at)
        if expires_at and expires_at < datetime.now(timezone.utc):
            approval.status = ApprovalStatus.EXPIRED.value
            approval.resolved_at = datetime.now(timezone.utc)
            execution = self.session.get(ActionExecution, approval.action_execution_id)
            if execution and execution.status == ExecutionStatus.PENDING_APPROVAL.value:
                execution.status = ExecutionStatus.CANCELLED.value
                execution.completed_at = datetime.now(timezone.utc)
            self.session.flush()
            raise ActionError("Approval request has expired", code="approval_expired", status_code=409)

    def _response(
        self,
        *,
        case: RecoveryCase,
        evaluation: PolicyDecision,
        execution: ActionExecution,
        execution_status: ExecutionStatus,
        audit_id,
        approval_id=None,
        provider_result: ProviderResult | None = None,
        reason: str | None = None,
    ) -> dict:
        result = execution.result or {}
        link = None
        if provider_result:
            link = provider_result.payment_link_url
        elif isinstance(result, dict):
            link = result.get("payment_link_url")
        recommendation_only = execution_status in {
            ExecutionStatus.BLOCKED,
            ExecutionStatus.PENDING_APPROVAL,
            ExecutionStatus.CANCELLED,
        }
        return {
            "case_id": case.id,
            "requested_action": execution.action,
            "policy_decision": execution.policy_decision,
            "execution_status": execution_status.value,
            "execution_id": execution.id,
            "provider": execution.provider,
            "provider_reference": execution.provider_reference,
            "payment_link": link,
            "recommendation_only": recommendation_only,
            "audit_id": audit_id,
            "approval_id": approval_id or execution.approval_id,
            "reason": reason or evaluation.reason,
            "workflow": execution.workflow,
            "mock": bool(result.get("mock")) if isinstance(result, dict) else getattr(self.provider, "mock", True),
        }


def _to_paise(amount: Decimal) -> int:
    return int((amount * Decimal("100")).quantize(Decimal("1")))


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
