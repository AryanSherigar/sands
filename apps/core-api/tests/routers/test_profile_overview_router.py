"""Integration tests for GET /v1/users/me/overview."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import (
    add_playthrough,
    add_turn_log,
    make_scenario,
    make_user,
)


@pytest.mark.asyncio
async def test_overview_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/v1/users/me/overview")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_overview_zero_history_shape(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    headers = {"x-dev-user-id": str(user.user_id)}
    response = await async_client.get("/v1/users/me/overview", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["lifetime_stats"] == {
        "turns_taken": 0,
        "stories_completed": 0,
        "endings_found": 0,
        "endings_total": 0,
        "worlds_played": 0,
        "campaigns_count": 0,
        "genres_explored": [],
    }
    assert body["weekly_activity"]["played_days"] == [False] * 7
    assert body["weekly_activity"]["played_day_count"] == 0
    assert body["continue_runs"] == []
    assert body["recent_milestones"] == []


@pytest.mark.asyncio
async def test_overview_reports_only_my_non_playtest_data(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    scenario = await make_scenario(db_session, me, genre_tags=["Sci-Fi"])
    mine = await add_playthrough(db_session, scenario, me, turn_count=6)
    await add_playthrough(db_session, scenario, me, turn_count=40, is_playtest=True)
    await add_playthrough(db_session, scenario, other, turn_count=70)
    await add_turn_log(db_session, mine, 6, datetime.now(UTC), "Ice hums.")

    headers = {"x-dev-user-id": str(me.user_id)}
    body = (await async_client.get("/v1/users/me/overview", headers=headers)).json()

    assert body["lifetime_stats"]["turns_taken"] == 6
    assert body["lifetime_stats"]["genres_explored"] == ["Sci-Fi"]
    assert [run["playthrough_id"] for run in body["continue_runs"]] == [
        str(mine.playthrough_id)
    ]
    assert body["continue_runs"][0]["narration_excerpt"] == "Ice hums."
    assert sum(body["weekly_activity"]["played_days"]) == 1


@pytest.mark.asyncio
async def test_no_visitor_overview_route(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    headers = {"x-dev-user-id": str(user.user_id)}
    response = await async_client.get(
        f"/v1/users/{uuid.uuid4()}/overview", headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_overview_returns_recent_milestones(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    await add_playthrough(db_session, scenario, user, turn_count=120)
    headers = {"x-dev-user-id": str(user.user_id)}

    body = (await async_client.get("/v1/users/me/overview", headers=headers)).json()

    assert [m["key"] for m in body["recent_milestones"]] == [
        "first-steps",
        "wayfarer",
    ]
    assert body["recent_milestones"][0]["name"] == "First Steps"
