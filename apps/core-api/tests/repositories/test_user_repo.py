"""Integration tests for UserRepo stats aggregation and query efficiency."""

import uuid

import pytest
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.repositories.user_repo import UserRepo
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    user = User(
        user_id=uuid.uuid4(),
        display_name="Stat Tester",
        auth_provider_id=f"test-auth-{uuid.uuid4()}",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = User(
        user_id=uuid.uuid4(),
        display_name="Other Tester",
        auth_provider_id=f"test-auth-{uuid.uuid4()}",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def base_scenario(db_session: AsyncSession, other_user: User) -> Scenario:
    scenario = Scenario(
        scenario_id=uuid.uuid4(),
        creator_id=other_user.user_id,
        title="Base Scenario",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="both",
        status="published",
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


@pytest.mark.asyncio
async def test_get_user_stats_empty(db_session: AsyncSession, user: User) -> None:
    repo = UserRepo(db_session)
    stats = await repo.get_user_stats(user.user_id)

    assert stats == {
        "campaigns_played_count": 0,
        "victories_count": 0,
        "total_turns_taken": 0,
        "scenarios_authored_count": 0,
        "total_plays_received": 0,
    }


@pytest.mark.asyncio
async def test_get_player_stats_filtering(
    db_session: AsyncSession, user: User, base_scenario: Scenario
) -> None:
    repo = UserRepo(db_session)

    # 1. Winning non-playtest campaign (10 turns)
    db_session.add(
        Playthrough(
            scenario_id=base_scenario.scenario_id,
            created_by=user.user_id,
            scenario_version=1,
            turn_count=10,
            status="completed",
            ended_outcome_tag="win",
            is_playtest=False,
            state={},
        )
    )

    # 2. Losing non-playtest campaign (5 turns)
    db_session.add(
        Playthrough(
            scenario_id=base_scenario.scenario_id,
            created_by=user.user_id,
            scenario_version=1,
            turn_count=5,
            status="completed",
            ended_outcome_tag="lose",
            is_playtest=False,
            state={},
        )
    )

    # 3. Active campaign without outcome (3 turns)
    db_session.add(
        Playthrough(
            scenario_id=base_scenario.scenario_id,
            created_by=user.user_id,
            scenario_version=1,
            turn_count=3,
            status="active",
            ended_outcome_tag=None,
            is_playtest=False,
            state={},
        )
    )

    # 4. Playtest campaign (must be excluded from player stats)
    db_session.add(
        Playthrough(
            scenario_id=base_scenario.scenario_id,
            created_by=user.user_id,
            scenario_version=1,
            turn_count=20,
            status="completed",
            ended_outcome_tag="win",
            is_playtest=True,
            state={},
        )
    )
    await db_session.flush()

    campaigns, victories, total_turns = await repo.get_player_stats(user.user_id)
    assert campaigns == 3
    assert victories == 1
    assert total_turns == 18


@pytest.mark.asyncio
async def test_get_creator_stats_filtering(
    db_session: AsyncSession, user: User
) -> None:
    repo = UserRepo(db_session)

    # Published scenario 1
    db_session.add(
        Scenario(
            creator_id=user.user_id,
            title="Published World 1",
            mode="newbie",
            complexity_tier="newbie",
            player_count_support="solo",
            status="published",
            play_count=15,
        )
    )

    # Published scenario 2
    db_session.add(
        Scenario(
            creator_id=user.user_id,
            title="Published World 2",
            mode="master",
            complexity_tier="master",
            player_count_support="both",
            status="published",
            play_count=25,
        )
    )

    # Draft scenario (must be excluded)
    db_session.add(
        Scenario(
            creator_id=user.user_id,
            title="Draft World",
            mode="newbie",
            complexity_tier="newbie",
            player_count_support="solo",
            status="draft",
            play_count=100,
        )
    )
    await db_session.flush()

    scenarios, total_plays = await repo.get_creator_stats(user.user_id)
    assert scenarios == 2
    assert total_plays == 40


@pytest.mark.asyncio
async def test_query_count_consolidation(
    test_engine: AsyncEngine, db_session: AsyncSession, user: User
) -> None:
    repo = UserRepo(db_session)
    executed_statements: list[str] = []

    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        executed_statements.append(statement)

    event.listen(
        test_engine.sync_engine, "before_cursor_execute", before_cursor_execute
    )
    try:
        # Test get_player_stats query count
        executed_statements.clear()
        await repo.get_player_stats(user.user_id)
        assert len(executed_statements) == 1

        # Test get_creator_stats query count
        executed_statements.clear()
        await repo.get_creator_stats(user.user_id)
        assert len(executed_statements) == 1

        # Test get_user_stats total query count
        executed_statements.clear()
        await repo.get_user_stats(user.user_id)
        assert len(executed_statements) == 2
    finally:
        event.remove(
            test_engine.sync_engine, "before_cursor_execute", before_cursor_execute
        )
