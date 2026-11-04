import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from app.config import settings
from app.exceptions.auth_exceptions import InvalidTokenError
from app.repositories.user_repo import UserRepo
from app.services.auth_service import AuthService
from firebase_admin import exceptions as firebase_exceptions
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_jwt_generation(db_session: AsyncSession):
    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service._upsert_user("test-123", "Test User")

    access_token = auth_service.generate_access_token(user)
    refresh_token = await auth_service.generate_refresh_token(user)

    assert access_token is not None
    assert refresh_token is not None

    import jwt
    from app.config import settings

    payload = jwt.decode(
        access_token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert payload["sub"] == str(user.user_id)
    assert payload["type"] == "access"
    assert payload["token_version"] == 1


@pytest.mark.asyncio
@patch("app.services.auth_service.firebase_auth.verify_id_token")
async def test_verify_firebase_token_success(mock_verify, db_session: AsyncSession):
    mock_verify.return_value = {"uid": "firebase-uid-1", "name": "Firebase User"}

    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service.verify_firebase_token_and_upsert_user("valid_token")

    assert user.auth_provider_id == "firebase-uid-1"
    assert user.display_name == "Firebase User"


@pytest.mark.asyncio
@patch("app.services.auth_service.firebase_auth.verify_id_token")
async def test_verify_firebase_token_failure(mock_verify, db_session: AsyncSession):
    mock_verify.side_effect = ValueError("Expired token")

    auth_service = AuthService(UserRepo(db_session))
    with pytest.raises(InvalidTokenError) as exc_info:
        await auth_service.verify_firebase_token_and_upsert_user("invalid_token")

    assert "Firebase token verification failed" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.auth_service.firebase_auth.verify_id_token")
async def test_verify_firebase_token_failure_wraps_firebase_error(
    mock_verify, db_session: AsyncSession
):
    mock_verify.side_effect = firebase_exceptions.FirebaseError(
        code="INVALID_ARGUMENT", message="bad token"
    )

    auth_service = AuthService(UserRepo(db_session))
    with pytest.raises(InvalidTokenError) as exc_info:
        await auth_service.verify_firebase_token_and_upsert_user("invalid_token")

    assert "Firebase token verification failed" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.auth_service.settings.environment", "production")
async def test_mock_dev_token_rejected_in_production(db_session: AsyncSession):
    """Regression test: the dev/test auth bypass must never be reachable in
    production, even with the exact "mock-dev-token" sentinel value."""
    auth_service = AuthService(UserRepo(db_session))
    with pytest.raises(InvalidTokenError):
        await auth_service.verify_firebase_token_and_upsert_user("mock-dev-token")


@pytest.mark.asyncio
async def test_refresh_tokens_rotates_jti_and_returns_new_tokens(
    db_session: AsyncSession,
):
    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service._upsert_user("refresh-rotate-1", "Rotate User")
    old_refresh_token = await auth_service.generate_refresh_token(user)

    access_token, new_refresh_token, refreshed_user = await auth_service.refresh_tokens(
        old_refresh_token
    )

    assert access_token
    assert new_refresh_token != old_refresh_token
    assert refreshed_user.user_id == user.user_id


@pytest.mark.asyncio
async def test_refresh_tokens_rejects_stale_jti_after_the_grace_window(
    db_session: AsyncSession,
):
    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service._upsert_user("refresh-stale-1", "Stale User")
    old_refresh_token = await auth_service.generate_refresh_token(user)
    await auth_service.generate_refresh_token(user)
    user.refresh_rotated_at = datetime.now(timezone.utc) - timedelta(
        seconds=settings.refresh_rotation_grace_seconds + 1
    )

    with pytest.raises(InvalidTokenError):
        await auth_service.refresh_tokens(old_refresh_token)


@pytest.mark.asyncio
async def test_refresh_replay_inside_the_grace_window_keeps_the_current_session(
    db_session: AsyncSession,
):
    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service._upsert_user("refresh-grace-1", "Grace User")
    first_token = await auth_service.generate_refresh_token(user)
    _, second_token, _ = await auth_service.refresh_tokens(first_token)
    current_jti = user.current_refresh_jti

    access_token, replay_token, _ = await auth_service.refresh_tokens(first_token)

    assert access_token
    assert user.current_refresh_jti == current_jti
    payload = jwt.decode(
        replay_token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert payload["jti"] == current_jti
    _, third_token, _ = await auth_service.refresh_tokens(second_token)
    assert third_token


@pytest.mark.asyncio
async def test_a_token_two_rotations_old_is_rejected_even_inside_the_window(
    db_session: AsyncSession,
):
    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service._upsert_user("refresh-grace-2", "Grace Two")
    first_token = await auth_service.generate_refresh_token(user)
    _, second_token, _ = await auth_service.refresh_tokens(first_token)
    await auth_service.refresh_tokens(second_token)

    with pytest.raises(InvalidTokenError):
        await auth_service.refresh_tokens(first_token)


@pytest.mark.asyncio
async def test_refresh_tokens_rejects_revoked_token_version(db_session: AsyncSession):
    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service._upsert_user("refresh-revoked-1", "Revoked User")
    refresh_token = await auth_service.generate_refresh_token(user)

    user.token_version += 1
    await auth_service.user_repo.update(user)

    with pytest.raises(InvalidTokenError):
        await auth_service.refresh_tokens(refresh_token)


@pytest.mark.asyncio
async def test_refresh_tokens_rejects_wrong_token_type(db_session: AsyncSession):
    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service._upsert_user("refresh-wrong-type-1", "Wrong Type User")
    access_token = auth_service.generate_access_token(user)

    with pytest.raises(InvalidTokenError):
        await auth_service.refresh_tokens(access_token)


@pytest.mark.asyncio
async def test_get_or_create_dev_user_creates_and_persists(db_session: AsyncSession):
    auth_service = AuthService(UserRepo(db_session))
    new_id = uuid.uuid4()

    user = await auth_service.get_or_create_dev_user(new_id)

    assert user.user_id == new_id
    assert user.display_name == "Dev User"

    fetched = await auth_service.user_repo.get_by_id(new_id)
    assert fetched is not None


@pytest.mark.asyncio
async def test_get_or_create_dev_user_returns_existing(db_session: AsyncSession):
    auth_service = AuthService(UserRepo(db_session))
    existing_id = uuid.uuid4()
    created = await auth_service.get_or_create_dev_user(existing_id)

    fetched_again = await auth_service.get_or_create_dev_user(existing_id)

    assert fetched_again.user_id == created.user_id


@pytest.mark.asyncio
async def test_get_user_for_access_token_returns_none_on_revoked_version(
    db_session: AsyncSession,
):
    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service._upsert_user("access-revoked-1", "Access Revoked User")

    result = await auth_service.get_user_for_access_token(
        user.user_id, user.token_version + 1
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_user_for_access_token_returns_user_on_valid_version(
    db_session: AsyncSession,
):
    auth_service = AuthService(UserRepo(db_session))
    user = await auth_service._upsert_user("access-valid-1", "Access Valid User")

    result = await auth_service.get_user_for_access_token(
        user.user_id, user.token_version
    )

    assert result is not None
    assert result.user_id == user.user_id


@pytest.mark.asyncio
async def test_new_accounts_throttled_per_ip_but_existing_users_sign_in(
    db_session: AsyncSession, rate_limit_enabled, monkeypatch
):
    from app.config import settings
    from app.exceptions.rate_limit_exceptions import RateLimitExceededError
    from app.services.rate_limit.quota_service import QuotaService

    monkeypatch.setattr(settings, "new_accounts_per_ip_per_day", 1)
    auth_service = AuthService(UserRepo(db_session), QuotaService(rate_limit_enabled))
    ip = "203.0.113.50"
    existing = await auth_service._upsert_user(f"uid-{uuid.uuid4()}", "First", ip)

    with pytest.raises(RateLimitExceededError):
        await auth_service._upsert_user(f"uid-{uuid.uuid4()}", "Second", ip)

    again = await auth_service._upsert_user(existing.auth_provider_id, "First", ip)
    assert again.user_id == existing.user_id
