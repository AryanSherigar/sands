"""Integration tests for TRS's internal-proxy shared-secret gate."""

from app.config import settings
from app.middleware.internal_proxy import HEADER_INTERNAL_PROXY_TOKEN
from httpx import AsyncClient

PROXY_TOKEN = "test-proxy-token"


async def test_request_without_token_is_forbidden(
    async_client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "internal_proxy_token", PROXY_TOKEN)

    response = await async_client.post("/v1/turn", json={})

    assert response.status_code == 403


async def test_request_with_token_reaches_the_app(
    async_client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "internal_proxy_token", PROXY_TOKEN)

    response = await async_client.post(
        "/v1/turn", json={}, headers={HEADER_INTERNAL_PROXY_TOKEN: PROXY_TOKEN}
    )

    assert response.status_code == 401


async def test_health_bypasses_gate(async_client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "internal_proxy_token", PROXY_TOKEN)

    assert (await async_client.get("/health")).status_code == 200
