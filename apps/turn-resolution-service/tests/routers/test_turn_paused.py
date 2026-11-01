"""The turn pause switch refuses /v1/turn before any quota or model work."""

import uuid

import pytest
from app.config import settings
from app.routers import turn as turn_router
from httpx import AsyncClient

PAUSED_CODE = "alpha_paused"
TURN_PATH = "/v1/turn"
HEALTH_PATH = "/health"


@pytest.fixture
def paused(monkeypatch) -> None:
    monkeypatch.setattr(settings, "is_turns_suspended", True)


@pytest.fixture
def pipeline_must_not_run(monkeypatch) -> list[str]:
    calls: list[str] = []

    def fail(*args: object, **kwargs: object) -> None:
        calls.append("run_turn")
        raise AssertionError("run_turn must not be reached while paused")

    monkeypatch.setattr(turn_router, "run_turn", fail)
    return calls


def is_paused_refusal(response) -> bool:
    return response.status_code == 503 and response.json().get("code") == PAUSED_CODE


async def test_paused_turn_returns_503_alpha_paused(
    async_client: AsyncClient, paused, pipeline_must_not_run
) -> None:
    headers = {"X-Dev-User-Id": str(uuid.uuid4())}

    response = await async_client.post(TURN_PATH, json={}, headers=headers)

    assert is_paused_refusal(response)
    assert pipeline_must_not_run == []


async def test_paused_turn_refuses_before_authentication(
    async_client: AsyncClient, paused, pipeline_must_not_run
) -> None:
    response = await async_client.post(TURN_PATH, json={})

    assert is_paused_refusal(response)
    assert pipeline_must_not_run == []


async def test_other_routes_are_unaffected_while_paused(
    async_client: AsyncClient, paused
) -> None:
    response = await async_client.get(HEALTH_PATH)

    assert response.status_code == 200


async def test_turn_is_not_refused_when_not_paused(async_client: AsyncClient) -> None:
    response = await async_client.post(TURN_PATH, json={})

    assert not is_paused_refusal(response)
