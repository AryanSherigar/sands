"""Tests for the internal memory relay endpoint and its middleware exemptions."""

import pytest
from app.config import settings
from app.main import app as fastapi_app
from app.models.memory_relay import RelaySummary
from app.services.memory_relay_service import get_relay_service
from app.services.rate_limit.policies import is_exempt_request
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

RELAY_PATH = "/internal/memory/relay"
TOKEN_HEADER = "X-Internal-Service-Token"


class _StubRelay:
    def __init__(self) -> None:
        self.calls = 0

    async def deliver_pending(self) -> RelaySummary:
        self.calls += 1
        return RelaySummary(playthroughs_attempted=2, rows_delivered=5, rows_failed=1)


@pytest.fixture
def stub_relay(monkeypatch) -> _StubRelay:
    relay = _StubRelay()
    fastapi_app.dependency_overrides[get_relay_service] = lambda: relay
    yield relay
    fastapi_app.dependency_overrides.pop(get_relay_service, None)


async def test_correct_token_runs_a_pass_and_returns_the_summary(
    async_client: AsyncClient, stub_relay: _StubRelay, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "internal_service_token", "s3cret")

    response = await async_client.post(RELAY_PATH, headers={TOKEN_HEADER: "s3cret"})

    assert response.status_code == 200
    assert response.json() == {
        "playthroughs_attempted": 2,
        "rows_delivered": 5,
        "rows_failed": 1,
    }
    assert stub_relay.calls == 1


@pytest.mark.parametrize("headers", [{}, {TOKEN_HEADER: "wrong"}, {TOKEN_HEADER: ""}])
async def test_missing_or_wrong_token_is_401_and_runs_nothing(
    async_client: AsyncClient, stub_relay: _StubRelay, monkeypatch, headers
) -> None:
    monkeypatch.setattr(settings, "internal_service_token", "s3cret")

    response = await async_client.post(RELAY_PATH, headers=headers)

    assert response.status_code == 401
    assert stub_relay.calls == 0


@pytest.mark.parametrize(
    "headers", [{}, {TOKEN_HEADER: ""}, {TOKEN_HEADER: "anything"}]
)
async def test_unset_token_disables_the_endpoint_even_for_an_empty_header(
    async_client: AsyncClient, stub_relay: _StubRelay, monkeypatch, headers
) -> None:
    monkeypatch.setattr(settings, "internal_service_token", "")

    response = await async_client.post(RELAY_PATH, headers=headers)

    assert response.status_code == 503
    assert stub_relay.calls == 0


async def test_internal_path_is_exempt_from_the_proxy_gate_but_v1_is_not(
    async_client: AsyncClient, stub_relay: _StubRelay, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "internal_proxy_token", "proxy-secret")
    monkeypatch.setattr(settings, "internal_service_token", "s3cret")

    internal = await async_client.post(RELAY_PATH, headers={TOKEN_HEADER: "s3cret"})
    gated = await async_client.post("/v1/turn", json={})

    assert internal.status_code == 200
    assert gated.status_code == 403


async def test_internal_paths_are_exempt_from_burst_limits_but_v1_paths_are_not() -> (
    None
):
    assert is_exempt_request("POST", RELAY_PATH)
    assert is_exempt_request("GET", "/health")
    assert not is_exempt_request("POST", "/v1/turn")
    assert not is_exempt_request("POST", "/internalx/memory/relay")
