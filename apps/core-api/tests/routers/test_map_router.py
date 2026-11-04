"""Integration tests for Map/MapPin/MapConnection REST endpoints."""

import uuid

import pytest
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
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
async def master_scenario_id(async_client: AsyncClient, headers) -> str:
    response = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "The Hollow Cairn",
            "mode": "master",
            "complexity_tier": "master",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["scenario_id"]


@pytest.fixture
async def newbie_scenario_id(async_client: AsyncClient, headers) -> str:
    response = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "A Freeform Tale",
            "mode": "newbie",
            "complexity_tier": "newbie",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["scenario_id"]


async def _create_location(
    async_client: AsyncClient, headers, scenario_id: str, name: str
) -> str:
    response = await async_client.post(
        f"/v1/scenarios/{scenario_id}/entities",
        json={"entity_type": "location", "canonical_name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["entity_id"]


async def _create_character(
    async_client: AsyncClient, headers, scenario_id: str, name: str
) -> str:
    response = await async_client.post(
        f"/v1/scenarios/{scenario_id}/entities",
        json={"entity_type": "character", "canonical_name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["entity_id"]


@pytest.mark.asyncio
async def test_create_map_rejected_on_newbie_mode_scenario(
    async_client: AsyncClient, headers, newbie_scenario_id: str
):
    response = await async_client.post(
        f"/v1/scenarios/{newbie_scenario_id}/maps",
        json={"name": "Overworld"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_map_crud_flow(
    async_client: AsyncClient, headers, master_scenario_id: str
):
    create_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps",
        json={"name": "Overworld", "display_order": 1},
        headers=headers,
    )
    assert create_resp.status_code == 201
    scenario_map = create_resp.json()
    map_id = scenario_map["map_id"]
    assert scenario_map["name"] == "Overworld"

    list_resp = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/maps", headers=headers
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    patch_resp = await async_client.patch(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}",
        json={"name": "Overworld Renamed"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Overworld Renamed"

    delete_resp = await async_client.delete(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    list_after = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/maps", headers=headers
    )
    assert list_after.json()["items"] == []


@pytest.mark.asyncio
async def test_create_map_requires_authentication(
    async_client: AsyncClient, master_scenario_id: str
):
    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps", json={"name": "Overworld"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_map_rejected_for_non_owner(
    async_client: AsyncClient, db_session: AsyncSession, master_scenario_id: str
):
    other_user = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Other"
    )
    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps",
        json={"name": "Overworld"},
        headers={"x-dev-user-id": str(other_user.user_id)},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pin_crud_flow(
    async_client: AsyncClient, headers, master_scenario_id: str
):
    map_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps",
        json={"name": "Overworld"},
        headers=headers,
    )
    map_id = map_resp.json()["map_id"]
    entity_id = await _create_location(
        async_client, headers, master_scenario_id, "The Cairn"
    )

    create_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}/pins",
        json={"entity_id": entity_id, "x": 0.5, "y": 0.5},
        headers=headers,
    )
    assert create_resp.status_code == 201
    pin = create_resp.json()
    pin_id = pin["pin_id"]
    assert pin["entity_id"] == entity_id

    list_resp = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}/pins", headers=headers
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    patch_resp = await async_client.patch(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}/pins/{pin_id}",
        json={"x": 0.1, "y": 0.9},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["x"] == 0.1
    assert patch_resp.json()["y"] == 0.9

    delete_resp = await async_client.delete(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}/pins/{pin_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_create_pin_rejects_non_location_entity(
    async_client: AsyncClient, headers, master_scenario_id: str
):
    map_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps",
        json={"name": "Overworld"},
        headers=headers,
    )
    map_id = map_resp.json()["map_id"]
    character_id = await _create_character(
        async_client, headers, master_scenario_id, "The Warden"
    )

    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}/pins",
        json={"entity_id": character_id, "x": 0.5, "y": 0.5},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_pin_rejects_second_start_location(
    async_client: AsyncClient, headers, master_scenario_id: str
):
    map_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps",
        json={"name": "Overworld"},
        headers=headers,
    )
    map_id = map_resp.json()["map_id"]
    entity_a = await _create_location(
        async_client, headers, master_scenario_id, "The Cairn"
    )
    entity_b = await _create_location(
        async_client, headers, master_scenario_id, "The Keep"
    )

    first = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}/pins",
        json={"entity_id": entity_a, "x": 0.1, "y": 0.1, "is_start_location": True},
        headers=headers,
    )
    assert first.status_code == 201

    second = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}/pins",
        json={"entity_id": entity_b, "x": 0.2, "y": 0.2, "is_start_location": True},
        headers=headers,
    )
    assert second.status_code == 422


@pytest.mark.asyncio
async def test_pin_coordinates_out_of_range_rejected(
    async_client: AsyncClient, headers, master_scenario_id: str
):
    map_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps",
        json={"name": "Overworld"},
        headers=headers,
    )
    map_id = map_resp.json()["map_id"]
    entity_id = await _create_location(
        async_client, headers, master_scenario_id, "The Cairn"
    )

    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/maps/{map_id}/pins",
        json={"entity_id": entity_id, "x": 1.5, "y": 0.5},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_connection_crud_flow(
    async_client: AsyncClient, headers, master_scenario_id: str
):
    entity_a = await _create_location(
        async_client, headers, master_scenario_id, "The Cairn"
    )
    entity_b = await _create_location(
        async_client, headers, master_scenario_id, "The Keep"
    )

    create_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/map-connections",
        json={"entity_id_a": entity_a, "entity_id_b": entity_b, "label": "a path"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    connection = create_resp.json()
    connection_id = connection["connection_id"]
    assert connection["label"] == "a path"

    duplicate_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/map-connections",
        json={"entity_id_a": entity_b, "entity_id_b": entity_a},
        headers=headers,
    )
    assert duplicate_resp.status_code == 422

    list_resp = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/map-connections", headers=headers
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    delete_resp = await async_client.delete(
        f"/v1/scenarios/{master_scenario_id}/map-connections/{connection_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 204

    list_after = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/map-connections", headers=headers
    )
    assert list_after.json()["items"] == []


@pytest.mark.asyncio
async def test_create_connection_rejects_self_link(
    async_client: AsyncClient, headers, master_scenario_id: str
):
    entity_id = await _create_location(
        async_client, headers, master_scenario_id, "The Cairn"
    )
    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/map-connections",
        json={"entity_id_a": entity_id, "entity_id_b": entity_id},
        headers=headers,
    )
    assert response.status_code == 422
