import json

from app.llm.base import LLMProvider, LLMResponse
from app.llm.prompts import CLARIFY_SYSTEM_PROMPT, EXPLAINER_SYSTEM_PROMPT


async def generate_explanation(
    provider: LLMProvider,
    features: dict,
    predicted_price_inr: float,
    assumptions: list[str],
) -> LLMResponse:
    user_payload = {
        "car_details": features,
        "predicted_price_inr": round(predicted_price_inr, 2),
        "predicted_price_lakhs": round(predicted_price_inr / 100_000, 2),
        "assumptions": assumptions,
    }
    messages = [
        {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, default=str)},
    ]
    return await provider.chat(messages=messages, temperature=0.6, max_tokens=300)


async def generate_clarification(
    provider: LLMProvider,
    so_far: dict,
    missing_fields: list[str],
) -> LLMResponse:
    user_payload = {"already_known": so_far, "missing_fields": missing_fields}
    messages = [
        {"role": "system", "content": CLARIFY_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, default=str)},
    ]
    return await provider.chat(messages=messages, temperature=0.5, max_tokens=120)
