"""Shared SlowAPI limiter (per-client IP, proxy-aware for Render / nginx)."""

from starlette.requests import Request

from slowapi import Limiter
from slowapi.util import get_remote_address


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)
