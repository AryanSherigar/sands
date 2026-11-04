from datetime import UTC, datetime

import pytest
from app.db.models.user import User
from httpx import AsyncClient
from sqlalchemy import select
from tests.stats_factories import make_user


@pytest.fixture
async def test_user(db_session) -> User:
    return await make_user(db_session)


async def _reload(db_session, user: User) -> User:
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_delete_me_requires_authentication(async_client: AsyncClient) -> None:
    response = await async_client.delete("/v1/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_me_flags_account_and_revokes_tokens(
    async_client: AsyncClient, db_session, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}
    version_before = test_user.token_version

    response = await async_client.delete("/v1/users/me", headers=headers)
    user = await _reload(db_session, test_user)

    assert response.status_code == 204
    assert user.deletion_requested_at is not None
    assert user.token_version == version_before + 1
    assert user.current_refresh_jti is None


@pytest.mark.asyncio
async def test_delete_me_twice_keeps_the_original_request_time(
    async_client: AsyncClient, db_session, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}
    await async_client.delete("/v1/users/me", headers=headers)
    first_requested_at = (await _reload(db_session, test_user)).deletion_requested_at

    response = await async_client.delete("/v1/users/me", headers=headers)

    assert response.status_code == 204
    assert (
        await _reload(db_session, test_user)
    ).deletion_requested_at == first_requested_at


@pytest.mark.asyncio
async def test_pending_deletion_hides_the_public_profile(
    async_client: AsyncClient, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}
    await async_client.delete("/v1/users/me", headers=headers)

    response = await async_client.get(f"/v1/users/{test_user.user_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_signing_in_during_grace_period_restores_the_account(
    async_client: AsyncClient, db_session
) -> None:
    user = User(
        display_name="Dev User",
        auth_provider_id="dev-firebase-id-123",
        deletion_requested_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.flush()

    response = await async_client.post(
        "/v1/auth/token", json={"firebase_id_token": "mock-dev-token"}
    )

    assert response.status_code == 200
    assert response.json()["is_account_restored"] is True
    assert (await _reload(db_session, user)).deletion_requested_at is None


@pytest.mark.asyncio
async def test_normal_sign_in_does_not_flag_a_restore(
    async_client: AsyncClient, db_session
) -> None:
    response = await async_client.post(
        "/v1/auth/token", json={"firebase_id_token": "mock-dev-token"}
    )

    assert response.status_code == 200
    assert response.json()["is_account_restored"] is False
    stored = (await db_session.execute(select(User))).scalars().first()
    assert stored is not None
