"""Integration tests for the internal-proxy shared-secret gate."""

from app.config import settings
from app.middleware.internal_proxy import HEADER_INTERNAL_PROXY_TOKEN
from httpx import AsyncClient

PROXY_TOKEN = "test-proxy-token"


async def test_gate_disabled_when_token_unset(
    async_client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "internal_proxy_token", "")

    assert (await async_client.get("/v1/music/defaults")).status_code == 200


async def test_missing_or_wrong_token_is_forbidden(
    async_client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "internal_proxy_token", PROXY_TOKEN)

    missing = await async_client.get("/v1/music/defaults")
    wrong = await async_client.get(
        "/v1/music/defaults", headers={HEADER_INTERNAL_PROXY_TOKEN: "nope"}
    )

    assert missing.status_code == 403
    assert wrong.status_code == 403


async def test_correct_token_passes(async_client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "internal_proxy_token", PROXY_TOKEN)

    response = await async_client.get(
        "/v1/music/defaults", headers={HEADER_INTERNAL_PROXY_TOKEN: PROXY_TOKEN}
    )

    assert response.status_code == 200


async def test_health_bypasses_gate(async_client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "internal_proxy_token", PROXY_TOKEN)

    assert (await async_client.get("/health")).status_code == 200
