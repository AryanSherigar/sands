"""Integration tests for PlaythroughRepo against a real test Postgres instance."""

import uuid

import pytest
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.repositories.playthrough_repo import PlaythroughRepo
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    user = User(
        user_id=uuid.uuid4(),
        display_name="Tester",
        auth_provider_id=f"test-auth-{uuid.uuid4()}",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def scenario(db_session: AsyncSession, user: User) -> Scenario:
    scenario = Scenario(
        scenario_id=uuid.uuid4(),
        creator_id=user.user_id,
        title="Test Scenario",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="both",
        status="published",
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


@pytest.fixture
async def playthrough(
    db_session: AsyncSession, user: User, scenario: Scenario
) -> Playthrough:
    playthrough = Playthrough(
        playthrough_id=uuid.uuid4(),
        scenario_id=scenario.scenario_id,
        created_by=user.user_id,
        scenario_version=1,
        state={"setup": {}},
    )
    db_session.add(playthrough)
    await db_session.flush()
    return playthrough


@pytest.mark.asyncio
async def test_get_by_id_for_update_returns_playthrough(
    db_session: AsyncSession, playthrough: Playthrough
) -> None:
    repo = PlaythroughRepo(db_session)
    result = await repo.get_by_id_for_update(playthrough.playthrough_id)
    assert result is not None
    assert result.playthrough_id == playthrough.playthrough_id


@pytest.mark.asyncio
async def test_get_by_id_for_update_returns_none_for_unknown(
    db_session: AsyncSession,
) -> None:
    repo = PlaythroughRepo(db_session)
    result = await repo.get_by_id_for_update(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_list_recent_active_with_scenarios_orders_limits_and_filters(
    db_session: AsyncSession,
) -> None:
    from datetime import UTC, datetime, timedelta

    from tests.stats_factories import add_playthrough, make_scenario, make_user

    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    scenario = await make_scenario(db_session, me)
    now = datetime.now(UTC)
    oldest = await add_playthrough(db_session, scenario, me, turn_count=1)
    newest = await add_playthrough(db_session, scenario, me, turn_count=2)
    middle = await add_playthrough(db_session, scenario, me, turn_count=3)
    await add_playthrough(db_session, scenario, me, status="completed")
    await add_playthrough(db_session, scenario, me, is_playtest=True)
    await add_playthrough(db_session, scenario, other)
    for run, age in ((oldest, 3), (middle, 2), (newest, 1)):
        run.updated_at = now - timedelta(days=age)
    await db_session.flush()

    rows = await PlaythroughRepo(db_session).list_recent_active_with_scenarios(
        me.user_id, limit=2
    )

    assert [pt.playthrough_id for pt, _ in rows] == [
        newest.playthrough_id,
        middle.playthrough_id,
    ]
    assert all(scen.scenario_id == scenario.scenario_id for _, scen in rows)
