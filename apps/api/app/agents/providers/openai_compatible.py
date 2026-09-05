import json

import httpx
from pydantic import ValidationError

from app.agents.exceptions import InvalidModelOutputError, ProviderTimeoutError, ProviderUnavailableError
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.providers.json_util import strip_fences
from app.agents.schemas import LLMStructuredOutput, RecoveryAgentContext


class OpenAICompatibleProvider:
    name = "openai"
    available = True

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        provider_name: str = "openai",
    ) -> None:
        self._api_key = api_key
        self.model_name = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self.name = provider_name

    def generate(self, context: RecoveryAgentContext) -> LLMStructuredOutput:
        if not self._api_key:
            raise ProviderUnavailableError("LLM API key is not configured")
        if not self.model_name:
            raise ProviderUnavailableError("LLM model is not configured")

        url = f"{self._base_url}/chat/completions"
        body = {
            "model": self.model_name,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "instruction": "Return only the required JSON object. Do not invent facts.",
                            "recovery_context": context.to_prompt_payload(),
                        }
                    ),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(url, json=body, headers=headers, timeout=self._timeout)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("The LLM provider timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("The LLM provider is unavailable") from exc

        if response.status_code >= 400:
            raise ProviderUnavailableError("The LLM provider rejected the request")

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(strip_fences(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
            raise InvalidModelOutputError("The LLM provider returned malformed structured output") from exc

        try:
            return LLMStructuredOutput.model_validate(parsed)
        except ValidationError as exc:
            raise InvalidModelOutputError("The LLM provider returned invalid structured output") from exc
