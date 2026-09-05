from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_payment_id: str
    amount: Decimal
    currency: str
    status: str
    payment_method: str
    failure_category: str | None
    customer_name: str
    customer_email: str
    created_at: datetime
    recovery_status: str | None


class PaginatedPayments(BaseModel):
    items: list[PaymentListItem]
    total: int
    limit: int
    offset: int


class RecoveryCaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    external_payment_id: str
    revenue_at_risk: Decimal
    currency: str
    failure_category: str | None
    recoverability_score: Decimal
    priority: str
    eligibility: str
    suggested_action: str
    status: str
    customer_name: str
    explanation_factors: list[str]
    created_at: datetime


class PaginatedRecoveryCases(BaseModel):
    items: list[RecoveryCaseListItem]
    total: int
    limit: int
    offset: int


class RecoverySummary(BaseModel):
    total_payments: int
    total_failed_payments: int
    recoverable_payments: int
    revenue_at_risk: Decimal
    open_recovery_cases: int
    recovered_cases: int
    recovered_revenue: Decimal


class AnalyzeRequest(BaseModel):
    merchant_id: UUID | None = None
    payment_id: UUID | None = None
    limit: int | None = Field(default=None, ge=1, le=20000)


class AnalyzeResponse(BaseModel):
    payments_analyzed: int
    cases_created: int
    cases_updated: int
    cases_skipped: int
    executed_payment_operations: bool = False
