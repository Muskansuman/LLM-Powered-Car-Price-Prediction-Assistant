import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Car Price API"

    # Auth
    API_KEY: str = os.getenv("API_KEY", "demo-key")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "secret")
    JWT_ALGORITHM: str = "HS256"

    # Infra
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    MODEL_PATH: str = os.getenv("MODEL_PATH", "app/models/model.joblib")

    # LLM layer
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()  # groq | gemini | ollama
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    # Conversation memory
    CHAT_HISTORY_TTL_SECONDS: int = int(os.getenv("CHAT_HISTORY_TTL_SECONDS", "3600"))
    CHAT_HISTORY_MAX_TURNS: int = int(os.getenv("CHAT_HISTORY_MAX_TURNS", "10"))

    # Rate limits (SlowAPI format, e.g. "60/minute")
    RATE_LIMIT_CHAT: str = os.getenv("RATE_LIMIT_CHAT", "60/minute")
    RATE_LIMIT_CHAT_DELETE: str = os.getenv("RATE_LIMIT_CHAT_DELETE", "120/minute")
    RATE_LIMIT_PREDICT: str = os.getenv("RATE_LIMIT_PREDICT", "120/minute")


settings = Settings()
