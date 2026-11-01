"""Browser authentication: the player's internal access JWT, validated statelessly.

NOTE: This service has no user table, so token_version cannot be checked; a
revoked session stays valid until its access token expires.
"""

from typing import Annotated
from uuid import UUID

import jwt
import structlog
from app.config import get_settings
from app.exceptions.auth_exceptions import InvalidTokenError
from app.models.auth import CurrentUser
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

DEV_USER_HEADER = "x-dev-user-id"
DEV_ENVIRONMENTS = ("development", "testing")
ACCESS_TOKEN_TYPE = "access"
REQUIRED_CLAIMS = ["exp", "sub"]

security = HTTPBearer(auto_error=False)


def _bind_user_context(user: CurrentUser) -> None:
    structlog.contextvars.bind_contextvars(user_id=str(user.user_id))


def _user_from_dev_header(request: Request) -> CurrentUser | None:
    if get_settings().environment not in DEV_ENVIRONMENTS:
        return None
    raw_user_id = request.headers.get(DEV_USER_HEADER)
    if not raw_user_id:
        return None
    try:
        return CurrentUser(user_id=UUID(raw_user_id))
    except ValueError as error:
        raise InvalidTokenError("Invalid UUID format in dev header") from error


def _user_from_token(token: str) -> CurrentUser:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": REQUIRED_CLAIMS},
        )
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            raise InvalidTokenError("Invalid token type")
        return CurrentUser(user_id=UUID(payload["sub"]))
    except (jwt.InvalidTokenError, ValueError, TypeError) as error:
        raise InvalidTokenError("Invalid or expired access token") from error


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> CurrentUser:
    user = _user_from_dev_header(request)
    if user is None:
        if credentials is None:
            raise InvalidTokenError("Not authenticated")
        user = _user_from_token(credentials.credentials)
    _bind_user_context(user)
    return user
