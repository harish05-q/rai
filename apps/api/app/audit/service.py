from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import AuditActor


class AuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        actor: AuditActor | str,
        source: str,
        status: str,
        reason: str,
        recovery_case_id: UUID | None = None,
        ai_decision_id: UUID | None = None,
        action_execution_id: UUID | None = None,
        approval_id: UUID | None = None,
        policy_decision: str | None = None,
        requested_action: str | None = None,
        executed_action: str | None = None,
        provider: str | None = None,
        provider_reference: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor=actor.value if isinstance(actor, AuditActor) else actor,
            source=source,
            status=status,
            reason=reason[:1024],
            recovery_case_id=recovery_case_id,
            ai_decision_id=ai_decision_id,
            action_execution_id=action_execution_id,
            approval_id=approval_id,
            policy_decision=policy_decision,
            requested_action=requested_action,
            executed_action=executed_action,
            provider=provider,
            provider_reference=provider_reference,
            details=details or {},
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(entry)
        self.session.flush()
        return entry
