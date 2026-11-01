import uuid
from typing import Annotated

import jwt
import structlog
from app.config import settings
from app.db.connection import get_db_session
from app.exceptions.auth_exceptions import InvalidTokenError
from app.models.auth import CurrentUser
from app.repositories.user_repo import UserRepo
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer(auto_error=False)


def _bind_user_context(user: CurrentUser) -> None:
    structlog.contextvars.bind_contextvars(user_id=str(user.user_id))


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> CurrentUser:
    if settings.environment in ("development", "testing"):
        dev_user_id = request.headers.get("x-dev-user-id")
        if dev_user_id:
            try:
                user = CurrentUser(user_id=uuid.UUID(dev_user_id), token_version=1)
                _bind_user_context(user)
                return user
            except ValueError as err:
                raise InvalidTokenError("Invalid UUID format in dev header") from err

    if not credentials:
        raise InvalidTokenError("Not authenticated")

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            raise InvalidTokenError("Invalid token type")

        user_id = payload.get("sub")
        token_version = payload.get("token_version")

        user = CurrentUser(user_id=uuid.UUID(user_id), token_version=token_version)
    except (jwt.InvalidTokenError, ValueError, TypeError, ValidationError) as err:
        raise InvalidTokenError("Invalid or expired access token") from err

    db_user = await UserRepo(session).get_by_id(user.user_id)
    if db_user is None or db_user.token_version != user.token_version:
        raise InvalidTokenError("Token revoked or user not found")

    _bind_user_context(user)
    return user
