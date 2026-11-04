import uuid

import pytest
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.scenario_exceptions import ScenarioNotFoundError
from app.repositories.creator_stats_repo import CreatorStatsRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.creator_stats_service import CreatorStatsService
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import add_playthrough, make_scenario, make_user


def build_service(session: AsyncSession) -> CreatorStatsService:
    return CreatorStatsService(CreatorStatsRepo(session), ScenarioRepo(session))


@pytest.mark.asyncio
async def test_owner_gets_stats_without_playtests(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    for _ in range(5):
        await add_playthrough(db_session, scenario, alice, turn_count=4)
    await add_playthrough(
        db_session, scenario, creator, turn_count=40, is_playtest=True
    )

    response = await build_service(db_session).get_scenario_stats(
        scenario.scenario_id, creator.user_id, "30d"
    )

    assert response.plays.total_plays == 5
    assert response.is_sample_sufficient is True
    assert response.engagement.average_turns == 4.0
    assert response.funnel.retention_rate == 1.0


@pytest.mark.asyncio
async def test_non_owner_gets_not_found(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    stranger = await make_user(db_session, "Stranger")
    scenario = await make_scenario(db_session, creator)

    with pytest.raises(ScenarioNotFoundError):
        await build_service(db_session).get_scenario_stats(
            scenario.scenario_id, stranger.user_id, "30d"
        )


@pytest.mark.asyncio
async def test_missing_scenario_gets_not_found(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    with pytest.raises(ScenarioNotFoundError):
        await build_service(db_session).get_scenario_stats(
            uuid.uuid4(), creator.user_id, "30d"
        )


@pytest.mark.asyncio
async def test_draft_returns_empty_stats(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    scenario = await make_scenario(db_session, creator, status="draft")

    response = await build_service(db_session).get_scenario_stats(
        scenario.scenario_id, creator.user_id, "30d"
    )

    assert response.scenario.has_stats is False
    assert response.plays.total_plays == 0


@pytest.mark.asyncio
async def test_overview_lists_only_callers_published_and_archived(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    other = await make_user(db_session, "Other")
    alice = await make_user(db_session, "Alice")
    published = await make_scenario(db_session, creator, status="published")
    archived = await make_scenario(db_session, creator, status="archived")
    await make_scenario(db_session, creator, status="draft")
    foreign = await make_scenario(db_session, other, status="published")
    await add_playthrough(db_session, published, alice)
    await add_playthrough(db_session, foreign, alice)

    response = await build_service(db_session).get_overview(creator.user_id, "30d")

    assert {row.scenario_id for row in response.scenarios} == {
        published.scenario_id,
        archived.scenario_id,
    }
    assert response.totals.plays.value == 1
    assert response.totals.plays.trend is not None
    assert response.totals.plays.trend.is_new is True


@pytest.mark.asyncio
async def test_overview_for_creator_without_scenarios(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    response = await build_service(db_session).get_overview(creator.user_id, "7d")
    assert response.has_published_scenarios is False
    assert response.scenarios == []


async def add_scenario_with_plays(
    session: AsyncSession, creator: User, player: User, genre_tag: str, plays: int = 5
) -> Scenario:
    scenario = await make_scenario(session, creator, genre_tags=[genre_tag])
    for _ in range(plays):
        await add_playthrough(
            session,
            scenario,
            player,
            turn_count=6,
            status="completed",
            outcome_tag="win",
        )
    return scenario


@pytest.mark.asyncio
async def test_benchmarks_use_genre_peers(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    player = await make_user(db_session, "Player")
    tag = f"genre-{uuid.uuid4().hex[:8]}"
    target = await add_scenario_with_plays(db_session, creator, player, tag)
    for _ in range(5):
        await add_scenario_with_plays(db_session, creator, player, tag)

    response = await build_service(db_session).get_scenario_stats(
        target.scenario_id, creator.user_id, "30d"
    )

    assert response.benchmarks is not None
    assert response.benchmarks.peer_scope == "genre"
    assert response.benchmarks.peer_count == 5


@pytest.mark.asyncio
async def test_benchmarks_fall_back_to_mode_peers(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    player = await make_user(db_session, "Player")
    target = await add_scenario_with_plays(
        db_session, creator, player, f"genre-{uuid.uuid4().hex[:8]}"
    )
    for _ in range(5):
        await add_scenario_with_plays(
            db_session, creator, player, f"genre-{uuid.uuid4().hex[:8]}"
        )

    response = await build_service(db_session).get_scenario_stats(
        target.scenario_id, creator.user_id, "30d"
    )

    assert response.benchmarks is not None
    assert response.benchmarks.peer_scope == "mode"


@pytest.mark.asyncio
async def test_benchmarks_hidden_under_five_peers(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    player = await make_user(db_session, "Player")
    target = await make_scenario(
        db_session,
        creator,
        mode="newbie",
        genre_tags=[f"genre-{uuid.uuid4().hex[:8]}"],
    )
    for _ in range(5):
        await add_playthrough(
            db_session, target, player, turn_count=6, status="completed"
        )

    response = await build_service(db_session).get_scenario_stats(
        target.scenario_id, creator.user_id, "30d"
    )

    assert response.outcomes is None
    assert response.heatmap == []
    if response.benchmarks is not None:
        assert response.benchmarks.peer_count >= 5
