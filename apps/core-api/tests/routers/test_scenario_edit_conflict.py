"""Two windows editing one story: a stale expected_content_edited_at is a 409."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

STALE_STAMP = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
CONFLICT_CODE = "scenario_edit_conflict"


@pytest.fixture
async def creator(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Creator"
    )


@pytest.fixture
def headers(creator) -> dict[str, str]:
    return {"x-dev-user-id": str(creator.user_id)}


@pytest.fixture
async def scenario(async_client: AsyncClient, headers) -> dict:
    response = await async_client.post(
        "/v1/scenarios", json={"title": "The Door Below"}, headers=headers
    )
    assert response.status_code == 201
    return response.json()


async def _create_entity(
    async_client: AsyncClient, headers, scenario_id: str, name: str
) -> dict:
    response = await async_client.post(
        f"/v1/scenarios/{scenario_id}/entities",
        json={"entity_type": "character", "canonical_name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_a_new_story_exposes_its_edit_stamp(scenario):
    assert scenario["content_edited_at"]
    assert scenario["visibility"] == "private"


@pytest.mark.asyncio
async def test_patch_with_a_stale_stamp_is_a_conflict(
    async_client: AsyncClient, headers, scenario
):
    response = await async_client.patch(
        f"/v1/scenarios/{scenario['scenario_id']}",
        json={"title": "Changed", "expected_content_edited_at": STALE_STAMP},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == CONFLICT_CODE
    unchanged = await async_client.get(
        f"/v1/scenarios/{scenario['scenario_id']}", headers=headers
    )
    assert unchanged.json()["title"] == "The Door Below"


@pytest.mark.asyncio
async def test_patch_with_the_current_stamp_succeeds_and_returns_a_new_one(
    async_client: AsyncClient, headers, scenario
):
    url = f"/v1/scenarios/{scenario['scenario_id']}"

    first = await async_client.patch(
        url,
        json={
            "title": "First",
            "expected_content_edited_at": scenario["content_edited_at"],
        },
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["content_edited_at"] != scenario["content_edited_at"]

    again = await async_client.patch(
        url,
        json={
            "title": "Second",
            "expected_content_edited_at": first.json()["content_edited_at"],
        },
        headers=headers,
    )
    assert again.status_code == 200
    assert again.json()["title"] == "Second"


@pytest.mark.asyncio
async def test_patch_without_a_stamp_behaves_as_before(
    async_client: AsyncClient, headers, scenario
):
    response = await async_client.patch(
        f"/v1/scenarios/{scenario['scenario_id']}",
        json={"title": "No stamp"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "No stamp"


@pytest.mark.asyncio
async def test_visibility_can_be_changed_by_patch_without_marking_unpublished_edits(
    async_client: AsyncClient, headers, scenario
):
    url = f"/v1/scenarios/{scenario['scenario_id']}"

    response = await async_client.patch(
        url, json={"visibility": "public"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["visibility"] == "public"
    assert response.json()["content_edited_at"] == scenario["content_edited_at"]
    invalid = await async_client.patch(
        url, json={"visibility": "secret"}, headers=headers
    )
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_entity_writes_check_the_stamp_and_return_the_new_one(
    async_client: AsyncClient, headers, scenario
):
    base = f"/v1/scenarios/{scenario['scenario_id']}/entities"

    stale = await async_client.post(
        base,
        json={
            "entity_type": "character",
            "canonical_name": "Mara",
            "expected_content_edited_at": STALE_STAMP,
        },
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == CONFLICT_CODE

    created = await async_client.post(
        base,
        json={
            "entity_type": "character",
            "canonical_name": "Mara",
            "expected_content_edited_at": scenario["content_edited_at"],
        },
        headers=headers,
    )
    assert created.status_code == 201
    new_stamp = created.json()["scenario_content_edited_at"]
    assert new_stamp != scenario["content_edited_at"]
    current = await async_client.get(
        f"/v1/scenarios/{scenario['scenario_id']}", headers=headers
    )
    assert current.json()["content_edited_at"] == new_stamp

    entity_url = f"{base}/{created.json()['entity_id']}"
    stale_update = await async_client.patch(
        entity_url,
        json={"description": "x", "expected_content_edited_at": STALE_STAMP},
        headers=headers,
    )
    assert stale_update.status_code == 409
    update = await async_client.patch(
        entity_url,
        json={"description": "x", "expected_content_edited_at": new_stamp},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["description"] == "x"


@pytest.mark.asyncio
async def test_entity_delete_checks_the_stamp_when_given(
    async_client: AsyncClient, headers, scenario
):
    entity = await _create_entity(
        async_client, headers, scenario["scenario_id"], "Mara"
    )
    entity_url = (
        f"/v1/scenarios/{scenario['scenario_id']}/entities/{entity['entity_id']}"
    )

    stale = await async_client.delete(
        entity_url, params={"expected_content_edited_at": STALE_STAMP}, headers=headers
    )
    assert stale.status_code == 409
    removed = await async_client.delete(
        entity_url,
        params={"expected_content_edited_at": entity["scenario_content_edited_at"]},
        headers=headers,
    )
    assert removed.status_code == 204


@pytest.mark.asyncio
async def test_fact_writes_check_the_stamp_and_return_the_new_one(
    async_client: AsyncClient, headers, scenario
):
    mara = await _create_entity(async_client, headers, scenario["scenario_id"], "Mara")
    door = await _create_entity(async_client, headers, scenario["scenario_id"], "Door")
    base = f"/v1/scenarios/{scenario['scenario_id']}/facts"
    body = {
        "subject_entity_id": mara["entity_id"],
        "predicate": "opens",
        "object_entity_id": door["entity_id"],
    }

    stale = await async_client.post(
        base, json={**body, "expected_content_edited_at": STALE_STAMP}, headers=headers
    )
    assert stale.status_code == 409

    created = await async_client.post(
        base,
        json={
            **body,
            "expected_content_edited_at": door["scenario_content_edited_at"],
        },
        headers=headers,
    )
    assert created.status_code == 201
    new_stamp = created.json()["scenario_content_edited_at"]
    fact_url = f"{base}/{created.json()['fact_id']}"
    assert (
        await async_client.patch(
            fact_url,
            json={"predicate": "locks", "expected_content_edited_at": STALE_STAMP},
            headers=headers,
        )
    ).status_code == 409
    update = await async_client.patch(
        fact_url,
        json={"predicate": "locks", "expected_content_edited_at": new_stamp},
        headers=headers,
    )
    assert update.status_code == 200
    assert (
        await async_client.delete(
            fact_url,
            params={"expected_content_edited_at": STALE_STAMP},
            headers=headers,
        )
    ).status_code == 409
