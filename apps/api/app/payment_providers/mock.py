from datetime import datetime, timezone

from app.payment_providers.exceptions import PaymentProviderError, ProviderTimeoutError
from app.payment_providers.types import PaymentLinkRequest, ProviderResult


class MockPaymentProvider:
    """Deterministic in-process provider. Results are always marked mock."""

    name = "mock"
    mock = True

    def __init__(self, *, force_error: bool = False, force_timeout: bool = False) -> None:
        self.force_error = force_error
        self.force_timeout = force_timeout
        self.created_links: dict[str, ProviderResult] = {}

    def create_payment_link(self, request: PaymentLinkRequest) -> ProviderResult:
        self._maybe_fail("create_payment_link")
        if not request.reference_id or request.amount_paise <= 0:
            raise PaymentProviderError("Malformed payment link request", code="provider_response_invalid")
        reference = f"plink_mock_{request.reference_id[:18]}"
        notify = "sent" if request.notify_email else "not_requested"
        result = ProviderResult(
            provider=self.name,
            mock=True,
            operation="create_payment_link",
            status="created",
            provider_reference=reference,
            payment_link_url=f"https://mock.razorpay.invalid/{reference}",
            notification_status=notify,
            message="Mock Payment Link created. This is not a Razorpay operation.",
            occurred_at=datetime.now(timezone.utc),
            details={
                "reference_id": request.reference_id,
                "amount_paise": request.amount_paise,
                "currency": request.currency,
                "preferred_methods": list(request.preferred_methods),
            },
        )
        self.created_links[reference] = result
        return result

    def send_payment_link_notification(self, provider_reference: str, medium: str) -> ProviderResult:
        self._maybe_fail("send_payment_link_notification")
        if medium not in {"email", "sms"}:
            raise PaymentProviderError("Unsupported notification medium", code="provider_response_invalid")
        return ProviderResult(
            provider=self.name,
            mock=True,
            operation="send_payment_link_notification",
            status="notified",
            provider_reference=provider_reference,
            payment_link_url=f"https://mock.razorpay.invalid/{provider_reference}",
            notification_status="sent",
            message=f"Mock {medium} notification recorded. This is not a Razorpay operation.",
            occurred_at=datetime.now(timezone.utc),
            details={"medium": medium},
        )

    def create_subscription_recovery_workflow(
        self,
        *,
        subscription_external_id: str | None,
        reference_id: str,
        amount_paise: int,
        currency: str,
    ) -> ProviderResult:
        self._maybe_fail("create_subscription_recovery_workflow")
        return ProviderResult(
            provider=self.name,
            mock=True,
            operation="subscription_provider_managed_recovery",
            status="deferred",
            provider_reference=subscription_external_id or f"sub_mock_{reference_id[:12]}",
            payment_link_url=None,
            notification_status=None,
            message=(
                "Mock provider-managed subscription recovery recorded. "
                "No charge was attempted; Razorpay has no generic retry_payment API."
            ),
            occurred_at=datetime.now(timezone.utc),
            details={
                "reference_id": reference_id,
                "amount_paise": amount_paise,
                "currency": currency,
                "workflow": "provider_managed_deferred",
            },
        )

    def get_payment(self, provider_payment_id: str) -> ProviderResult:
        self._maybe_fail("get_payment")
        return ProviderResult(
            provider=self.name,
            mock=True,
            operation="get_payment",
            status="failed",
            provider_reference=provider_payment_id,
            payment_link_url=None,
            notification_status=None,
            message="Mock payment fetch. This is not a Razorpay operation.",
            occurred_at=datetime.now(timezone.utc),
            details={"id": provider_payment_id},
        )

    def get_subscription(self, subscription_id: str) -> ProviderResult:
        self._maybe_fail("get_subscription")
        return ProviderResult(
            provider=self.name,
            mock=True,
            operation="get_subscription",
            status="past_due",
            provider_reference=subscription_id,
            payment_link_url=None,
            notification_status=None,
            message="Mock subscription fetch. This is not a Razorpay operation.",
            occurred_at=datetime.now(timezone.utc),
            details={"id": subscription_id, "status": "past_due"},
        )

    def _maybe_fail(self, operation: str) -> None:
        if self.force_timeout:
            raise ProviderTimeoutError(f"Mock provider timed out during {operation}")
        if self.force_error:
            raise PaymentProviderError(f"Mock provider error during {operation}")
