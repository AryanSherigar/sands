"""Service-level tests for ProfileOverviewService against the real test DB."""

from datetime import UTC, datetime

import pytest
from app.repositories.endings_repo import EndingsRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.profile_overview_repo import ProfileOverviewRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.services.achievement_service import build_achievement_service
from app.services.endings_service import EndingsService
from app.services.profile_overview_service import ProfileOverviewService
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import (
    add_playthrough,
    add_turn_log,
    make_scenario,
    make_user,
)

NOW = datetime(2026, 10, 30, 10, 0, tzinfo=UTC)  # Friday


def build_service(session: AsyncSession) -> ProfileOverviewService:
    return ProfileOverviewService(
        ProfileOverviewRepo(session),
        PlaythroughRepo(session),
        TurnLogRepo(session),
        EndingsService(EndingsRepo(session)),
        build_achievement_service(session),
    )


@pytest.mark.asyncio
async def test_zero_history_user_gets_empty_overview(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    overview = await build_service(db_session).get_overview(user.user_id, NOW)
    assert overview.lifetime_stats.turns_taken == 0
    assert overview.lifetime_stats.genres_explored == []
    assert overview.lifetime_stats.endings_found == 0
    assert overview.lifetime_stats.endings_total == 0
    assert overview.weekly_activity.played_days == [False] * 7
    assert overview.weekly_activity.played_day_count == 0
    assert overview.continue_runs == []
    assert overview.recent_milestones == []


@pytest.mark.asyncio
async def test_overview_composes_stats_week_and_continue_runs(
    db_session: AsyncSession,
) -> None:
    player = await make_user(db_session)
    noir = await make_scenario(
        db_session, player, mode="master", genre_tags=["Noir / Detective"]
    )
    newbie = await make_scenario(db_session, player, mode="newbie", genre_tags=[])
    master_run = await add_playthrough(
        db_session, noir, player, turn_count=14, state={"setup": {}}
    )
    master_run.checkpoint = "Act II: The Slipway"
    newbie_run = await add_playthrough(db_session, newbie, player, turn_count=8)
    newbie_run.checkpoint = "ignored-for-newbie"
    await db_session.flush()
    await add_turn_log(
        db_session,
        master_run,
        14,
        datetime(2026, 10, 27, 9, 0, tzinfo=UTC),
        "Rain  slicks\nthe wharf.",
    )
    await add_turn_log(
        db_session, newbie_run, 8, datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
    )

    overview = await build_service(db_session).get_overview(player.user_id, NOW)

    assert overview.lifetime_stats.turns_taken == 22
    assert overview.lifetime_stats.worlds_played == 2
    assert overview.lifetime_stats.campaigns_count == 2
    assert overview.lifetime_stats.genres_explored == ["Noir / Detective"]
    assert overview.weekly_activity.played_days == [
        False,
        True,
        False,
        False,
        True,
        False,
        False,
    ]
    assert overview.weekly_activity.played_day_count == 2
    by_id = {run.playthrough_id: run for run in overview.continue_runs}
    master_card = by_id[master_run.playthrough_id]
    assert master_card.checkpoint == "Act II: The Slipway"
    assert master_card.primary_genre == "Noir / Detective"
    assert master_card.narration_excerpt == "Rain slicks the wharf."
    newbie_card = by_id[newbie_run.playthrough_id]
    assert newbie_card.checkpoint is None
    assert newbie_card.primary_genre is None
    assert newbie_card.narration_excerpt is None


@pytest.mark.asyncio
async def test_continue_runs_are_limited_to_two(db_session: AsyncSession) -> None:
    player = await make_user(db_session)
    scenario = await make_scenario(db_session, player)
    for _ in range(3):
        await add_playthrough(db_session, scenario, player, turn_count=1)
    overview = await build_service(db_session).get_overview(player.user_id, NOW)
    assert len(overview.continue_runs) == 2


@pytest.mark.asyncio
async def test_overview_endings_match_the_endings_service(
    db_session: AsyncSession,
) -> None:
    import uuid

    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user, mode="master")
    ashen, consumed = uuid.uuid4(), uuid.uuid4()
    snap = {
        "end_conditions": [
            {
                "outcome_title": "Ashen",
                "outcome_tag": "win",
                "is_secret": False,
                "priority": 0,
                "end_condition_id": str(ashen),
            },
            {
                "outcome_title": "Consumed",
                "outcome_tag": "lose",
                "is_secret": False,
                "priority": 1,
                "end_condition_id": str(consumed),
            },
        ]
    }
    await add_playthrough(
        db_session,
        scenario,
        user,
        turn_count=5,
        status="completed",
        outcome_tag="win",
        outcome_title="Ashen",
        outcome_id=ashen,
        snapshot=snap,
    )

    overview = await build_service(db_session).get_overview(user.user_id, NOW)
    endings = await EndingsService(EndingsRepo(db_session)).get_endings(user.user_id)

    found = sum(story.found_count for story in endings.scenarios)
    total = sum(story.total_count for story in endings.scenarios)
    assert overview.lifetime_stats.endings_found == found == 1
    assert overview.lifetime_stats.endings_total == total == 2
