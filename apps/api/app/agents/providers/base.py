from typing import Protocol

from app.agents.schemas import LLMStructuredOutput, RecoveryAgentContext


class LLMProvider(Protocol):
    name: str
    model_name: str
    available: bool

    def generate(self, context: RecoveryAgentContext) -> LLMStructuredOutput:
        """Return validated structured output or raise an agent exception."""
