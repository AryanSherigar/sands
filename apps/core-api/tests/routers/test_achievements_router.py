import uuid

import pytest
from app.db.models.user_achievement import UserAchievement
from app.repositories.achievement_repo import AchievementRepo
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import add_playthrough, make_scenario, make_user


async def _award_count(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(UserAchievement)
    return int((await session.execute(stmt)).scalar_one())


@pytest.mark.asyncio
async def test_owner_achievements_require_auth(async_client: AsyncClient) -> None:
    assert (await async_client.get("/v1/users/me/achievements")).status_code == 401


@pytest.mark.asyncio
async def test_owner_achievements_list_all_17_with_progress(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user, genre_tags=["Horror"])
    await add_playthrough(db_session, scenario, user, turn_count=63)

    response = await async_client.get(
        "/v1/users/me/achievements", headers={"x-dev-user-id": str(user.user_id)}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 17
    by_key = {item["key"]: item for item in body}
    assert by_key["first-steps"]["earned_at"] is not None
    assert by_key["wayfarer"]["earned_at"] is None
    assert by_key["wayfarer"]["progress"] == {"current": 63, "target": 100}
    assert by_key["wayfarer"]["family"] == "Journey"


@pytest.mark.asyncio
async def test_public_achievements_earned_only_no_progress_and_never_write(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    await add_playthrough(db_session, scenario, user, turn_count=5)

    before = await _award_count(db_session)
    empty = await async_client.get(f"/v1/users/{user.user_id}/achievements")
    assert empty.status_code == 200
    assert empty.json() == []  # nothing awarded yet, and reading did not award
    assert await _award_count(db_session) == before

    await async_client.get(
        "/v1/users/me/achievements", headers={"x-dev-user-id": str(user.user_id)}
    )
    public = (await async_client.get(f"/v1/users/{user.user_id}/achievements")).json()
    assert [item["key"] for item in public] == ["first-steps"]
    assert "progress" not in public[0]


@pytest.mark.asyncio
async def test_public_achievements_for_an_unknown_user_are_empty(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get(f"/v1/users/{uuid.uuid4()}/achievements")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/v1/users/me", "/v1/users/me/playthroughs"])
async def test_owner_reads_award_badges(
    path: str, async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    await add_playthrough(db_session, scenario, user, turn_count=3)

    response = await async_client.get(
        path, headers={"x-dev-user-id": str(user.user_id)}
    )

    assert response.status_code == 200
    rows = await AchievementRepo(db_session).list_earned(user.user_id)
    assert "first-steps" in {row.key for row in rows}


@pytest.mark.asyncio
async def test_evaluation_failure_does_not_break_me(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await make_user(db_session)

    async def boom(*args, **kwargs):
        raise SQLAlchemyError("simulated")

    monkeypatch.setattr(AchievementRepo, "insert_earned", boom)

    response = await async_client.get(
        "/v1/users/me", headers={"x-dev-user-id": str(user.user_id)}
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.user_id)


@pytest.mark.asyncio
async def test_review_awards_the_creator_immediately(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    creator = await make_user(db_session, "Creator")
    fan = await make_user(db_session, "Fan")
    scenario = await make_scenario(db_session, creator)
    scenario.published_at = scenario.created_at
    await add_playthrough(db_session, scenario, fan, turn_count=12)
    await db_session.flush()

    response = await async_client.post(
        f"/v1/scenarios/{scenario.scenario_id}/reviews",
        json={"rating": 5, "comment": "Great"},
        headers={"x-dev-user-id": str(fan.user_id)},
    )

    assert response.status_code == 201
    creator_rows = await AchievementRepo(db_session).list_earned(creator.user_id)
    assert {"five-stars", "worldmaker"} <= {row.key for row in creator_rows}
    fan_rows = await AchievementRepo(db_session).list_earned(fan.user_id)
    assert "five-stars" not in {row.key for row in fan_rows}


@pytest.mark.asyncio
async def test_owner_achievements_still_return_earned_badges_when_evaluation_fails(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    await add_playthrough(db_session, scenario, user, turn_count=3)
    headers = {"x-dev-user-id": str(user.user_id)}
    first = await async_client.get("/v1/users/me/achievements", headers=headers)
    assert first.status_code == 200

    async def boom(*args, **kwargs):
        raise SQLAlchemyError("simulated")

    monkeypatch.setattr(AchievementRepo, "insert_earned", boom)

    response = await async_client.get("/v1/users/me/achievements", headers=headers)

    assert response.status_code == 200
    by_key = {item["key"]: item for item in response.json()}
    assert len(by_key) == 17
    assert by_key["first-steps"]["earned_at"] is not None
    assert by_key["wayfarer"]["earned_at"] is None


@pytest.mark.asyncio
async def test_overview_survives_an_evaluation_failure_with_stored_milestones(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    await add_playthrough(db_session, scenario, user, turn_count=3)
    headers = {"x-dev-user-id": str(user.user_id)}
    await async_client.get("/v1/users/me/achievements", headers=headers)

    async def boom(*args, **kwargs):
        raise SQLAlchemyError("simulated")

    monkeypatch.setattr(AchievementRepo, "insert_earned", boom)

    response = await async_client.get("/v1/users/me/overview", headers=headers)

    assert response.status_code == 200
    keys = [m["key"] for m in response.json()["recent_milestones"]]
    assert keys == ["first-steps"]
