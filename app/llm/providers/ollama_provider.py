import time

import httpx

from app.llm.base import LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Local LLM via Ollama (https://ollama.com).

    Run `ollama pull llama3.1:8b` once, then `ollama serve` (auto-runs after install).
    """

    name = "ollama"

    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self.model = model

    async def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        latency_ms = (time.perf_counter() - start) * 1000

        return LLMResponse(
            text=data.get("message", {}).get("content", ""),
            provider=self.name,
            model=self.model,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            latency_ms=latency_ms,
        )
