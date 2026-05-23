import hashlib
import json
import logging
from typing import Any, Optional

import joblib
import pandas as pd

from app.cache.redis_cache import get_cached_prediction, set_cached_prediction
from app.core.config import settings

logger = logging.getLogger(__name__)

_model: Optional[Any] = None


def _get_model():
    """Load the sklearn model on first use (avoids import-time crashes)."""
    global _model
    if _model is None:
        logger.info("Loading model from %s", settings.MODEL_PATH)
        _model = joblib.load(settings.MODEL_PATH)
    return _model


def _cache_key(data: dict) -> str:
    """Order-independent, collision-resistant cache key."""
    canonical = json.dumps(data, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"prediction:{digest}"


def predict_car_price(data: dict) -> float:
    key = _cache_key(data)
    cached = get_cached_prediction(key)
    if cached is not None:
        logger.debug("Cache hit for key=%s", key)
        return float(cached)

    model = _get_model()
    input_df = pd.DataFrame([data])
    prediction = float(model.predict(input_df)[0])
    set_cached_prediction(key, prediction)
    return prediction
