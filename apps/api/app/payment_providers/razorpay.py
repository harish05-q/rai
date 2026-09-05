from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.logging import log_event
from app.payment_providers.exceptions import (
    PaymentProviderError,
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.payment_providers.types import PaymentLinkRequest, ProviderResult

LIVE_KEY_PREFIX = "rzp_live_"


class RazorpayPaymentProvider:
    """Razorpay Test Mode adapter. Only documented Payment Links / fetch APIs."""

    name = "razorpay"
    mock = False

    def __init__(
        self,
        *,
        key_id: str,
        key_secret: str,
        base_url: str = "https://api.razorpay.com",
        timeout_seconds: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not key_id or not key_secret:
            raise ProviderConfigurationError("Razorpay test-mode credentials are not configured")
        if key_id.startswith(LIVE_KEY_PREFIX):
            raise ProviderConfigurationError("Live Razorpay keys are not permitted")
        self._key_id = key_id
        self._auth = (key_id, key_secret)
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(
            base_url=self._base_url,
            auth=self._auth,
            timeout=timeout_seconds,
            headers={"Content-Type": "application/json"},
        )

    def create_payment_link(self, request: PaymentLinkRequest) -> ProviderResult:
        payload: dict[str, Any] = {
            "amount": request.amount_paise,
            "currency": request.currency,
            "reference_id": request.reference_id[:40],
            "description": request.description[:2048],
            "accept_partial": False,
            "notify": {"email": request.notify_email, "sms": False},
            "reminder_enable": request.reminder_enable,
            "notes": {"source": "rai", **request.notes},
        }
        if request.expire_by:
            payload["expire_by"] = request.expire_by
        customer: dict[str, str] = {}
        if request.customer_name:
            customer["name"] = request.customer_name
        if request.customer_email:
            customer["email"] = request.customer_email
        if customer:
            payload["customer"] = customer
        if request.preferred_methods:
            payload["options"] = {
                "checkout": {
                    "method": {method: 1 for method in request.preferred_methods},
                }
            }
        data = self._request("POST", "/v1/payment_links", json=payload)
        link_id = data.get("id")
        if not isinstance(link_id, str):
            raise ProviderResponseError("Razorpay payment link response was missing id")
        short_url = data.get("short_url")
        notify_status = "requested" if request.notify_email else "not_requested"
        return ProviderResult(
            provider=self.name,
            mock=False,
            operation="create_payment_link",
            status=str(data.get("status") or "created"),
            provider_reference=link_id,
            payment_link_url=short_url if isinstance(short_url, str) else None,
            notification_status=notify_status,
            message="Razorpay Payment Link created in test mode.",
            occurred_at=datetime.now(timezone.utc),
            details={"reference_id": request.reference_id, "status": data.get("status")},
        )

    def send_payment_link_notification(self, provider_reference: str, medium: str) -> ProviderResult:
        if medium not in {"email", "sms"}:
            raise PaymentProviderError("Unsupported notification medium")
        data = self._request("POST", f"/v1/payment_links/{provider_reference}/notify_by/{medium}")
        success = data.get("success")
        return ProviderResult(
            provider=self.name,
            mock=False,
            operation="send_payment_link_notification",
            status="notified" if success else "failed",
            provider_reference=provider_reference,
            payment_link_url=None,
            notification_status="sent" if success else "failed",
            message="Razorpay Payment Link notification requested.",
            occurred_at=datetime.now(timezone.utc),
            details={"medium": medium, "success": success},
        )

    def create_subscription_recovery_workflow(
        self,
        *,
        subscription_external_id: str | None,
        reference_id: str,
        amount_paise: int,
        currency: str,
    ) -> ProviderResult:
        details: dict[str, Any] = {
            "workflow": "provider_managed_deferred",
            "reference_id": reference_id,
            "amount_paise": amount_paise,
            "currency": currency,
        }
        status = "deferred"
        message = (
            "Razorpay does not expose a generic retry_payment API. Subscription recovery is "
            "recorded as provider-managed/deferred rather than a direct charge."
        )
        if subscription_external_id:
            try:
                fetched = self.get_subscription(subscription_external_id)
                details["subscription_status"] = fetched.status
                status = "deferred"
            except PaymentProviderError as exc:
                details["subscription_fetch"] = exc.message
        return ProviderResult(
            provider=self.name,
            mock=False,
            operation="subscription_provider_managed_recovery",
            status=status,
            provider_reference=subscription_external_id,
            payment_link_url=None,
            notification_status=None,
            message=message,
            occurred_at=datetime.now(timezone.utc),
            details=details,
        )

    def get_payment(self, provider_payment_id: str) -> ProviderResult:
        data = self._request("GET", f"/v1/payments/{provider_payment_id}")
        payment_id = data.get("id")
        return ProviderResult(
            provider=self.name,
            mock=False,
            operation="get_payment",
            status=str(data.get("status") or "unknown"),
            provider_reference=payment_id if isinstance(payment_id, str) else provider_payment_id,
            payment_link_url=None,
            notification_status=None,
            message="Fetched Razorpay payment.",
            occurred_at=datetime.now(timezone.utc),
            details={"status": data.get("status")},
        )

    def get_subscription(self, subscription_id: str) -> ProviderResult:
        data = self._request("GET", f"/v1/subscriptions/{subscription_id}")
        sub_id = data.get("id")
        return ProviderResult(
            provider=self.name,
            mock=False,
            operation="get_subscription",
            status=str(data.get("status") or "unknown"),
            provider_reference=sub_id if isinstance(sub_id, str) else subscription_id,
            payment_link_url=None,
            notification_status=None,
            message="Fetched Razorpay subscription.",
            occurred_at=datetime.now(timezone.utc),
            details={"status": data.get("status")},
        )

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        log_event("razorpay_request", method=method, path=path, provider="razorpay")
        try:
            response = self._client.request(method, path, json=json, auth=self._auth)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Razorpay request timed out") from exc
        except httpx.HTTPError as exc:
            raise PaymentProviderError("Razorpay request failed") from exc
        if response.status_code >= 400:
            raise PaymentProviderError(
                f"Razorpay returned HTTP {response.status_code}",
                code="provider_http_error",
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderResponseError("Razorpay response was not valid JSON") from exc
        if not isinstance(data, dict):
            raise ProviderResponseError("Razorpay response was not an object")
        return data

    def observe_payment_link(self, provider_reference: str) -> ProviderResult:
        """Documented Payment Link fetch: GET /v1/payment_links/{id}."""

        data = self._request("GET", f"/v1/payment_links/{provider_reference}")
        link_id = data.get("id")
        short_url = data.get("short_url")
        return ProviderResult(
            provider=self.name,
            mock=False,
            operation="observe_payment_link",
            status=str(data.get("status") or "unknown"),
            provider_reference=link_id if isinstance(link_id, str) else provider_reference,
            payment_link_url=short_url if isinstance(short_url, str) else None,
            notification_status=None,
            message="Fetched Razorpay Payment Link status in test mode.",
            occurred_at=datetime.now(timezone.utc),
            details={"status": data.get("status"), "amount_paid": data.get("amount_paid")},
        )
