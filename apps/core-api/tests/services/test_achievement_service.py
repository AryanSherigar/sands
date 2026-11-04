"""Service-level tests for AchievementService against the real test DB."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.repositories.achievement_repo import AchievementRepo
from app.services.achievement_service import (
    RECENT_MILESTONE_LIMIT,
    build_achievement_service,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import add_playthrough, make_scenario, make_user

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_zero_history_user_earns_nothing_and_sees_all_17_at_zero(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    service = build_achievement_service(db_session)

    items = await service.get_owner_achievements(user.user_id, NOW)

    assert len(items) == 17
    assert all(item.earned_at is None for item in items)
    assert all(item.progress.current == 0 for item in items)
    assert items[0].key == "first-steps"
    assert (items[2].progress.current, items[2].progress.target) == (0, 100)


@pytest.mark.asyncio
async def test_first_evaluation_backfills_with_now_and_later_ones_keep_the_date(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user, genre_tags=["Sci-Fi"])
    await add_playthrough(db_session, scenario, user, turn_count=1000)
    service = build_achievement_service(db_session)

    first = await service.get_owner_achievements(user.user_id, NOW)
    later = await service.get_owner_achievements(user.user_id, NOW + timedelta(days=3))

    earned_first = {i.key: i.earned_at for i in first if i.earned_at}
    assert {"first-steps", "wayfarer", "voyager", "chronicler"} <= set(earned_first)
    assert set(earned_first.values()) == {NOW}
    earned_later = {i.key: i.earned_at for i in later if i.earned_at}
    assert earned_later == earned_first


@pytest.mark.asyncio
async def test_turn_threshold_boundary_99_vs_100(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    run = await add_playthrough(db_session, scenario, user, turn_count=99)
    service = build_achievement_service(db_session)
    before = {
        i.key
        for i in await service.get_owner_achievements(user.user_id, NOW)
        if i.earned_at
    }
    assert "wayfarer" not in before

    run.turn_count = 100
    await db_session.flush()
    after = {
        i.key
        for i in await service.get_owner_achievements(user.user_id, NOW)
        if i.earned_at
    }
    assert "wayfarer" in after


@pytest.mark.asyncio
async def test_playtests_and_other_users_never_count(db_session: AsyncSession) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    scenario = await make_scenario(db_session, me)
    await add_playthrough(db_session, scenario, me, turn_count=500, is_playtest=True)
    await add_playthrough(db_session, scenario, other, turn_count=500)
    service = build_achievement_service(db_session)
    items = await service.get_owner_achievements(me.user_id, NOW)
    assert [i for i in items if i.earned_at] == []


@pytest.mark.asyncio
async def test_public_achievements_are_earned_only_and_never_write(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    await add_playthrough(db_session, scenario, user, turn_count=5)
    service = build_achievement_service(db_session)

    assert await service.get_public_achievements(user.user_id) == []  # never evaluated

    await service.evaluate_and_award(user.user_id, NOW)
    public = await service.get_public_achievements(user.user_id)

    assert [item.key for item in public] == ["first-steps"]
    assert public[0].earned_at == NOW
    assert not hasattr(public[0], "progress")


@pytest.mark.asyncio
async def test_recent_milestones_are_limited_and_tie_break_on_catalogue_order(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    await add_playthrough(db_session, scenario, user, turn_count=1000)
    service = build_achievement_service(db_session)

    milestones = await service.get_recent_milestones(user.user_id, NOW)

    assert len(milestones) == RECENT_MILESTONE_LIMIT == 3
    assert [m.key for m in milestones] == ["first-steps", "wayfarer", "voyager"]


@pytest.mark.asyncio
async def test_recent_milestones_prefer_the_newest_award(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    repo = AchievementRepo(db_session)
    await repo.insert_earned(user.user_id, ["first-steps"], NOW - timedelta(days=10))
    await repo.insert_earned(user.user_id, ["crowd"], NOW - timedelta(days=1))
    service = build_achievement_service(db_session)

    milestones = await service.get_recent_milestones(user.user_id, NOW)

    assert [m.key for m in milestones][:2] == ["crowd", "first-steps"]


@pytest.mark.asyncio
async def test_evaluation_failure_is_swallowed_and_the_session_stays_usable(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    await add_playthrough(db_session, scenario, user, turn_count=5)

    async def boom(*args, **kwargs):
        raise SQLAlchemyError("simulated")

    monkeypatch.setattr(AchievementRepo, "insert_earned", boom)
    service = build_achievement_service(db_session)

    await service.evaluate_and_award(user.user_id, NOW)  # must not raise
    milestones = await service.get_recent_milestones(user.user_id, NOW)

    assert milestones == []
    assert await AchievementRepo(db_session).list_earned(user.user_id) == []


@pytest.mark.asyncio
async def test_award_scenario_creator_evaluates_the_creator(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    scenario = await make_scenario(db_session, creator)
    scenario.published_at = NOW
    await db_session.flush()
    service = build_achievement_service(db_session)

    await service.award_scenario_creator(scenario.scenario_id, NOW)

    keys = {
        row.key
        for row in await AchievementRepo(db_session).list_earned(creator.user_id)
    }
    assert keys == {"worldmaker"}


@pytest.mark.asyncio
async def test_award_scenario_creator_ignores_unknown_scenarios(
    db_session: AsyncSession,
) -> None:
    service = build_achievement_service(db_session)
    await service.award_scenario_creator(uuid.uuid4(), NOW)  # must not raise
