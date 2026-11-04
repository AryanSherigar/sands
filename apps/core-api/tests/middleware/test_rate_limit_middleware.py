"""Integration tests for the burst rate-limit middleware on the real app."""

import uuid

from app.config import settings
from app.repositories.user_repo import UserRepo
from app.services.rate_limit.store import PostgresRateLimitStore
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

ANONYMOUS_PATH = "/v1/music/defaults"


async def _dev_headers(db_session: AsyncSession, auth_provider_id: str | None = None):
    user = await UserRepo(db_session).create(
        auth_provider_id=auth_provider_id or f"uid-{uuid.uuid4()}",
        display_name="Limited User",
    )
    return {"x-dev-user-id": str(user.user_id)}


async def test_anonymous_requests_limited_with_contract(
    async_client: AsyncClient, rate_limit_enabled, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_anonymous_per_window", 2)

    statuses = [(await async_client.get(ANONYMOUS_PATH)).status_code for _ in range(2)]
    rejected = await async_client.get(ANONYMOUS_PATH)

    assert statuses == [200, 200]
    assert rejected.status_code == 429
    body = rejected.json()
    assert body["code"] == "rate_limited"
    assert body["scope"] == "anonymous"
    assert body["reset_at"]
    assert int(rejected.headers["Retry-After"]) >= 1
    assert rejected.headers["RateLimit-Policy"] == '"anonymous";q=2;w=60'
    assert rejected.headers["RateLimit"].startswith('"anonymous";r=0;')


async def test_successful_response_carries_rate_limit_headers(
    async_client: AsyncClient, rate_limit_enabled
) -> None:
    response = await async_client.get(ANONYMOUS_PATH)

    assert response.status_code == 200
    assert response.headers["RateLimit-Policy"].startswith('"anonymous";q=')


async def test_authenticated_users_have_separate_buckets(
    async_client: AsyncClient, db_session, rate_limit_enabled, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_read_per_window", 1)
    first_user = await _dev_headers(db_session)
    second_user = await _dev_headers(db_session)

    assert (
        await async_client.get("/v1/users/me", headers=first_user)
    ).status_code == 200
    assert (
        await async_client.get("/v1/users/me", headers=first_user)
    ).status_code == 429
    assert (
        await async_client.get("/v1/users/me", headers=second_user)
    ).status_code == 200


async def test_exempt_user_skips_per_user_limit(
    async_client: AsyncClient, db_session, rate_limit_enabled, monkeypatch
) -> None:
    exempt_uid = f"admin-{uuid.uuid4()}"
    monkeypatch.setattr(settings, "rate_limit_read_per_window", 1)
    monkeypatch.setattr(settings, "rate_limit_exempt_firebase_uids", exempt_uid)
    headers = await _dev_headers(db_session, exempt_uid)

    for _ in range(3):
        response = await async_client.get("/v1/users/me", headers=headers)
        assert response.status_code == 200


async def test_ip_ceiling_applies_to_authenticated_traffic(
    async_client: AsyncClient, db_session, rate_limit_enabled, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_ip_ceiling_per_window", 1)
    headers = await _dev_headers(db_session)

    await async_client.get("/v1/users/me", headers=headers)
    rejected = await async_client.get("/v1/users/me", headers=headers)

    assert rejected.status_code == 429
    assert rejected.json()["scope"] == "ip_ceiling"


async def test_health_is_never_limited(
    async_client: AsyncClient, rate_limit_enabled, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_anonymous_per_window", 0)

    assert (await async_client.get("/health")).status_code == 200


async def test_store_failure_fails_open(
    async_client: AsyncClient,
    rate_limit_enabled: PostgresRateLimitStore,
    monkeypatch,
) -> None:
    async def _broken_hit(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    monkeypatch.setattr(rate_limit_enabled, "hit_sliding_window", _broken_hit)
    monkeypatch.setattr(settings, "rate_limit_anonymous_per_window", 0)

    assert (await async_client.get(ANONYMOUS_PATH)).status_code == 200


async def test_disabled_flag_bypasses_limits(
    async_client: AsyncClient, rate_limit_enabled, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "is_rate_limit_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_anonymous_per_window", 0)

    assert (await async_client.get(ANONYMOUS_PATH)).status_code == 200
