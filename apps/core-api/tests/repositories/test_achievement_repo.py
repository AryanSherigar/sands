"""Integration tests for AchievementRepo."""

from datetime import UTC, datetime, timedelta

import pytest
from app.db.models.review import ScenarioReview
from app.repositories.achievement_repo import AchievementRepo
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import add_playthrough, make_scenario, make_user

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_insert_earned_is_idempotent_and_never_moves_earned_at(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    repo = AchievementRepo(db_session)

    first = await repo.insert_earned(user.user_id, ["first-steps", "wayfarer"], NOW)
    second = await repo.insert_earned(
        user.user_id, ["first-steps", "voyager"], NOW + timedelta(days=1)
    )

    assert sorted(first) == ["first-steps", "wayfarer"]
    assert second == ["voyager"]
    rows = {row.key: row.earned_at for row in await repo.list_earned(user.user_id)}
    assert rows["first-steps"] == NOW
    assert rows["voyager"] == NOW + timedelta(days=1)


@pytest.mark.asyncio
async def test_insert_earned_with_no_keys_and_list_is_per_user(
    db_session: AsyncSession,
) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    repo = AchievementRepo(db_session)
    assert await repo.insert_earned(me.user_id, [], NOW) == []
    await repo.insert_earned(other.user_id, ["crowd"], NOW)
    assert await repo.list_earned(me.user_id) == []


@pytest.mark.asyncio
async def test_count_wins_excludes_playtests_losses_and_other_users(
    db_session: AsyncSession,
) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    scenario = await make_scenario(db_session, me)
    await add_playthrough(
        db_session,
        scenario,
        me,
        turn_count=5,
        status="completed",
        outcome_tag="win",
        outcome_title="A",
    )
    await add_playthrough(
        db_session,
        scenario,
        me,
        turn_count=5,
        status="completed",
        outcome_tag="lose",
        outcome_title="B",
    )
    await add_playthrough(
        db_session,
        scenario,
        me,
        turn_count=5,
        status="completed",
        outcome_tag="win",
        outcome_title="C",
        is_playtest=True,
    )
    await add_playthrough(
        db_session,
        scenario,
        other,
        turn_count=5,
        status="completed",
        outcome_tag="win",
        outcome_title="D",
    )
    assert await AchievementRepo(db_session).count_wins(me.user_id) == 1


@pytest.mark.asyncio
async def test_creator_metrics_only_count_published_scenarios(
    db_session: AsyncSession,
) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    published = await make_scenario(db_session, me)
    published.published_at = NOW
    published.play_count = 12
    archived_after_publish = await make_scenario(db_session, me, status="archived")
    archived_after_publish.published_at = NOW
    archived_after_publish.play_count = 3
    draft = await make_scenario(db_session, me, status="draft")
    draft.play_count = 500  # never published: must not count
    theirs = await make_scenario(db_session, other)
    theirs.published_at = NOW
    theirs.play_count = 900
    await db_session.flush()

    metrics = await AchievementRepo(db_session).get_creator_metrics(me.user_id)

    assert (metrics.published_count, metrics.plays_received) == (2, 15)


@pytest.mark.asyncio
async def test_creator_metrics_for_a_user_with_nothing(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    metrics = await AchievementRepo(db_session).get_creator_metrics(user.user_id)
    assert (metrics.published_count, metrics.plays_received) == (0, 0)


@pytest.mark.asyncio
async def test_five_star_reviews_exclude_self_lower_ratings_and_other_creators(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    fan = await make_user(db_session, "Fan")
    other_fan = await make_user(db_session, "OtherFan")
    other_creator = await make_user(db_session, "OtherCreator")
    mine = await make_scenario(db_session, creator)
    theirs = await make_scenario(db_session, other_creator)
    db_session.add_all(
        [
            ScenarioReview(
                scenario_id=mine.scenario_id,
                user_id=fan.user_id,
                rating=5,
                comment="a",
            ),
            ScenarioReview(
                scenario_id=mine.scenario_id,
                user_id=creator.user_id,
                rating=5,
                comment="self",
            ),
            ScenarioReview(
                scenario_id=theirs.scenario_id,
                user_id=fan.user_id,
                rating=5,
                comment="elsewhere",
            ),
            ScenarioReview(
                scenario_id=mine.scenario_id,
                user_id=other_fan.user_id,
                rating=4,
                comment="four",
            ),
        ]
    )
    await db_session.flush()

    count = await AchievementRepo(db_session).count_five_star_reviews(creator.user_id)
    assert count == 1
