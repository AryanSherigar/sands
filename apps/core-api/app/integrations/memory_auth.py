"""Google ID-token auth for calls to the memory service.

When the memory service runs behind Cloud Run IAM, each request carries an ID
token for this service's account whose audience is the memory URL. The token
is fetched from the metadata server (or local credentials), cached until just
before it expires, and refreshed on demand. The Turn Resolution Service keeps an identical copy:
services never import each other.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Callable

import httpx
import structlog
from app.config import settings
from google.auth import exceptions as google_auth_exceptions
from google.auth import jwt as google_jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

logger = structlog.get_logger()

EVENT_MEMORY_ID_TOKEN_FETCH_FAILED = "memory_id_token_fetch_failed"
EXPIRY_MARGIN_SECONDS = 60
FALLBACK_LIFETIME_SECONDS = 300
HTTP_STATUS_UNAUTHORIZED = 401


class MemoryAuthError(httpx.HTTPError):
    """The ID token for the memory service could not be obtained."""


def fetch_google_id_token(audience: str) -> str:
    return google_id_token.fetch_id_token(google_requests.Request(), audience)


def _expiry_of(token: str) -> float:
    try:
        return float(google_jwt.decode(token, verify=False)["exp"])
    except (ValueError, KeyError, TypeError):
        return time.time() + FALLBACK_LIFETIME_SECONDS


class IdTokenAuth(httpx.Auth):
    def __init__(
        self,
        audience: str,
        fetch_token: Callable[[str], str] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._audience = audience
        self._fetch_token = fetch_token
        self._clock = clock
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        request.headers["Authorization"] = f"Bearer {await self._current_token()}"
        response = yield request
        if response.status_code == HTTP_STATUS_UNAUTHORIZED:
            self._token = None

    async def _current_token(self) -> str:
        async with self._lock:
            if self._token is None or self._clock() >= self._expires_at:
                await self._refresh()
            return self._token

    async def _refresh(self) -> None:
        fetch = self._fetch_token or fetch_google_id_token
        loop = asyncio.get_running_loop()
        try:
            token = await loop.run_in_executor(None, fetch, self._audience)
        except google_auth_exceptions.GoogleAuthError as error:
            logger.error(
                EVENT_MEMORY_ID_TOKEN_FETCH_FAILED, error_type=type(error).__name__
            )
            raise MemoryAuthError("memory ID token unavailable") from error
        self._token = token
        self._expires_at = _expiry_of(token) - EXPIRY_MARGIN_SECONDS


def build_memory_auth() -> httpx.Auth | None:
    if not settings.is_memory_iam_auth_enabled:
        return None
    return IdTokenAuth(settings.memory_url)
