from functools import lru_cache

from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.providers.gemini_provider import GeminiProvider
from app.llm.providers.groq_provider import GroqProvider
from app.llm.providers.ollama_provider import OllamaProvider


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider, instantiated once per process."""
    provider = settings.LLM_PROVIDER
    if provider == "groq":
        return GroqProvider(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
    if provider == "gemini":
        return GeminiProvider(api_key=settings.GOOGLE_API_KEY, model=settings.GEMINI_MODEL)
    if provider == "ollama":
        return OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
    raise ValueError(
        f"Unknown LLM_PROVIDER={provider!r}. Use one of: groq, gemini, ollama."
    )
