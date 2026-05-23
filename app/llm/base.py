from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[float] = None


class LLMProvider(ABC):
    """Provider-agnostic chat interface.

    All providers accept OpenAI-style messages and return an LLMResponse.
    Set json_mode=True to constrain output to valid JSON.
    """

    name: str = "base"
    model: str = "unknown"

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        ...
