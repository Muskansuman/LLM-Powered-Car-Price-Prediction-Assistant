import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import get_api_key
from app.core.rate_limit import limiter
from app.llm.explainer import generate_clarification, generate_explanation
from app.llm.extractor import extract_car_features
from app.llm.factory import get_llm_provider
from app.memory.conversation import append_turn, clear_history, get_history
from app.services.model_service import predict_car_price

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    predicted_price: Optional[float] = None
    formatted_price: Optional[str] = None
    extracted_features: Optional[dict] = None
    missing_fields: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    provider: str
    model: str
    latency_ms: float


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def chat(request: Request, req: ChatRequest, _=Depends(get_api_key)):
    session_id = req.session_id or uuid.uuid4().hex
    history = get_history(session_id)

    try:
        provider = get_llm_provider()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    extracted, extract_resp = await extract_car_features(
        provider, req.message, history=history
    )

    if extracted.is_complete():
        features = extracted.to_features()
        # Run sync model.predict in a thread so we don't block the event loop.
        prediction = await asyncio.to_thread(predict_car_price, features)
        explain_resp = await generate_explanation(
            provider, features, prediction, extracted.assumptions
        )
        reply = explain_resp.text.strip()
        total_latency = (extract_resp.latency_ms or 0) + (explain_resp.latency_ms or 0)

        append_turn(session_id, req.message, reply)
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            predicted_price=round(prediction, 2),
            formatted_price=f"\u20b9{prediction:,.2f}",
            extracted_features=features,
            missing_fields=[],
            assumptions=extracted.assumptions,
            provider=provider.name,
            model=provider.model,
            latency_ms=round(total_latency, 1),
        )

    so_far = {f: v for f, v in extracted.model_dump().items()
              if f not in ("missing_fields", "assumptions") and v is not None}
    clarify_resp = await generate_clarification(
        provider, so_far, extracted.missing_fields
    )
    reply = clarify_resp.text.strip()
    total_latency = (extract_resp.latency_ms or 0) + (clarify_resp.latency_ms or 0)

    append_turn(session_id, req.message, reply)
    return ChatResponse(
        session_id=session_id,
        reply=reply,
        extracted_features=so_far,
        missing_fields=extracted.missing_fields,
        assumptions=extracted.assumptions,
        provider=provider.name,
        model=provider.model,
        latency_ms=round(total_latency, 1),
    )


@router.delete("/chat/{session_id}")
@limiter.limit(settings.RATE_LIMIT_CHAT_DELETE)
async def reset_chat(request: Request, session_id: str, _=Depends(get_api_key)):
    clear_history(session_id)
    return {"ok": True, "session_id": session_id}
