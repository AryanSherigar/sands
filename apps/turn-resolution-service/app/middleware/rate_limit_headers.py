"""429/503 bodies and IETF RateLimit / RateLimit-Policy headers.

Header syntax follows draft-ietf-httpapi-ratelimit-headers (structured
fields): RateLimit-Policy: "<scope>";q=<quota>;w=<window>, and
RateLimit: "<scope>";r=<remaining>;t=<seconds-to-reset>.
"""

from app.exceptions.rate_limit_exceptions import (
    QuotaStoreUnavailableError,
    RateLimitExceededError,
)
from app.models.rate_limit import RateLimitErrorResponse
from fastapi.responses import JSONResponse

HEADER_RETRY_AFTER = "Retry-After"
HEADER_RATE_LIMIT = "RateLimit"
HEADER_RATE_LIMIT_POLICY = "RateLimit-Policy"


def build_rate_limit_headers(
    scope: str, limit: int, window_seconds: int, remaining: int, reset_seconds: int
) -> dict[str, str]:
    return {
        HEADER_RATE_LIMIT_POLICY: f'"{scope}";q={limit};w={window_seconds}',
        HEADER_RATE_LIMIT: f'"{scope}";r={remaining};t={reset_seconds}',
    }


def build_rate_limit_response(error: RateLimitExceededError) -> JSONResponse:
    headers: dict[str, str] = {}
    if error.retry_after_seconds is not None:
        headers[HEADER_RETRY_AFTER] = str(error.retry_after_seconds)
    if error.policy is not None:
        headers |= build_rate_limit_headers(
            error.scope,
            error.policy.limit,
            error.policy.window_seconds,
            error.policy.remaining,
            error.retry_after_seconds or 0,
        )
    body = RateLimitErrorResponse(
        detail=error.message,
        code=error.code,
        scope=error.scope,
        reset_at=error.reset_at,
    )
    return JSONResponse(
        status_code=error.status_code,
        content=body.model_dump(mode="json"),
        headers=headers,
    )


def build_quota_unavailable_response(error: QuotaStoreUnavailableError) -> JSONResponse:
    body = RateLimitErrorResponse(
        detail=error.message, code=error.code, scope=error.scope
    )
    return JSONResponse(
        status_code=error.status_code, content=body.model_dump(mode="json")
    )
