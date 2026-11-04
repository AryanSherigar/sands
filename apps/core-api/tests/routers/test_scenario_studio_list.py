"""Integration tests for the creator's Studio scenario list (GET /v1/scenarios?mine=true)."""

import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.review import ScenarioReview
from app.db.models.scenario import Scenario
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

STUDIO_LIST_URL = "/v1/scenarios?mine=true"


@pytest.fixture
async def creator(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Studio Creator"
    )


@pytest.fixture
async def reviewer(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Reviewer"
    )


def _headers(user) -> dict[str, str]:
    return {"x-dev-user-id": str(user.user_id)}


async def _create_scenario(
    client: AsyncClient, user, title: str, genre_tags: list[str] | None = None
) -> str:
    payload = {"title": title, "mode": "newbie", "complexity_tier": "newbie"}
    if genre_tags is not None:
        payload["genre_tags"] = genre_tags
    response = await client.post("/v1/scenarios", json=payload, headers=_headers(user))
    assert response.status_code == 201
    return response.json()["scenario_id"]


async def _mark_status(
    db_session: AsyncSession, scenario_id: str, status: str, **extra: object
) -> None:
    await db_session.execute(
        update(Scenario)
        .where(Scenario.scenario_id == uuid.UUID(scenario_id))
        .values(status=status, **extra)
    )


async def _mark_published(db_session: AsyncSession, scenario_id: str) -> None:
    """Publish with a snapshot equal to the current content_edited_at."""
    scenario = await db_session.get(Scenario, uuid.UUID(scenario_id))
    await db_session.refresh(scenario)
    await _mark_status(
        db_session,
        scenario_id,
        "published",
        published_at=datetime.now(UTC),
        published_content_edited_at=scenario.content_edited_at,
    )


async def _get_row(client: AsyncClient, user, scenario_id: str) -> dict:
    response = await client.get(STUDIO_LIST_URL, headers=_headers(user))
    assert response.status_code == 200
    rows = [r for r in response.json()["items"] if r["scenario_id"] == scenario_id]
    assert len(rows) == 1
    return rows[0]


@pytest.mark.asyncio
async def test_list_returns_studio_shape_sorted_by_last_edit(
    async_client: AsyncClient, creator
):
    first_id = await _create_scenario(async_client, creator, "First")
    second_id = await _create_scenario(async_client, creator, "Second")
    await async_client.patch(
        f"/v1/scenarios/{first_id}",
        json={"title": "First, revised"},
        headers=_headers(creator),
    )

    response = await async_client.get(STUDIO_LIST_URL, headers=_headers(creator))

    body = response.json()
    assert [row["scenario_id"] for row in body["items"]] == [first_id, second_id]
    assert body["status_counts"] == {
        "all": 2,
        "drafts": 2,
        "published": 0,
        "archived": 0,
    }
    assert body["items"][0]["review_count"] == 0
    assert body["items"][0]["has_unpublished_changes"] is False


@pytest.mark.asyncio
async def test_tab_filters_rows_but_counts_stay_totals(
    async_client: AsyncClient, db_session: AsyncSession, creator
):
    draft_id = await _create_scenario(async_client, creator, "A draft")
    live_id = await _create_scenario(async_client, creator, "A live one")
    await _mark_published(db_session, live_id)

    response = await async_client.get(
        f"{STUDIO_LIST_URL}&tab=published", headers=_headers(creator)
    )

    body = response.json()
    assert [row["scenario_id"] for row in body["items"]] == [live_id]
    assert draft_id not in [row["scenario_id"] for row in body["items"]]
    assert body["status_counts"]["all"] == 2
    assert body["status_counts"]["drafts"] == 1


@pytest.mark.asyncio
async def test_search_matches_title_and_genre(async_client: AsyncClient, creator):
    noir_id = await _create_scenario(async_client, creator, "Ledger", ["noir"])
    await _create_scenario(async_client, creator, "Harbor", ["fantasy"])

    by_genre = await async_client.get(
        f"{STUDIO_LIST_URL}&q=noir", headers=_headers(creator)
    )
    by_title = await async_client.get(
        f"{STUDIO_LIST_URL}&q=harb", headers=_headers(creator)
    )

    assert [r["scenario_id"] for r in by_genre.json()["items"]] == [noir_id]
    assert [r["title"] for r in by_title.json()["items"]] == ["Harbor"]


