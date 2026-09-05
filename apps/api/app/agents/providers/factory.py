from app.agents.exceptions import ProviderUnavailableError
from app.agents.providers.mock import MockLLMProvider
from app.agents.providers.openai_compatible import OpenAICompatibleProvider
from app.agents.schemas import LLMStructuredOutput, RecoveryAgentContext
from app.core.config import Settings, get_settings


class UnavailableLLMProvider:
    name = "unavailable"
    model_name = ""
    available = False

    def __init__(self, message: str, provider_name: str = "unavailable") -> None:
        self._message = message
        self.name = provider_name

    def generate(self, context: RecoveryAgentContext) -> LLMStructuredOutput:
        raise ProviderUnavailableError(self._message)


def get_llm_provider(settings: Settings | None = None):
    config = settings or get_settings()
    mode = (config.ai_mode or "mock").strip().lower()
    provider = (config.llm_provider or "").strip().lower()

    if mode == "mock" or provider == "mock":
        return MockLLMProvider()

    if mode != "live":
        return MockLLMProvider()

    if not config.llm_api_key:
        return UnavailableLLMProvider("LLM_API_KEY is not configured")
    if not config.llm_model:
        return UnavailableLLMProvider("LLM_MODEL is not configured")

    name = provider or "openai"
    if name in {"openai", "openai_compatible", ""}:
        return OpenAICompatibleProvider(
            api_key=config.llm_api_key,
            model=config.llm_model,
            base_url=config.llm_base_url or "https://api.openai.com/v1",
            timeout_seconds=config.llm_timeout_seconds,
            provider_name="openai",
        )

    return UnavailableLLMProvider(f"Unsupported LLM_PROVIDER '{config.llm_provider}'")
