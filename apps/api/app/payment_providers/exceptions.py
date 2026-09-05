class PaymentProviderError(Exception):
    code = "provider_error"
    retryable = False

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class ProviderTimeoutError(PaymentProviderError):
    code = "provider_timeout"
    retryable = True


class ProviderResponseError(PaymentProviderError):
    code = "provider_response_invalid"


class ProviderConfigurationError(PaymentProviderError):
    code = "provider_configuration"
