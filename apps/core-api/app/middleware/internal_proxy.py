"""Reject requests that didn't come through the frontend nginx proxy.

Enforced only when INTERNAL_PROXY_TOKEN is configured, so running this
service directly (uvicorn + Vite dev server) keeps working locally.
"""

import hmac
from collections.abc import Awaitable, Callable

import structlog
from app.config import settings
from app.services.rate_limit.policies import EXEMPT_PATHS
from fastapi import Request, Response
from fastapi.responses import JSONResponse

HEADER_INTERNAL_PROXY_TOKEN = "X-Internal-Proxy-Token"
EVENT_INTERNAL_PROXY_REJECTED = "internal_proxy_token_rejected"
FORBIDDEN_DETAIL = "Forbidden"

logger = structlog.get_logger()


def _has_valid_token(request: Request) -> bool:
    presented = request.headers.get(HEADER_INTERNAL_PROXY_TOKEN, "")
    return hmac.compare_digest(
        presented.encode(), settings.internal_proxy_token.encode()
    )


async def internal_proxy_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    is_gate_enabled = bool(settings.internal_proxy_token)
    if not is_gate_enabled or request.url.path in EXEMPT_PATHS:
        return await call_next(request)
    if not _has_valid_token(request):
        logger.warning(EVENT_INTERNAL_PROXY_REJECTED, path=request.url.path)
        return JSONResponse(status_code=403, content={"detail": FORBIDDEN_DETAIL})
    return await call_next(request)
