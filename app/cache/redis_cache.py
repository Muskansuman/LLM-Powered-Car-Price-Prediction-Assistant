import json
import logging
from typing import Any, Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


def get_client() -> Optional[redis.Redis]:
    """Lazy, fault-tolerant Redis client.

    Returns None (instead of raising) if Redis is unreachable so the
    rest of the app keeps working without a cache.
    """
    global _client
    if _client is not None:
        return _client
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        _client = client
        logger.info("Connected to Redis at %s", settings.REDIS_URL)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Redis unavailable (%s); continuing without cache.", exc)
        _client = None
    return _client


def get_cached_prediction(key: str) -> Optional[Any]:
    client = get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception as exc:
        logger.warning("Redis GET failed: %s", exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("Corrupted cache entry for key=%s; ignoring.", key)
        return None


def set_cached_prediction(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    client = get_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value), ex=ttl_seconds)
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to serialize cache value for key=%s: %s", key, exc)
    except Exception as exc:
        logger.warning("Redis SET failed: %s", exc)
