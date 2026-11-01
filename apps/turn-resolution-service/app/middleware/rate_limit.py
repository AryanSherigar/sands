"""Sliding-window burst limits applied to every request by route group."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from app.config import settings
from app.exceptions.rate_limit_exceptions import (
    CODE_RATE_LIMITED,
    LimitPolicy,
    RateLimitExceededError,
)
from app.middleware.rate_limit_headers import (
    build_rate_limit_headers,
    build_rate_limit_response,
)
from app.services.rate_limit.burst_limit_service import (
    BurstLimitService,
    BurstOutcome,
)
from app.services.rate_limit.client_identity import resolve_client_identity
from app.services.rate_limit.exemption_service import get_exemption_service
from app.services.rate_limit.policies import is_exempt_request
from app.services.rate_limit.store import get_rate_limit_store
from fastapi import FastAPI, Request, Response

DependencyT = TypeVar("DependencyT")

RATE_LIMITED_MESSAGE = (
    "Too many requests. Please slow down and try again in {seconds} seconds."
)


def _resolve_dependency(
    app: FastAPI, dependency: Callable[[], DependencyT]
) -> DependencyT:
    """Middleware sits outside dependency injection, so honour test overrides by hand."""
    return app.dependency_overrides.get(dependency, dependency)()


def _build_service(app: FastAPI) -> BurstLimitService:
    store = _resolve_dependency(app, get_rate_limit_store)
    exemptions = _resolve_dependency(app, get_exemption_service)
    return BurstLimitService(store, exemptions)


def _to_error(outcome: BurstOutcome) -> RateLimitExceededError:
    retry_after = outcome.decision.retry_after_seconds
    return RateLimitExceededError(
        RATE_LIMITED_MESSAGE.format(seconds=retry_after),
        code=CODE_RATE_LIMITED,
        scope=outcome.policy.group,
        reset_at=datetime.now(UTC) + timedelta(seconds=retry_after),
        retry_after_seconds=retry_after,
        policy=LimitPolicy(outcome.policy.limit, outcome.policy.window_seconds),
    )


def _outcome_headers(outcome: BurstOutcome) -> dict[str, str]:
    return build_rate_limit_headers(
        outcome.policy.group,
        outcome.policy.limit,
        outcome.policy.window_seconds,
        outcome.decision.remaining,
        outcome.decision.reset_seconds,
    )


async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    method, path = request.method, request.url.path
    if not settings.is_rate_limit_enabled or is_exempt_request(method, path):
        return await call_next(request)

    service = _build_service(request.app)
    outcome = await service.check(resolve_client_identity(request), method, path)
    if outcome is None:
        return await call_next(request)
    if not outcome.decision.is_allowed:
        return build_rate_limit_response(_to_error(outcome))

    response = await call_next(request)
    response.headers.update(_outcome_headers(outcome))
    return response
