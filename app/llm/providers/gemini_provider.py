import asyncio
import time

from google import genai
from google.genai import types

from app.llm.base import LLMProvider, LLMResponse


def _to_gemini_contents(messages: list[dict]) -> tuple[str, list]:
    """Split OpenAI-style messages into a system instruction + user/assistant turns."""
    system_parts: list[str] = []
    contents: list = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=content)]))
        elif role == "assistant":
            contents.append(types.Content(role="model", parts=[types.Part(text=content)]))
    return "\n\n".join(system_parts), contents


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Get a free key at https://aistudio.google.com"
            )
        self._client = genai.Client(api_key=api_key)
        self.model = model

    async def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        system_instruction, contents = _to_gemini_contents(messages)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction or None,
        )
        if json_mode:
            config.response_mime_type = "application/json"

        start = time.perf_counter()
        # google-genai's sync client; offload to a thread to keep FastAPI async.
        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.model,
            contents=contents,
            config=config,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        usage = getattr(response, "usage_metadata", None)
        return LLMResponse(
            text=response.text or "",
            provider=self.name,
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            completion_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
            latency_ms=latency_ms,
        )
