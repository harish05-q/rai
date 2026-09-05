class AgentError(Exception):
    code = "agent_error"
    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CaseNotFoundError(AgentError):
    code = "case_not_found"
    status_code = 404


class MissingContextError(AgentError):
    code = "missing_context"
    status_code = 422


class ProviderUnavailableError(AgentError):
    code = "provider_unavailable"
    status_code = 503


class ProviderTimeoutError(AgentError):
    code = "provider_timeout"
    status_code = 504


class InvalidModelOutputError(AgentError):
    code = "invalid_model_output"
    status_code = 502
