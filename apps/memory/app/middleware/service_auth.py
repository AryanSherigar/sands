"""Service-to-service authentication for the memory service.

verify_service_identity is the single dependency every authenticated route
depends on. In dev mode the caller name is a trusted header; in iam mode the
caller presents a Google-signed ID token (a Cloud Run service account) whose
audience is this service's URL and whose email must be on the allowlist.
GET /health depends on neither branch and is always unauthenticated.
"""

import asyncio
import time

import structlog
from app.config import Settings, get_settings
from app.exceptions.auth_exceptions import (
    ServiceCallerNotAllowedError,
    ServiceTokenInvalidError,
    ServiceUnauthenticatedError,
)
from fastapi import Request
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

logger = structlog.get_logger()

EVENT_SERVICE_TOKEN_REJECTED = "service_token_rejected"
DEV_CALLER_HEADER = "x-dev-service-name"
DEV_CALLER_DEFAULT = "dev-caller"
BEARER_PREFIX = "bearer "
AUTHORIZATION_HEADER = "authorization"
MAX_CACHED_TOKENS = 64

# NOTE: Verifying a token fetches Google's signing certificates over the
# network. Callers reuse one token for about an hour, so verified claims are
# kept until the token's own expiry; the allowlist is still checked per request.
_verified_claims: dict[str, dict[str, object]] = {}


def verify_google_id_token(token: str, audience: str) -> dict[str, object]:
    return google_id_token.verify_oauth2_token(
        token, google_requests.Request(), audience
    )


def clear_verified_claims() -> None:
    _verified_claims.clear()


async def verify_service_identity(request: Request) -> str:
    settings = get_settings()
    if settings.memory_auth_mode == "dev":
        return _verify_dev(request)
    return await _verify_iam(request, settings)


def _verify_dev(request: Request) -> str:
    return request.headers.get(DEV_CALLER_HEADER, DEV_CALLER_DEFAULT)


async def _verify_iam(request: Request, settings: Settings) -> str:
    token = _bearer_token(request)
    claims = await _claims_for(token, settings.memory_iam_audience)
    caller = _verified_email(claims)
    if caller not in settings.allowed_caller_emails:
        raise ServiceCallerNotAllowedError()
    return caller


def _bearer_token(request: Request) -> str:
    header = request.headers.get(AUTHORIZATION_HEADER, "")
    if not header.lower().startswith(BEARER_PREFIX):
        raise ServiceUnauthenticatedError()
    token = header[len(BEARER_PREFIX) :].strip()
    if not token:
        raise ServiceUnauthenticatedError()
    return token


async def _claims_for(token: str, audience: str) -> dict[str, object]:
    cached = _verified_claims.get(token)
    if cached is not None and _is_unexpired(cached):
        return cached
    try:
        claims = await asyncio.to_thread(verify_google_id_token, token, audience)
    except (ValueError, google_auth_exceptions.GoogleAuthError) as error:
        logger.warning(EVENT_SERVICE_TOKEN_REJECTED, error_type=type(error).__name__)
        raise ServiceTokenInvalidError() from error
    _remember(token, claims)
    return claims


def _is_unexpired(claims: dict[str, object]) -> bool:
    expires_at = claims.get("exp")
    return isinstance(expires_at, int | float) and expires_at > time.time()


def _remember(token: str, claims: dict[str, object]) -> None:
    if not _is_unexpired(claims):
        return
    if len(_verified_claims) >= MAX_CACHED_TOKENS:
        _verified_claims.clear()
    _verified_claims[token] = claims


def _verified_email(claims: dict[str, object]) -> str:
    email = claims.get("email")
    if not isinstance(email, str) or claims.get("email_verified") is not True:
        raise ServiceTokenInvalidError()
    return email
