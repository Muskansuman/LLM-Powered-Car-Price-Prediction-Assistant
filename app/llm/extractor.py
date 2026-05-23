import json
import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.llm.base import LLMProvider, LLMResponse
from app.llm.prompts import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# Fields the user must supply — clarification is triggered if any are null
USER_REQUIRED_FIELDS = [
    "company", "year", "owner", "fuel", "seller_type", "transmission", "km_driven",
]

# Technical fields inferred from car model — never ask the user for these
INFERRED_FIELDS = [
    "mileage_mpg", "engine_cc", "max_power_bhp", "torque_nm", "seats",
]

# All fields needed by the ML model
REQUIRED_FIELDS = USER_REQUIRED_FIELDS + INFERRED_FIELDS

# Typical fallback values used when LLM fails to infer technical specs
_INFERRED_DEFAULTS = {
    "mileage_mpg": 40.0,    # ~17 kmpl, typical Indian petrol hatchback
    "engine_cc": 1200.0,
    "max_power_bhp": 82.0,
    "torque_nm": 113.0,
    "seats": 5.0,
}


class ExtractedCar(BaseModel):
    """Loose schema: every field optional so the LLM can return partials."""

    model_config = ConfigDict(extra="ignore")

    company: Optional[str] = None
    year: Optional[int] = None
    owner: Optional[str] = None
    fuel: Optional[str] = None
    seller_type: Optional[str] = None
    transmission: Optional[str] = None
    km_driven: Optional[float] = None
    mileage_mpg: Optional[float] = None
    engine_cc: Optional[float] = None
    max_power_bhp: Optional[float] = None
    torque_nm: Optional[float] = None
    seats: Optional[float] = None
    missing_fields: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    def _fill_inferred_defaults(self) -> None:
        """Fill any still-null technical fields with safe fallback values."""
        for f, default in _INFERRED_DEFAULTS.items():
            if getattr(self, f) is None:
                setattr(self, f, default)
                self.assumptions.append(
                    f"Used typical default for {f} ({default}) — no specific data available"
                )

    def is_complete(self) -> bool:
        """Ready to predict when all user-facing fields are present."""
        return all(getattr(self, f) is not None for f in USER_REQUIRED_FIELDS)

    def truly_missing(self) -> list[str]:
        """Only report user-facing fields as missing — never technical specs."""
        return [f for f in USER_REQUIRED_FIELDS if getattr(self, f) is None]

    def to_features(self) -> dict:
        self._fill_inferred_defaults()
        return {f: getattr(self, f) for f in REQUIRED_FIELDS}


async def extract_car_features(
    provider: LLMProvider,
    user_message: str,
    history: Optional[list[dict]] = None,
) -> tuple[ExtractedCar, LLMResponse]:
    """Extract car features from a user message using JSON-mode LLM output."""
    messages: list[dict] = [{"role": "system", "content": EXTRACTION_SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = await provider.chat(
        messages=messages,
        json_mode=True,
        temperature=0.1,
        max_tokens=512,
    )

    raw = response.text.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("LLM returned invalid JSON: %s | raw=%r", exc, raw[:300])
        payload = {}

    try:
        extracted = ExtractedCar.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Extraction failed validation: %s", exc)
        extracted = ExtractedCar()

    extracted.missing_fields = extracted.truly_missing()
    return extracted, response
