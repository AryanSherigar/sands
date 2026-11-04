"""Integration tests for the sheet rule REST endpoints."""

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
async def scenario_id(async_client: httpx.AsyncClient, headers) -> str:
    created = await async_client.post(
        "/v1/scenarios",
        json={"title": "Night Desk", "mode": "master", "complexity_tier": "master"},
        headers=headers,
    )
    return created.json()["scenario_id"]


async def _enable_rule_sheet(async_client, headers, scenario_id: str) -> None:
    await async_client.put(
        f"/v1/scenarios/{scenario_id}/tools",
        json={"enabled_tools": ["rule_sheet"]},
        headers=headers,
    )


def _payload(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "key": "r1",
        "number": 1,
        "text": "Never answer the phone twice.",
    }
    payload.update(overrides)
    return payload


async def test_create_while_the_tool_is_off_is_409_with_machine_code(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    response = await async_client.post(
        f"/v1/scenarios/{scenario_id}/sheet-rules", json=_payload(), headers=headers
    )

    assert response.status_code == 409
    assert response.json()["code"] == "tool_not_enabled"
    assert "rule_sheet" in response.json()["detail"]


async def test_create_list_get_update_delete_round_trip(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    await _enable_rule_sheet(async_client, headers, scenario_id)
    base = f"/v1/scenarios/{scenario_id}/sheet-rules"

    created = await async_client.post(base, json=_payload(), headers=headers)
    rule_id = created.json()["rule_id"]
    listed = await async_client.get(base, headers=headers)
    fetched = await async_client.get(f"{base}/{rule_id}", headers=headers)
    patched = await async_client.patch(
        f"{base}/{rule_id}", json={"source_style": "ink"}, headers=headers
    )
    deleted = await async_client.delete(f"{base}/{rule_id}", headers=headers)

    assert created.status_code == 201
    assert [r["rule_id"] for r in listed.json()["items"]] == [rule_id]
    assert fetched.json()["key"] == "r1"
    assert patched.json()["source_style"] == "ink"
    assert deleted.status_code == 204


async def test_duplicate_key_is_409(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    await _enable_rule_sheet(async_client, headers, scenario_id)
    base = f"/v1/scenarios/{scenario_id}/sheet-rules"
    await async_client.post(base, json=_payload(), headers=headers)

    response = await async_client.post(base, json=_payload(number=2), headers=headers)

    assert response.status_code == 409


async def test_invalid_payload_is_422(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    await _enable_rule_sheet(async_client, headers, scenario_id)

    response = await async_client.post(
        f"/v1/scenarios/{scenario_id}/sheet-rules",
        json=_payload(key="Bad Key"),
        headers=headers,
    )

    assert response.status_code == 422


async def test_reorder_returns_the_new_order(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    await _enable_rule_sheet(async_client, headers, scenario_id)
    base = f"/v1/scenarios/{scenario_id}/sheet-rules"
    first = await async_client.post(base, json=_payload(), headers=headers)
    second = await async_client.post(
        base, json=_payload(key="r2", number=2), headers=headers
    )

    response = await async_client.post(
        f"{base}/reorder",
        json={"ordered_rule_ids": [second.json()["rule_id"], first.json()["rule_id"]]},
        headers=headers,
    )

    assert [r["key"] for r in response.json()["items"]] == ["r2", "r1"]


async def test_another_users_scenario_is_refused(
    async_client: httpx.AsyncClient, db_session: AsyncSession, headers, scenario_id: str
):
    stranger = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Stranger"
    )

    response = await async_client.get(
        f"/v1/scenarios/{scenario_id}/sheet-rules",
        headers={"x-dev-user-id": str(stranger.user_id)},
    )

    assert response.status_code in (403, 404)
