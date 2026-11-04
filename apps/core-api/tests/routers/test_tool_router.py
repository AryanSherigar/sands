"""Integration tests for the scenario tools endpoints."""

import uuid

import httpx
import pytest
from app.repositories.user_repo import UserRepo
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.fixture
def headers(dev_user):
    return {"x-dev-user-id": str(dev_user.user_id)}


@pytest.fixture
async def master_scenario_id(async_client: httpx.AsyncClient, headers) -> str:
    response = await async_client.post(
        "/v1/scenarios",
        json={"title": "Night Desk", "mode": "master", "complexity_tier": "master"},
        headers=headers,
    )
    return response.json()["scenario_id"]


async def test_get_tools_defaults_to_empty(
    async_client: httpx.AsyncClient, headers, master_scenario_id: str
):
    response = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/tools", headers=headers
    )

    assert response.status_code == 200
    assert response.json() == {
        "enabled_tools": [],
        "auto_enabled": [],
        "inert_data": {},
    }


async def test_put_tools_auto_enables_and_scenario_response_reflects_it(
    async_client: httpx.AsyncClient, headers, master_scenario_id: str
):
    response = await async_client.put(
        f"/v1/scenarios/{master_scenario_id}/tools",
        json={"enabled_tools": ["atmosphere"]},
        headers=headers,
    )
    scenario = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}", headers=headers
    )

    assert response.status_code == 200
    assert response.json()["enabled_tools"] == ["status_hud", "atmosphere"]
    assert response.json()["auto_enabled"] == ["status_hud"]
    assert scenario.json()["enabled_tools"] == ["status_hud", "atmosphere"]


async def test_put_unknown_tool_is_422(
    async_client: httpx.AsyncClient, headers, master_scenario_id: str
):
    response = await async_client.put(
        f"/v1/scenarios/{master_scenario_id}/tools",
        json={"enabled_tools": ["teleporter"]},
        headers=headers,
    )

    assert response.status_code == 422


async def test_patch_scenario_ignores_enabled_tools(
    async_client: httpx.AsyncClient, headers, master_scenario_id: str
):
    await async_client.patch(
        f"/v1/scenarios/{master_scenario_id}",
        json={"title": "Night Desk 2", "enabled_tools": ["composure"]},
        headers=headers,
    )
    response = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/tools", headers=headers
    )

    assert response.json()["enabled_tools"] == []


async def test_disabling_required_tool_is_409(
    async_client: httpx.AsyncClient, headers, master_scenario_id: str
):
    url = f"/v1/scenarios/{master_scenario_id}/tools"
    await async_client.put(url, json={"enabled_tools": ["atmosphere"]}, headers=headers)

    response = await async_client.put(
        url, json={"enabled_tools": ["atmosphere"]}, headers=headers
    )

    assert response.status_code == 409
    assert "atmosphere" in response.json()["detail"]


async def test_other_user_cannot_read_tools(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    master_scenario_id: str,
):
    stranger = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Stranger"
    )

    response = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/tools",
        headers={"x-dev-user-id": str(stranger.user_id)},
    )

    assert response.status_code in (403, 404)


async def test_tool_not_enabled_error_body_carries_machine_readable_code(
    async_client: httpx.AsyncClient, headers, master_scenario_id: str
):
    from app.exceptions.tool_exceptions import ToolNotEnabledError
    from app.main import app
    from fastapi import APIRouter

    probe = APIRouter()

    @probe.get("/__probe/tool-not-enabled")
    async def raise_tool_not_enabled() -> None:
        raise ToolNotEnabledError("atmosphere")

    app.include_router(probe)

    response = await async_client.get("/__probe/tool-not-enabled", headers=headers)

    assert response.status_code == 409
    assert response.json()["code"] == "tool_not_enabled"
    assert "atmosphere" in response.json()["detail"]
