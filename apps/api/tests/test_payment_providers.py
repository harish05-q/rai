import httpx
import pytest

from app.payment_providers.exceptions import PaymentProviderError, ProviderTimeoutError
from app.payment_providers.mock import MockPaymentProvider
from app.payment_providers.razorpay import RazorpayPaymentProvider
from app.payment_providers.types import PaymentLinkRequest


def _request(**overrides) -> PaymentLinkRequest:
    data = dict(
        amount_paise=129900,
        currency="INR",
        reference_id="rai_test_ref_123456789012345678",
        description="test",
        customer_name="Test Customer",
        customer_email="customer@example.invalid",
        notify_email=True,
    )
    data.update(overrides)
    return PaymentLinkRequest(**data)


def test_mock_payment_link_creation() -> None:
    result = MockPaymentProvider().create_payment_link(_request())
    assert result.mock is True
    assert result.provider == "mock"
    assert result.provider_reference.startswith("plink_mock_")
    assert result.payment_link_url
    assert result.notification_status == "sent"


def test_mock_notification() -> None:
    provider = MockPaymentProvider()
    created = provider.create_payment_link(_request(notify_email=False))
    notified = provider.send_payment_link_notification(created.provider_reference, "email")
    assert notified.notification_status == "sent"
    assert notified.mock is True


def test_mock_provider_error() -> None:
    provider = MockPaymentProvider(force_error=True)
    with pytest.raises(PaymentProviderError):
        provider.create_payment_link(_request())


def test_mock_provider_timeout() -> None:
    provider = MockPaymentProvider(force_timeout=True)
    with pytest.raises(ProviderTimeoutError):
        provider.create_payment_link(_request())


def test_mock_malformed_request() -> None:
    provider = MockPaymentProvider()
    with pytest.raises(PaymentProviderError):
        provider.create_payment_link(_request(reference_id="", amount_paise=0))


def test_razorpay_create_payment_link_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v1/payment_links")
        assert "Authorization" in request.headers
        return httpx.Response(
            200,
            json={
                "id": "plink_test_1",
                "short_url": "https://rzp.io/i/test",
                "status": "created",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.razorpay.com")
    provider = RazorpayPaymentProvider(
        key_id="rzp_test_123",
        key_secret="secret",
        client=client,
    )
    result = provider.create_payment_link(_request())
    assert result.mock is False
    assert result.provider_reference == "plink_test_1"
    assert result.payment_link_url == "https://rzp.io/i/test"


def test_razorpay_malformed_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "an", "object"])

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.razorpay.com")
    provider = RazorpayPaymentProvider(key_id="rzp_test_123", key_secret="secret", client=client)
    with pytest.raises(PaymentProviderError):
        provider.create_payment_link(_request())


def test_razorpay_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.razorpay.com")
    provider = RazorpayPaymentProvider(key_id="rzp_test_123", key_secret="secret", client=client)
    with pytest.raises(ProviderTimeoutError):
        provider.create_payment_link(_request())


def test_razorpay_rejects_live_keys() -> None:
    with pytest.raises(PaymentProviderError):
        RazorpayPaymentProvider(key_id="rzp_live_abc", key_secret="secret")
