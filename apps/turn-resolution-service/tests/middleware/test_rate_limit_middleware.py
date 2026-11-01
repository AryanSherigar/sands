"""Integration tests for TRS's burst rate-limit middleware on the real app."""

import uuid

from app.config import settings
from httpx import AsyncClient


def _dev_headers() -> dict[str, str]:
    return {"X-Dev-User-Id": str(uuid.uuid4())}


async def test_turn_group_limited_per_user(
    async_client: AsyncClient, rate_limit_enabled, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_turn_per_window", 0)

    response = await async_client.post("/v1/turn", json={}, headers=_dev_headers())

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert response.json()["scope"] == "turn"
    assert response.headers["RateLimit-Policy"] == '"turn";q=0;w=60'
    assert int(response.headers["Retry-After"]) >= 1


async def test_anonymous_spectators_limited_per_ip(
    async_client: AsyncClient, rate_limit_enabled, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_anonymous_per_window", 1)
    path = f"/v1/session/{uuid.uuid4()}/spectate?share_token=bad"

    first = await async_client.get(path)
    second = await async_client.get(path)

    assert first.status_code != 429
    assert second.status_code == 429
    assert second.json()["scope"] == "anonymous"


async def test_health_is_never_limited(
    async_client: AsyncClient, rate_limit_enabled, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_anonymous_per_window", 0)

    assert (await async_client.get("/health")).status_code == 200
