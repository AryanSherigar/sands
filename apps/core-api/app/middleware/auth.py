import uuid
from typing import Annotated

import jwt
import structlog
from app.config import settings
from app.db.connection import get_db_session
from app.db.models.user import User
from app.exceptions.auth_exceptions import InvalidTokenError
from app.repositories.user_repo import UserRepo
from app.services.auth_service import AuthService
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer(auto_error=False)
optional_security = HTTPBearer(auto_error=False)


def _bind_user_context(user: User) -> None:
    structlog.contextvars.bind_contextvars(user_id=str(user.user_id))


def _build_auth_service(session: AsyncSession) -> AuthService:
    return AuthService(UserRepo(session))


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> User:
    auth_service = _build_auth_service(session)
    if settings.environment in ("development", "testing"):
        dev_user_id = request.headers.get("x-dev-user-id")
        if dev_user_id:
            try:
                user_uuid = uuid.UUID(dev_user_id)
                user = await auth_service.get_or_create_dev_user(user_uuid)
                _bind_user_context(user)
                return user
            except ValueError:
                pass
            raise InvalidTokenError("Dev user not found or invalid UUID format")

    if not credentials:
        raise InvalidTokenError("Not authenticated")

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            raise InvalidTokenError("Invalid token type")

        user = await auth_service.get_user_for_access_token(
            uuid.UUID(payload.get("sub")), payload.get("token_version")
        )
        if user is None:
            raise InvalidTokenError("Token revoked or user not found")

        _bind_user_context(user)
        return user
    except (jwt.InvalidTokenError, ValueError, TypeError) as err:
        raise InvalidTokenError("Invalid or expired access token") from err


async def get_optional_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(optional_security)
    ],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> User | None:
    auth_service = _build_auth_service(session)
    if settings.environment in ("development", "testing"):
        dev_user_id = request.headers.get("x-dev-user-id")
        if dev_user_id:
            try:
                user_uuid = uuid.UUID(dev_user_id)
                user = await auth_service.get_or_create_dev_user(user_uuid)
                _bind_user_context(user)
                return user
            except ValueError:
                pass

    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            return None

        user = await auth_service.get_user_for_access_token(
            uuid.UUID(payload.get("sub")), payload.get("token_version")
        )
        if user is None:
            return None

        _bind_user_context(user)
        return user
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
