"""Integration tests for ProfileOverviewRepo aggregates."""

from datetime import UTC, date, datetime

import pytest
from app.repositories.profile_overview_repo import ProfileOverviewRepo
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import (
    add_playthrough,
    add_turn_log,
    make_scenario,
    make_user,
)

WEEK_START = datetime(2026, 10, 26, tzinfo=UTC)
WEEK_END = datetime(2026, 11, 2, tzinfo=UTC)


@pytest.mark.asyncio
async def test_lifetime_counts_empty_user(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    counts = await ProfileOverviewRepo(db_session).get_lifetime_counts(user.user_id)
    assert (
        counts.turns_taken,
        counts.stories_completed,
        counts.worlds_played,
        counts.campaigns_count,
    ) == (0, 0, 0, 0)


@pytest.mark.asyncio
async def test_lifetime_counts_rules(db_session: AsyncSession) -> None:
    player = await make_user(db_session, "Player")
    creator = await make_user(db_session, "Creator")
    scen_a = await make_scenario(db_session, creator, genre_tags=["Noir / Detective"])
    scen_b = await make_scenario(db_session, creator, genre_tags=["Sci-Fi"])
    await add_playthrough(
        db_session,
        scen_a,
        player,
        turn_count=10,
        status="completed",
        outcome_tag="win",
        outcome_title="Case Closed",
    )
    await add_playthrough(
        db_session,
        scen_a,
        player,
        turn_count=4,
        status="completed",
        outcome_tag="lose",
        outcome_title="Case Closed",
    )
    await add_playthrough(
        db_session,
        scen_a,
        player,
        turn_count=6,
        status="completed",
        outcome_tag="lose",
        outcome_title="Cold Trail",
    )
    await add_playthrough(db_session, scen_b, player, turn_count=5, status="abandoned")
    await add_playthrough(db_session, scen_b, player, turn_count=0, status="active")
    await add_playthrough(db_session, scen_b, player, turn_count=99, is_playtest=True)

    counts = await ProfileOverviewRepo(db_session).get_lifetime_counts(player.user_id)

    assert counts.turns_taken == 25  # abandoned counted, playtest excluded
    assert counts.stories_completed == 3
    assert counts.worlds_played == 2  # scen_b has one run with turns
    assert counts.campaigns_count == 5  # playtest excluded


@pytest.mark.asyncio
async def test_lifetime_counts_ignore_other_users(db_session: AsyncSession) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    scenario = await make_scenario(db_session, other)
    await add_playthrough(
        db_session,
        scenario,
        other,
        turn_count=50,
        status="completed",
        outcome_tag="win",
        outcome_title="Done",
    )
    counts = await ProfileOverviewRepo(db_session).get_lifetime_counts(me.user_id)
    assert counts.turns_taken == 0
    assert counts.campaigns_count == 0


@pytest.mark.asyncio
async def test_genre_run_counts_order_and_filters(db_session: AsyncSession) -> None:
    player = await make_user(db_session)
    creator = await make_user(db_session, "Creator")
    noir = await make_scenario(
        db_session, creator, genre_tags=["Noir / Detective", "Mystery"]
    )
    scifi = await make_scenario(db_session, creator, genre_tags=["Sci-Fi"])
    untagged = await make_scenario(db_session, creator, genre_tags=[])
    horror = await make_scenario(db_session, creator, genre_tags=["Horror"])
    await add_playthrough(db_session, noir, player, turn_count=2)
    await add_playthrough(db_session, noir, player, turn_count=3)
    await add_playthrough(db_session, scifi, player, turn_count=1)
    await add_playthrough(db_session, untagged, player, turn_count=9)
    await add_playthrough(db_session, horror, player, turn_count=0)  # no turns
    await add_playthrough(db_session, horror, player, turn_count=8, is_playtest=True)

    rows = await ProfileOverviewRepo(db_session).list_genre_run_counts(player.user_id)

    assert rows == [("Noir / Detective", 2), ("Sci-Fi", 1)]


@pytest.mark.asyncio
async def test_played_dates_bucket_by_utc_and_half_open_range(
    db_session: AsyncSession,
) -> None:
    player = await make_user(db_session)
    scenario = await make_scenario(db_session, player)
    run = await add_playthrough(db_session, scenario, player, turn_count=5)
    stamps = [
        datetime(2026, 10, 25, 23, 59, 59, tzinfo=UTC),  # before the week
        datetime(2026, 10, 26, 0, 0, 0, tzinfo=UTC),  # Monday, first instant
        datetime(2026, 10, 26, 18, 0, tzinfo=UTC),  # same day again
        datetime(2026, 11, 1, 23, 59, 59, tzinfo=UTC),  # Sunday, last second
        datetime(2026, 11, 2, 0, 0, 0, tzinfo=UTC),  # next Monday, excluded
    ]
    for number, stamp in enumerate(stamps, start=1):
        await add_turn_log(db_session, run, number, stamp)

    dates = await ProfileOverviewRepo(db_session).list_played_dates(
        player.user_id, WEEK_START, WEEK_END
    )

    assert sorted(dates) == [date(2026, 10, 26), date(2026, 11, 1)]


@pytest.mark.asyncio
async def test_played_dates_exclude_playtest_and_other_users(
    db_session: AsyncSession,
) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    scenario = await make_scenario(db_session, me)
    playtest = await add_playthrough(db_session, scenario, me, is_playtest=True)
    theirs = await add_playthrough(db_session, scenario, other, turn_count=2)
    noon = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
    await add_turn_log(db_session, playtest, 1, noon)
    await add_turn_log(db_session, theirs, 1, noon)

    dates = await ProfileOverviewRepo(db_session).list_played_dates(
        me.user_id, WEEK_START, WEEK_END
    )

    assert dates == []
