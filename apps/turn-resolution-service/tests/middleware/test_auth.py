"""Unit tests for get_current_user's JWT decode + token_version check.

Malformed claims must raise InvalidTokenError (401), never escape as a raw
TypeError/ValueError/ValidationError (500). A token whose token_version no
longer matches the DB (revoked/rotated) must also be rejected -- this is the
cross-service revocation-parity fix: Core API already enforced this via
get_user_for_access_token; TRS did not.
"""

import uuid

import jwt
import pytest
from app.config import settings
from app.db.models.user import User
from app.exceptions.auth_exceptions import InvalidTokenError
from app.middleware.auth import get_current_user
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request


def _request() -> Request:
    return Request({"type": "http", "headers": []})


def _credentials_for(payload: dict[str, object]) -> HTTPAuthorizationCredentials:
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def _seed_user(db_session: AsyncSession, token_version: int = 1) -> User:
    user = User(
        auth_provider_id=f"auth-{uuid.uuid4()}",
        display_name="Test User",
        token_version=token_version,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_get_current_user_accepts_valid_token(db_session: AsyncSession) -> None:
    user = await _seed_user(db_session, token_version=1)
    credentials = _credentials_for(
        {"sub": str(user.user_id), "token_version": 1, "type": "access"}
    )

    result = await get_current_user(_request(), credentials, db_session)

    assert result.user_id == user.user_id
    assert result.token_version == 1


@pytest.mark.asyncio
async def test_get_current_user_rejects_stale_token_version(
    db_session: AsyncSession,
) -> None:
    user = await _seed_user(db_session, token_version=2)
    credentials = _credentials_for(
        {"sub": str(user.user_id), "token_version": 1, "type": "access"}
    )

    with pytest.raises(InvalidTokenError):
        await get_current_user(_request(), credentials, db_session)


@pytest.mark.asyncio
async def test_get_current_user_rejects_unknown_user(db_session: AsyncSession) -> None:
    credentials = _credentials_for(
        {"sub": str(uuid.uuid4()), "token_version": 1, "type": "access"}
    )

    with pytest.raises(InvalidTokenError):
        await get_current_user(_request(), credentials, db_session)


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_sub(db_session: AsyncSession) -> None:
    credentials = _credentials_for({"token_version": 1, "type": "access"})

    with pytest.raises(InvalidTokenError):
        await get_current_user(_request(), credentials, db_session)


@pytest.mark.asyncio
async def test_get_current_user_rejects_non_uuid_sub(db_session: AsyncSession) -> None:
    credentials = _credentials_for(
        {"sub": "not-a-uuid", "token_version": 1, "type": "access"}
    )

    with pytest.raises(InvalidTokenError):
        await get_current_user(_request(), credentials, db_session)


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_token_version(
    db_session: AsyncSession,
) -> None:
    credentials = _credentials_for({"sub": str(uuid.uuid4()), "type": "access"})

    with pytest.raises(InvalidTokenError):
        await get_current_user(_request(), credentials, db_session)


@pytest.mark.asyncio
async def test_get_current_user_rejects_wrong_type_token_version(
    db_session: AsyncSession,
) -> None:
    credentials = _credentials_for(
        {"sub": str(uuid.uuid4()), "token_version": "not-a-number", "type": "access"}
    )

    with pytest.raises(InvalidTokenError):
        await get_current_user(_request(), credentials, db_session)