@pytest.mark.asyncio
async def test_offset_paging_never_repeats_a_row(async_client: AsyncClient, creator):
    created = [
        await _create_scenario(async_client, creator, f"Story {i}") for i in range(3)
    ]

    page_one = (
        await async_client.get(f"{STUDIO_LIST_URL}&limit=2", headers=_headers(creator))
    ).json()
    page_two = (
        await async_client.get(
            f"{STUDIO_LIST_URL}&limit=2&offset={page_one['next_cursor']}",
            headers=_headers(creator),
        )
    ).json()

    seen = [r["scenario_id"] for r in page_one["items"] + page_two["items"]]
    assert sorted(seen) == sorted(created)
    assert page_two["next_cursor"] is None


@pytest.mark.asyncio
async def test_review_count_is_reported_per_scenario(
    async_client: AsyncClient, db_session: AsyncSession, creator, reviewer
):
    scenario_id = await _create_scenario(async_client, creator, "Reviewed")
    db_session.add(
        ScenarioReview(
            scenario_id=uuid.UUID(scenario_id),
            user_id=reviewer.user_id,
            rating=5,
            comment="Great",
        )
    )
    await db_session.flush()

    row = await _get_row(async_client, creator, scenario_id)

    assert row["review_count"] == 1


@pytest.mark.asyncio
async def test_content_edit_flags_unpublished_changes_but_plays_do_not(
    async_client: AsyncClient, db_session: AsyncSession, creator
):
    scenario_id = await _create_scenario(async_client, creator, "Live story")
    await _mark_published(db_session, scenario_id)

    await db_session.execute(
        update(Scenario)
        .where(Scenario.scenario_id == uuid.UUID(scenario_id))
        .values(play_count=Scenario.play_count + 10)
    )
    after_play = await _get_row(async_client, creator, scenario_id)
    await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={"title": "Live story, revised"},
        headers=_headers(creator),
    )
    after_edit = await _get_row(async_client, creator, scenario_id)

    assert after_play["has_unpublished_changes"] is False
    assert after_edit["has_unpublished_changes"] is True


@pytest.mark.asyncio
async def test_child_table_write_bumps_content_edited_at(
    async_client: AsyncClient, creator
):
    response = await async_client.post(
        "/v1/scenarios",
        json={"title": "Master", "mode": "master", "complexity_tier": "master"},
        headers=_headers(creator),
    )
    scenario_id = response.json()["scenario_id"]
    before = (await _get_row(async_client, creator, scenario_id))["content_edited_at"]

    await async_client.post(
        f"/v1/scenarios/{scenario_id}/entities",
        json={"entity_type": "character", "canonical_name": "The Warden"},
        headers=_headers(creator),
    )

    after = (await _get_row(async_client, creator, scenario_id))["content_edited_at"]
    assert after > before


@pytest.mark.asyncio
async def test_failed_first_publish_reports_error_on_draft_row(
    async_client: AsyncClient, db_session: AsyncSession, creator
):
    scenario_id = await _create_scenario(async_client, creator, "Broken")
    await _mark_status(
        db_session, scenario_id, "draft", publish_error="content_tag is required"
    )

    row = await _get_row(async_client, creator, scenario_id)

    assert row["status"] == "draft"
    assert row["publish_error"] == "content_tag is required"


@pytest.mark.asyncio
async def test_deleting_a_published_scenario_archives_it(
    async_client: AsyncClient, db_session: AsyncSession, creator
):
    scenario_id = await _create_scenario(async_client, creator, "Was live")
    await _mark_published(db_session, scenario_id)

    delete_response = await async_client.delete(
        f"/v1/scenarios/{scenario_id}", headers=_headers(creator)
    )
    archived = await async_client.get(
        f"{STUDIO_LIST_URL}&tab=archived", headers=_headers(creator)
    )

    assert delete_response.status_code == 204
    assert [r["scenario_id"] for r in archived.json()["items"]] == [scenario_id]


@pytest.mark.asyncio
async def test_deleting_an_unplayed_draft_removes_it(
    async_client: AsyncClient, creator
):
    scenario_id = await _create_scenario(async_client, creator, "Scrap")

    await async_client.delete(f"/v1/scenarios/{scenario_id}", headers=_headers(creator))
    response = await async_client.get(STUDIO_LIST_URL, headers=_headers(creator))

    assert response.json()["items"] == []
    assert response.json()["status_counts"]["all"] == 0
