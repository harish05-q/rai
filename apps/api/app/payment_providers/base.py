from typing import Protocol

from app.payment_providers.types import PaymentLinkRequest, ProviderResult


class PaymentProvider(Protocol):
    name: str
    mock: bool

    def create_payment_link(self, request: PaymentLinkRequest) -> ProviderResult: ...

    def send_payment_link_notification(self, provider_reference: str, medium: str) -> ProviderResult: ...

    def create_subscription_recovery_workflow(
        self,
        *,
        subscription_external_id: str | None,
        reference_id: str,
        amount_paise: int,
        currency: str,
    ) -> ProviderResult: ...

    def get_payment(self, provider_payment_id: str) -> ProviderResult: ...

    def get_subscription(self, subscription_id: str) -> ProviderResult: ...
