"""Integration tests for Rule Invariant REST endpoints."""

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
async def master_scenario_id(async_client: AsyncClient, dev_user) -> str:
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    create_resp = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "The Hollow Cairn",
            "mode": "master",
            "complexity_tier": "master",
        },
        headers=headers,
    )
    scenario_id = create_resp.json()["scenario_id"]
    await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={
            "state_schema": {
                "player": {"type": "object", "fields": {"health": {"type": "number"}}}
            }
        },
        headers=headers,
    )
    return scenario_id


@pytest.mark.asyncio
async def test_invariant_crud_flow(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}

    create_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/invariants",
        json={
            "label": "Health cannot go negative",
            "invariant_expression": {"field": "player.health", "op": ">=", "value": 0},
            "applies_to": "global",
            "narrator_text": "Health cannot fall below zero.",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    invariant_id = create_resp.json()["invariant_id"]

    list_resp = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/invariants", headers=headers
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    delete_resp = await async_client.delete(
        f"/v1/scenarios/{master_scenario_id}/invariants/{invariant_id}", headers=headers
    )
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_invariant_invalid_applies_to_rejected(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    response = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/invariants",
        json={
            "label": "Bad",
            "invariant_expression": {"field": "player.health", "op": ">=", "value": 0},
            "applies_to": "not-a-real-scope",
            "narrator_text": "x",
        },
        headers=headers,
    )
    assert response.status_code == 422


UI_METADATA = {"rows": [{"comparison": "is_at_most"}], "joiner": "and"}
OVERSIZED_UI_METADATA = {"blob": "x" * 5000}


async def _create_invariant(
    async_client: AsyncClient, headers: dict, scenario_id: str, **extra: object
):
    return await async_client.post(
        f"/v1/scenarios/{scenario_id}/invariants",
        json={
            "label": "Health floor",
            "invariant_expression": {"field": "player.health", "op": ">=", "value": 0},
            "applies_to": "global",
            "narrator_text": "Health cannot fall below zero.",
            **extra,
        },
        headers=headers,
    )


@pytest.mark.asyncio
async def test_invariant_metadata_defaults_to_null(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}

    created = await _create_invariant(async_client, headers, master_scenario_id)

    assert created.status_code == 201
    assert created.json()["metadata"] is None


@pytest.mark.asyncio
async def test_invariant_metadata_round_trips_on_create_patch_and_get(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    base = f"/v1/scenarios/{master_scenario_id}/invariants"
    created = await _create_invariant(
        async_client, headers, master_scenario_id, metadata=UI_METADATA
    )
    invariant_id = created.json()["invariant_id"]
    changed = {"rows": [{"comparison": "becomes_yes"}], "joiner": "or"}

    patched = await async_client.patch(
        f"{base}/{invariant_id}", json={"metadata": changed}, headers=headers
    )
    fetched = await async_client.get(f"{base}/{invariant_id}", headers=headers)

    assert created.json()["metadata"] == UI_METADATA
    assert patched.json()["metadata"] == changed
    assert fetched.json()["metadata"] == changed


@pytest.mark.asyncio
async def test_invariant_patch_without_metadata_keeps_it(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    created = await _create_invariant(
        async_client, headers, master_scenario_id, metadata=UI_METADATA
    )

    patched = await async_client.patch(
        f"/v1/scenarios/{master_scenario_id}/invariants/"
        f"{created.json()['invariant_id']}",
        json={"label": "Renamed"},
        headers=headers,
    )

    assert patched.json()["label"] == "Renamed"
    assert patched.json()["metadata"] == UI_METADATA


@pytest.mark.asyncio
async def test_invariant_metadata_over_four_kb_is_rejected(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}

    response = await _create_invariant(
        async_client, headers, master_scenario_id, metadata=OVERSIZED_UI_METADATA
    )

    assert response.status_code == 422
