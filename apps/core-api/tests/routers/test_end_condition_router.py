"""Integration tests for End Condition REST endpoints."""

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
    response = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "The Hollow Cairn",
            "mode": "master",
            "complexity_tier": "master",
        },
        headers=headers,
    )
    return response.json()["scenario_id"]


@pytest.mark.asyncio
async def test_end_condition_multi_outcome_flow(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}

    win_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/end_conditions",
        json={
            "condition_expression": {},
            "outcome_tag": "win",
            "outcome_title": "The Ashen Ending",
            "outcome_text": "The Warden kneels.",
        },
        headers=headers,
    )
    assert win_resp.status_code == 201

    secret_win_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/end_conditions",
        json={
            "condition_expression": {},
            "outcome_tag": "win",
            "outcome_title": "The Vigil's Ending",
            "outcome_text": "You relieve it.",
            "is_secret": True,
        },
        headers=headers,
    )
    assert secret_win_resp.status_code == 201

    list_resp = await async_client.get(
        f"/v1/scenarios/{master_scenario_id}/end_conditions", headers=headers
    )
    items = list_resp.json()["items"]
    assert len(items) == 2
    assert {item["outcome_tag"] for item in items} == {"win"}


@pytest.mark.asyncio
async def test_end_condition_reorder(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    first = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/end_conditions",
        json={
            "condition_expression": {},
            "outcome_tag": "win",
            "outcome_title": "A",
            "outcome_text": "a",
        },
        headers=headers,
    )
    second = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/end_conditions",
        json={
            "condition_expression": {},
            "outcome_tag": "lose",
            "outcome_title": "B",
            "outcome_text": "b",
        },
        headers=headers,
    )
    first_id = first.json()["end_condition_id"]
    second_id = second.json()["end_condition_id"]

    reorder_resp = await async_client.post(
        f"/v1/scenarios/{master_scenario_id}/end_conditions/reorder",
        json={"ordered_end_condition_ids": [second_id, first_id]},
        headers=headers,
    )
    assert reorder_resp.status_code == 200
    items = reorder_resp.json()["items"]
    assert [item["end_condition_id"] for item in items] == [second_id, first_id]


UI_METADATA = {"rows": [{"comparison": "drops_to"}], "joiner": "and"}
OVERSIZED_UI_METADATA = {"blob": "x" * 5000}


async def _create_end_condition(
    async_client: AsyncClient, headers: dict, scenario_id: str, **extra: object
):
    return await async_client.post(
        f"/v1/scenarios/{scenario_id}/end_conditions",
        json={
            "condition_expression": {},
            "outcome_tag": "lose",
            "outcome_title": "Gone",
            "outcome_text": "The light fades.",
            **extra,
        },
        headers=headers,
    )


@pytest.mark.asyncio
async def test_end_condition_metadata_defaults_to_null(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}

    created = await _create_end_condition(async_client, headers, master_scenario_id)

    assert created.status_code == 201
    assert created.json()["metadata"] is None


@pytest.mark.asyncio
async def test_end_condition_metadata_round_trips_on_create_patch_and_get(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    base = f"/v1/scenarios/{master_scenario_id}/end_conditions"
    created = await _create_end_condition(
        async_client, headers, master_scenario_id, metadata=UI_METADATA
    )
    end_condition_id = created.json()["end_condition_id"]
    changed = {"rows": [{"comparison": "is_at_most"}], "joiner": "or"}

    patched = await async_client.patch(
        f"{base}/{end_condition_id}", json={"metadata": changed}, headers=headers
    )
    fetched = await async_client.get(f"{base}/{end_condition_id}", headers=headers)
    listed = await async_client.get(base, headers=headers)

    assert created.json()["metadata"] == UI_METADATA
    assert patched.json()["metadata"] == changed
    assert fetched.json()["metadata"] == changed
    assert listed.json()["items"][0]["metadata"] == changed


@pytest.mark.asyncio
async def test_end_condition_patch_without_metadata_keeps_it(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    created = await _create_end_condition(
        async_client, headers, master_scenario_id, metadata=UI_METADATA
    )

    patched = await async_client.patch(
        f"/v1/scenarios/{master_scenario_id}/end_conditions/"
        f"{created.json()['end_condition_id']}",
        json={"outcome_title": "Renamed"},
        headers=headers,
    )

    assert patched.json()["outcome_title"] == "Renamed"
    assert patched.json()["metadata"] == UI_METADATA


@pytest.mark.asyncio
async def test_end_condition_metadata_over_four_kb_is_rejected(
    async_client: AsyncClient, dev_user, master_scenario_id: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}

    response = await _create_end_condition(
        async_client, headers, master_scenario_id, metadata=OVERSIZED_UI_METADATA
    )

    assert response.status_code == 422
