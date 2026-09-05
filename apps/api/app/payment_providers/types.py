from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PaymentLinkRequest:
    amount_paise: int
    currency: str
    reference_id: str
    description: str
    customer_name: str | None = None
    customer_email: str | None = None
    expire_by: int | None = None
    notify_email: bool = False
    notify_sms: bool = False
    reminder_enable: bool = False
    preferred_methods: tuple[str, ...] = ()
    notes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    mock: bool
    operation: str
    status: str
    provider_reference: str | None
    payment_link_url: str | None
    notification_status: str | None
    message: str
    occurred_at: datetime
    details: dict[str, Any] = field(default_factory=dict)

    def as_safe_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "mock": self.mock,
            "operation": self.operation,
            "status": self.status,
            "provider_reference": self.provider_reference,
            "payment_link_url": self.payment_link_url,
            "notification_status": self.notification_status,
            "message": self.message,
            "occurred_at": self.occurred_at.isoformat(),
            "details": self.details,
        }
