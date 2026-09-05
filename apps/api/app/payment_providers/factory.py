from app.core.config import Settings, get_settings
from app.core.logging import log_event
from app.payment_providers.mock import MockPaymentProvider
from app.payment_providers.razorpay import RazorpayPaymentProvider


def get_payment_provider(settings: Settings | None = None):
    cfg = settings or get_settings()
    requested = (cfg.payment_provider or "mock").strip().lower()
    if requested == "razorpay":
        if cfg.razorpay_key_id and cfg.razorpay_key_secret:
            log_event("payment_provider_selected", provider="razorpay", mode="test")
            return RazorpayPaymentProvider(
                key_id=cfg.razorpay_key_id,
                key_secret=cfg.razorpay_key_secret,
                base_url=cfg.razorpay_base_url,
                timeout_seconds=cfg.razorpay_timeout_seconds,
            )
        log_event("payment_provider_fallback_mock", reason="missing_razorpay_credentials")
    return MockPaymentProvider(force_error=cfg.mock_provider_force_error)
