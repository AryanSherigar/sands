"""Integration tests for CreatorStatsRepo aggregations (real Postgres)."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from app.db.models.bookmark import Bookmark
from app.db.models.participant import Participant
from app.db.models.review import ScenarioReview
from app.db.models.share import PlaythroughShare
from app.repositories.creator_stats_repo import CreatorStatsRepo
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import (
    STATS_NOW,
    THRESHOLDS,
    WINDOW_START,
    add_playthrough,
    make_scenario,
    make_user,
)


@pytest.mark.asyncio
async def test_playthrough_totals_counts_statuses_and_excludes_playtests(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    bob = await make_user(db_session, "Bob")
    scenario = await make_scenario(db_session, creator)
    await add_playthrough(
        db_session,
        scenario,
        alice,
        turn_count=12,
        status="completed",
        outcome_tag="win",
    )
    await add_playthrough(
        db_session,
        scenario,
        alice,
        turn_count=2,
        status="completed",
        outcome_tag="lose",
    )
    await add_playthrough(db_session, scenario, bob, turn_count=4, status="abandoned")
    await add_playthrough(db_session, scenario, bob, turn_count=1)
    await add_playthrough(
        db_session, scenario, creator, turn_count=50, is_playtest=True
    )

    rows = await CreatorStatsRepo(db_session).get_playthrough_totals(
        [scenario.scenario_id], WINDOW_START, STATS_NOW, THRESHOLDS
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.plays == 4
    assert (row.active_count, row.ended_count, row.abandoned_count) == (1, 2, 1)
    assert (row.win_count, row.lose_count) == (1, 1)
    assert row.turn_total == 19
    assert row.distinct_players == 2


@pytest.mark.asyncio
async def test_funnel_counts_short_completed_runs_as_passing(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    await add_playthrough(
        db_session,
        scenario,
        alice,
        turn_count=12,
        status="completed",
        outcome_tag="win",
    )
    await add_playthrough(
        db_session,
        scenario,
        alice,
        turn_count=2,
        status="completed",
        outcome_tag="lose",
    )
    await add_playthrough(db_session, scenario, alice, turn_count=4, status="abandoned")
    await add_playthrough(db_session, scenario, alice, turn_count=1)

    rows = await CreatorStatsRepo(db_session).get_playthrough_totals(
        [scenario.scenario_id], WINDOW_START, STATS_NOW, THRESHOLDS
    )

    row = rows[0]
    assert row.reached_turn_counts == (3, 2)
    assert row.plays >= row.reached_turn_counts[0] >= row.reached_turn_counts[1]
    assert row.reached_turn_counts[1] >= row.ended_count


@pytest.mark.asyncio
async def test_multiplayer_counts_playthroughs_with_a_joined_participant(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    bob = await make_user(db_session, "Bob")
    carol = await make_user(db_session, "Carol")
    scenario = await make_scenario(db_session, creator)
    shared = await add_playthrough(db_session, scenario, alice)
    await add_playthrough(db_session, scenario, bob)
    for user, role, position in (
        (alice, "owner", 0),
        (bob, "joined", 1),
        (carol, "joined", 2),
    ):
        db_session.add(
            Participant(
                playthrough_id=shared.playthrough_id,
                user_id=user.user_id,
                role=role,
                turn_order_position=position,
            )
        )
    await db_session.flush()

    rows = await CreatorStatsRepo(db_session).get_playthrough_totals(
        [scenario.scenario_id], WINDOW_START, STATS_NOW, THRESHOLDS
    )

    assert (rows[0].plays, rows[0].multiplayer_count) == (2, 1)


@pytest.mark.asyncio
async def test_window_excludes_older_playthroughs(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    await add_playthrough(
        db_session, scenario, alice, created_at=STATS_NOW - timedelta(days=45)
    )
    await add_playthrough(db_session, scenario, alice)
    repo = CreatorStatsRepo(db_session)

    in_range = await repo.get_playthrough_totals(
        [scenario.scenario_id], WINDOW_START, STATS_NOW, THRESHOLDS
    )
    all_time = await repo.get_playthrough_totals(
        [scenario.scenario_id], None, STATS_NOW, THRESHOLDS
    )

    assert in_range[0].plays == 1
    assert all_time[0].plays == 2


@pytest.mark.asyncio
async def test_play_series_buckets_by_utc_day(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    test_now = datetime(2026, 11, 2, tzinfo=UTC)
    for created_at in (
        datetime(2026, 10, 26, 10, tzinfo=UTC),
        datetime(2026, 10, 26, 11, tzinfo=UTC),
        datetime(2026, 10, 28, 23, 30, tzinfo=UTC),
    ):
        await add_playthrough(db_session, scenario, alice, created_at=created_at)

    series = await CreatorStatsRepo(db_session).get_play_series(
        [scenario.scenario_id], None, test_now, "day"
    )

    assert [(moment.date(), count) for moment, count in series] == [
        (date(2026, 10, 26), 2),
        (date(2026, 10, 28), 1),
    ]


@pytest.mark.asyncio
async def test_play_series_weekly_buckets_start_monday(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    test_now = datetime(2026, 11, 2, tzinfo=UTC)
    await add_playthrough(
        db_session, scenario, alice, created_at=datetime(2026, 10, 28, tzinfo=UTC)
    )
    await add_playthrough(
        db_session, scenario, alice, created_at=datetime(2026, 11, 1, tzinfo=UTC)
    )

    series = await CreatorStatsRepo(db_session).get_play_series(
        [scenario.scenario_id], None, test_now, "week"
    )

    assert [(moment.date(), count) for moment, count in series] == [
        (date(2026, 10, 26), 2)
    ]


@pytest.mark.asyncio
async def test_repeat_and_distinct_players(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    bob = await make_user(db_session, "Bob")
    first = await make_scenario(db_session, creator)
    second = await make_scenario(db_session, creator)
    await add_playthrough(db_session, first, alice)
    await add_playthrough(db_session, first, alice)
    await add_playthrough(db_session, first, bob)
    await add_playthrough(db_session, first, bob, is_playtest=True)
    await add_playthrough(db_session, second, alice)
    repo = CreatorStatsRepo(db_session)

    repeat = await repo.count_repeat_players(
        first.scenario_id, WINDOW_START, STATS_NOW, 2
    )
    distinct = await repo.count_distinct_players(
        [first.scenario_id, second.scenario_id], WINDOW_START, STATS_NOW
    )

    assert repeat == 1
    assert distinct == 2


@pytest.mark.asyncio
async def test_turn_count_frequencies(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    for turns in (3, 3, 7):
        await add_playthrough(db_session, scenario, alice, turn_count=turns)

    frequencies = await CreatorStatsRepo(db_session).get_turn_count_frequencies(
        scenario.scenario_id, WINDOW_START, STATS_NOW
    )

    assert sorted(frequencies) == [(3, 2), (7, 1)]


@pytest.mark.asyncio
async def test_rating_counts_respect_window(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    scenario = await make_scenario(db_session, creator)
    for rating, age_days in ((5, 1), (5, 2), (3, 3), (1, 60)):
        reviewer = await make_user(db_session, "Reviewer")
        db_session.add(
            ScenarioReview(
                scenario_id=scenario.scenario_id,
                user_id=reviewer.user_id,
                rating=rating,
                created_at=STATS_NOW - timedelta(days=age_days),
            )
        )
    await db_session.flush()

    rows = await CreatorStatsRepo(db_session).get_rating_counts(
        [scenario.scenario_id], WINDOW_START, STATS_NOW
    )

    assert sorted((rating, count) for _, rating, count in rows) == [(3, 1), (5, 2)]


@pytest.mark.asyncio
async def test_latest_reviews_are_newest_first_with_author_names(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    scenario = await make_scenario(db_session, creator)
    for name, age_days in (("Older", 3), ("Newest", 1), ("Middle", 2)):
        reviewer = await make_user(db_session, name)
        db_session.add(
            ScenarioReview(
                scenario_id=scenario.scenario_id,
                user_id=reviewer.user_id,
                rating=4,
                comment=f"From {name}",
                created_at=STATS_NOW - timedelta(days=age_days),
            )
        )
    await db_session.flush()

    rows = await CreatorStatsRepo(db_session).list_latest_reviews(
        [scenario.scenario_id], WINDOW_START, STATS_NOW, 2
    )

    assert [row.author_display_name for row in rows] == ["Newest", "Middle"]
    assert rows[0].scenario_title == scenario.title
    assert rows[0].comment == "From Newest"


@pytest.mark.asyncio
async def test_bookmark_and_share_counts(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    db_session.add(Bookmark(user_id=alice.user_id, scenario_id=scenario.scenario_id))
    real = await add_playthrough(db_session, scenario, alice)
    second_real = await add_playthrough(db_session, scenario, alice)
    playtest = await add_playthrough(db_session, scenario, creator, is_playtest=True)
    for playthrough, mode in (
        (real, "spectate"),
        (real, "join"),
        (second_real, "spectate"),
        (playtest, "join"),
    ):
        db_session.add(
            PlaythroughShare(
                share_token=uuid.uuid4().hex,
                playthrough_id=playthrough.playthrough_id,
                mode=mode,
                expires_at=STATS_NOW + timedelta(days=30),
            )
        )
    await db_session.flush()
    repo = CreatorStatsRepo(db_session)
    window_end = STATS_NOW + timedelta(minutes=5)

    bookmarks = await repo.count_bookmarks(
        scenario.scenario_id, WINDOW_START, window_end
    )
    shares = await repo.get_share_counts(scenario.scenario_id, WINDOW_START, window_end)

    assert bookmarks == 1
    assert shares == {"spectate": 2, "join": 1}


@pytest.mark.asyncio
async def test_list_stats_scenarios_filters_status_and_owner(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    other = await make_user(db_session, "Other")
    published = await make_scenario(db_session, creator, status="published")
    archived = await make_scenario(db_session, creator, status="archived")
    await make_scenario(db_session, creator, status="draft")
    await make_scenario(db_session, other, status="published")

    scenarios = await CreatorStatsRepo(db_session).list_stats_scenarios(
        creator.user_id, ["published", "archived"]
    )

    assert {scenario.scenario_id for scenario in scenarios} == {
        published.scenario_id,
        archived.scenario_id,
    }
