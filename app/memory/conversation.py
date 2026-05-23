"""Redis-backed conversation memory.

Falls back to an in-process dict if Redis is unavailable, so chat still works.
"""

import json
import logging
from collections import defaultdict, deque
from typing import Optional

from app.cache.redis_cache import get_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# In-process fallback: { session_id: deque[messages] }
_FALLBACK: dict[str, deque] = defaultdict(
    lambda: deque(maxlen=settings.CHAT_HISTORY_MAX_TURNS * 2)
)


def _key(session_id: str) -> str:
    return f"chat:history:{session_id}"


def get_history(session_id: str) -> list[dict]:
    """Return chat history (oldest first) as OpenAI-style messages."""
    if not session_id:
        return []
    client = get_client()
    if client is None:
        return list(_FALLBACK.get(session_id, []))
    try:
        raw = client.lrange(_key(session_id), 0, -1)
        return [json.loads(item) for item in raw]
    except Exception as exc:
        logger.warning("Failed to read history for %s: %s", session_id, exc)
        return []


def append_turn(session_id: str, user_msg: str, assistant_msg: str) -> None:
    if not session_id:
        return
    items = [
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": assistant_msg},
    ]
    client = get_client()
    if client is None:
        buf = _FALLBACK[session_id]
        for item in items:
            buf.append(item)
        return
    try:
        pipe = client.pipeline()
        for item in items:
            pipe.rpush(_key(session_id), json.dumps(item))
        # Keep only the last N turns (2 messages per turn).
        pipe.ltrim(_key(session_id), -settings.CHAT_HISTORY_MAX_TURNS * 2, -1)
        pipe.expire(_key(session_id), settings.CHAT_HISTORY_TTL_SECONDS)
        pipe.execute()
    except Exception as exc:
        logger.warning("Failed to write history for %s: %s", session_id, exc)


def clear_history(session_id: str) -> None:
    client = get_client()
    if client is not None:
        try:
            client.delete(_key(session_id))
        except Exception:
            pass
    _FALLBACK.pop(session_id, None)
