from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    ComparisonStatus,
    FailureCategory,
    FailureSeverity,
    RecoverabilityAssessment,
    StrategyTiming,
    SuggestedAction,
)


class PaymentAgentContext(BaseModel):
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    attempt_number: int
    checkout_started: bool
    checkout_completed: bool
    external_payment_id: str


class FailureAgentContext(BaseModel):
    failure_code: str
    failure_category: str
    failure_message: str
    occurred_at: datetime


class CustomerAgentContext(BaseModel):
    successful_payments: int
    failed_payments: int
    total_payments: int
    total_amount_paid: Decimal


class SubscriptionAgentContext(BaseModel):
    status: str
    plan_name: str
    amount: Decimal
    next_billing_at: datetime | None = None


class DeterministicSignals(BaseModel):
    recoverability_score: Decimal
    priority: str
    eligibility: str
    suggested_action: str
    explanation_factors: list[str]
    case_status: str


class RecoveryAgentContext(BaseModel):
    case_id: UUID
    payment: PaymentAgentContext
    failure: FailureAgentContext | None = None
    customer: CustomerAgentContext | None = None
    subscription: SubscriptionAgentContext | None = None
    deterministic: DeterministicSignals

    def to_prompt_payload(self) -> dict:
        return self.model_dump(mode="json")


class AIDiagnosis(BaseModel):
    failure_category: FailureCategory
    failure_severity: FailureSeverity
    recoverability_assessment: RecoverabilityAssessment
    key_context_factors: list[str] = Field(min_length=1, max_length=8)

    @field_validator("key_context_factors")
    @classmethod
    def bound_factors(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("key_context_factors must contain at least one factor")
        return [item[:200] for item in cleaned[:8]]


class AIStrategy(BaseModel):
    recommended_action: SuggestedAction
    rationale: str = Field(min_length=8, max_length=1024)
    confidence: float = Field(ge=0.0, le=1.0)
    timing: StrategyTiming
    alternative_action: SuggestedAction | None = None
    concerns: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("rationale")
    @classmethod
    def concise_rationale(cls, value: str) -> str:
        return value.strip()

    @field_validator("concerns")
    @classmethod
    def bound_concerns(cls, value: list[str]) -> list[str]:
        return [item.strip()[:200] for item in value if item and item.strip()][:5]


class LLMStructuredOutput(BaseModel):
    diagnosis: AIDiagnosis
    strategy: AIStrategy


class BaselineComparison(BaseModel):
    status: ComparisonStatus
    reason: str


class AIRecoveryDecision(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    diagnosis: AIDiagnosis
    strategy: AIStrategy
    baseline_action: SuggestedAction
    baseline_score: Decimal
    ai_confidence: float
    comparison: BaselineComparison
    model: str
    provider: str
    ai_mode: str
    recommendation_only: bool = True
    created_at: datetime


class AgentStatus(BaseModel):
    ai_mode: str
    provider: str
    model: str
    available: bool
    recommendation_only: bool = True


class AgentActivityItem(BaseModel):
    id: UUID
    case_id: UUID
    external_payment_id: str
    title: str
    diagnosis_label: str
    recommended_action: str
    confidence: Decimal
    baseline_action: str
    comparison_status: str
    comparison_reason: str
    ai_mode: str
    created_at: datetime


class PaginatedAgentActivity(BaseModel):
    items: list[AgentActivityItem]
    total: int
    limit: int
    offset: int


class AgentSummary(BaseModel):
    cases_analyzed: int
    recommendations: int
    average_confidence: float | None
    agreement_rate: float | None
    cases_requiring_review: int
    ai_mode: str
    recommendation_only: bool = True


class AgentCaseResponse(BaseModel):
    case_id: UUID
    analysis: AIRecoveryDecision | None = None
    history_count: int = 0
    recommendation_only: bool = True


class BatchAnalyzeRequest(BaseModel):
    case_ids: list[UUID] | None = None
    limit: int = Field(default=10, ge=1, le=25)
    skip_existing: bool = True


class BatchAnalyzeResponse(BaseModel):
    requested: int
    analyzed: int
    reused: int
    skipped: int
    failed: int
    errors: list[str] = Field(default_factory=list)
    decisions: list[AIRecoveryDecision]
    executed_payment_operations: bool = False
    recommendation_only: bool = True
