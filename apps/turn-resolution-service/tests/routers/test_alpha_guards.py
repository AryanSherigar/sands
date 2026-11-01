"""Alpha mode locks voice, studio assistant and both session routes."""

import uuid

import pytest
from app.config import settings
from httpx import AsyncClient

DISABLED_CODE = "alpha_feature_disabled"
LOCKED_ROUTES = [
    ("POST", "/v1/voice/transcribe"),
    ("POST", "/v1/studio/assistant"),
    ("GET", f"/v1/session/{uuid.uuid4()}/spectate?share_token=x"),
    ("GET", f"/v1/session/{uuid.uuid4()}/notifications?participant_id={uuid.uuid4()}"),
]


@pytest.fixture
def alpha_on(monkeypatch) -> None:
    monkeypatch.setattr(settings, "is_alpha_mode", True)
    monkeypatch.setattr(settings, "alpha_scenario_id", uuid.uuid4())


def is_alpha_refusal(response) -> bool:
    return response.status_code == 403 and response.json().get("code") == DISABLED_CODE


@pytest.mark.parametrize(("method", "path"), LOCKED_ROUTES)
async def test_locked_route_is_refused_in_alpha_mode(
    async_client: AsyncClient, alpha_on, method, path
) -> None:
    headers = {"X-Dev-User-Id": str(uuid.uuid4())}

    response = await async_client.request(method, path, headers=headers)

    assert is_alpha_refusal(response)


@pytest.mark.parametrize(("method", "path"), LOCKED_ROUTES)
async def test_locked_route_refuses_before_authentication(
    async_client: AsyncClient, alpha_on, method, path
) -> None:
    response = await async_client.request(method, path)

    assert is_alpha_refusal(response)


@pytest.mark.parametrize(("method", "path"), LOCKED_ROUTES)
async def test_locked_route_is_not_refused_when_alpha_is_off(
    async_client: AsyncClient, method, path
) -> None:
    headers = {"X-Dev-User-Id": str(uuid.uuid4())}

    response = await async_client.request(method, path, headers=headers)

    assert not is_alpha_refusal(response)
