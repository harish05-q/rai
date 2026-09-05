from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.agents.comparison import compare_to_baseline
from app.agents.context import build_recovery_context
from app.agents.exceptions import CaseNotFoundError, MissingContextError
from app.agents.providers.factory import get_llm_provider
from app.agents.schemas import (
    AIDiagnosis,
    AIRecoveryDecision,
    AgentActivityItem,
    AgentCaseResponse,
    AgentStatus,
    AgentSummary,
    AIStrategy,
    BaselineComparison,
    BatchAnalyzeResponse,
    LLMStructuredOutput,
)
from app.core.config import get_settings
from app.models.ai_decision import AIDecision
from app.models.customer import Customer
from app.models.enums import ComparisonStatus, SuggestedAction
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase


class AgentOrchestrator:
    def __init__(self, session: Session, provider=None) -> None:
        self.session = session
        self.settings = get_settings()
        self.provider = provider or get_llm_provider(self.settings)

    def status(self) -> AgentStatus:
        return AgentStatus(
            ai_mode=self._ai_mode(),
            provider=self.provider.name,
            model=getattr(self.provider, "model_name", "") or self.settings.llm_model or "",
            available=bool(getattr(self.provider, "available", True)),
        )

    def get_case_analysis(self, case_id) -> AgentCaseResponse:
        self._load_case(case_id)
        decisions = self._decisions_for_case(case_id)
        latest = decisions[0] if decisions else None
        return AgentCaseResponse(
            case_id=case_id,
            analysis=self._to_decision(latest) if latest else None,
            history_count=len(decisions),
        )

    def analyze_case(self, case_id, *, reuse_recent: bool = False) -> AIRecoveryDecision:
        case = self._load_case(case_id)
        if reuse_recent:
            existing = self._latest_decision(case.id)
            if existing is not None:
                return self._to_decision(existing, case)

        try:
            context = build_recovery_context(case)
        except ValueError as exc:
            raise MissingContextError(str(exc)) from exc

        output: LLMStructuredOutput = self.provider.generate(context)
        comparison = compare_to_baseline(
            output.strategy.recommended_action,
            case.suggested_action,
            output.strategy.rationale,
        )
        record = AIDecision(
            recovery_case_id=case.id,
            model=getattr(self.provider, "model_name", "") or self.settings.llm_model or "unknown",
            provider=self.provider.name,
            ai_mode=self._ai_mode(),
            recommended_action=output.strategy.recommended_action.value,
            confidence=Decimal(str(round(output.strategy.confidence, 4))),
            diagnosis=output.diagnosis.model_dump(mode="json"),
            rationale=output.strategy.rationale,
            alternative_action=(
                output.strategy.alternative_action.value if output.strategy.alternative_action else None
            ),
            timing=output.strategy.timing.value,
            concerns=output.strategy.concerns,
            baseline_action=case.suggested_action,
            baseline_score=Decimal(str(case.recoverability_score)),
            comparison_status=comparison.status.value,
            comparison_reason=comparison.reason,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return self._to_decision(record, case)

    def analyze_batch(
        self,
        *,
        case_ids: list | None = None,
        limit: int = 10,
        skip_existing: bool = True,
    ) -> BatchAnalyzeResponse:
        max_batch = min(limit, self.settings.agent_batch_max)
        cases = self._select_batch_cases(case_ids=case_ids, limit=max_batch)
        analyzed: list[AIRecoveryDecision] = []
        reused = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        for case in cases:
            existing = self._latest_decision(case.id)
            if skip_existing and existing is not None:
                analyzed.append(self._to_decision(existing, case))
                reused += 1
                continue
            try:
                analyzed.append(self.analyze_case(case.id, reuse_recent=False))
            except Exception as exc:
                failed += 1
                errors.append(f"{case.id}: {exc}")

        return BatchAnalyzeResponse(
            requested=len(cases),
            analyzed=len(analyzed) - reused,
            reused=reused,
            skipped=skipped,
            failed=failed,
            errors=errors[:10],
            decisions=analyzed,
        )

    def activity(self, *, limit: int = 20, offset: int = 0) -> tuple[list[AgentActivityItem], int]:
        total = self.session.scalar(select(func.count(AIDecision.id))) or 0
        records = self.session.scalars(
            select(AIDecision)
            .options(selectinload(AIDecision.recovery_case).selectinload(RecoveryCase.payment))
            .order_by(AIDecision.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        items = [self._to_activity(record) for record in records]
        return items, int(total)

    def summary(self) -> AgentSummary:
        total = self.session.scalar(select(func.count(AIDecision.id))) or 0
        cases = self.session.scalar(select(func.count(func.distinct(AIDecision.recovery_case_id)))) or 0
        avg = self.session.scalar(select(func.avg(AIDecision.confidence)))
        aligned = self.session.scalar(
            select(func.count(AIDecision.id)).where(AIDecision.comparison_status == ComparisonStatus.ALIGNED)
        ) or 0
        review = self.session.scalar(
            select(func.count(func.distinct(AIDecision.recovery_case_id))).where(
                AIDecision.recommended_action == SuggestedAction.HUMAN_REVIEW
            )
        ) or 0
        agreement = float(aligned) / float(total) if total else None
        return AgentSummary(
            cases_analyzed=int(cases),
            recommendations=int(total),
            average_confidence=float(avg) if avg is not None else None,
            agreement_rate=agreement,
            cases_requiring_review=int(review),
            ai_mode=self._ai_mode(),
        )

    def _ai_mode(self) -> str:
        mode = (self.settings.ai_mode or "mock").strip().lower()
        if self.provider.name == "mock":
            return "mock"
        return mode if mode in {"mock", "live"} else "mock"

    def _load_case(self, case_id) -> RecoveryCase:
        case = self.session.scalar(
            select(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .options(
                selectinload(RecoveryCase.payment).selectinload(Payment.customer),
                selectinload(RecoveryCase.payment).selectinload(Payment.failures),
                selectinload(RecoveryCase.payment).selectinload(Payment.customer).selectinload(
                    Customer.subscriptions
                ),
            )
        )
        if case is None:
            raise CaseNotFoundError("Recovery case was not found")
        return case

    def _select_batch_cases(self, *, case_ids: list | None, limit: int) -> list[RecoveryCase]:
        query = select(RecoveryCase).options(
            selectinload(RecoveryCase.payment).selectinload(Payment.customer),
            selectinload(RecoveryCase.payment).selectinload(Payment.failures),
        )
        if case_ids:
            query = query.where(RecoveryCase.id.in_(case_ids[:limit]))
        else:
            query = query.order_by(RecoveryCase.created_at.desc()).limit(limit)
        return list(self.session.scalars(query).unique().all())

    def _decisions_for_case(self, case_id) -> list[AIDecision]:
        return list(
            self.session.scalars(
                select(AIDecision)
                .where(AIDecision.recovery_case_id == case_id)
                .order_by(AIDecision.created_at.desc())
            ).all()
        )

    def _latest_decision(self, case_id) -> AIDecision | None:
        return self.session.scalar(
            select(AIDecision)
            .where(AIDecision.recovery_case_id == case_id)
            .order_by(AIDecision.created_at.desc())
            .limit(1)
        )

    def _to_decision(self, record: AIDecision, case: RecoveryCase | None = None) -> AIRecoveryDecision:
        diagnosis = AIDiagnosis.model_validate(record.diagnosis)
        strategy = AIStrategy(
            recommended_action=SuggestedAction(record.recommended_action),
            rationale=record.rationale,
            confidence=float(record.confidence),
            timing=record.timing,
            alternative_action=SuggestedAction(record.alternative_action) if record.alternative_action else None,
            concerns=list(record.concerns or []),
        )
        return AIRecoveryDecision(
            id=record.id,
            case_id=record.recovery_case_id,
            diagnosis=diagnosis,
            strategy=strategy,
            baseline_action=SuggestedAction(record.baseline_action),
            baseline_score=record.baseline_score,
            ai_confidence=float(record.confidence),
            comparison=BaselineComparison(
                status=ComparisonStatus(record.comparison_status),
                reason=record.comparison_reason,
            ),
            model=record.model,
            provider=record.provider,
            ai_mode=record.ai_mode,
            created_at=record.created_at,
        )

    def _to_activity(self, record: AIDecision) -> AgentActivityItem:
        payment = record.recovery_case.payment if record.recovery_case else None
        external_id = payment.external_payment_id if payment else "unknown"
        diagnosis = record.diagnosis or {}
        category = str(diagnosis.get("failure_category", "unknown")).replace("_", " ")
        return AgentActivityItem(
            id=record.id,
            case_id=record.recovery_case_id,
            external_payment_id=external_id,
            title=f"R.AI analyzed {external_id}",
            diagnosis_label=category,
            recommended_action=record.recommended_action,
            confidence=record.confidence,
            baseline_action=record.baseline_action,
            comparison_status=record.comparison_status,
            comparison_reason=record.comparison_reason,
            ai_mode=record.ai_mode,
            created_at=record.created_at,
        )
