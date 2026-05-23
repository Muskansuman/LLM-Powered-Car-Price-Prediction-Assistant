import logging

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import routes_auth, routes_chat, routes_predict
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import limiter
from app.middleware.logging_middleware import LoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

app = FastAPI(title="Car Price Prediction API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(LoggingMiddleware)

app.include_router(routes_auth.router, tags=["Auth"])
app.include_router(routes_predict.router, tags=["Prediction"])
app.include_router(routes_chat.router, tags=["Chat"])

Instrumentator().instrument(app).expose(app)

register_exception_handlers(app)


@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok"}
