import uuid

import pytest
from app.db.models.scenario import Scenario
from app.exceptions.scenario_exceptions import ScenarioAlreadyPublishingError
from app.repositories.user_repo import UserRepo
from scripts.aldermark.builder import scenario_columns
from scripts.aldermark.ids import SCENARIO_ID
from scripts.aldermark.persist import persist
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

MAP_URL = "https://media.example.test/aldermark/map.webp"


@pytest.fixture
async def creator(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


async def _count(session: AsyncSession) -> int:
    statement = (
        select(func.count())
        .select_from(Scenario)
        .where(Scenario.scenario_id == SCENARIO_ID)
    )
    return (await session.execute(statement)).scalar_one()


@pytest.mark.asyncio
async def test_persist_writes_a_draft_strategy_scenario(db_session, creator) -> None:
    scenario = await persist(db_session, scenario_columns(MAP_URL), creator.user_id)

    assert scenario.scenario_id == SCENARIO_ID
    assert scenario.status == "draft"
    assert scenario.mode == "strategy"
    assert scenario.creator_id == creator.user_id


@pytest.mark.asyncio
async def test_persisting_twice_replaces_the_row_in_place(db_session, creator) -> None:
    await persist(db_session, scenario_columns(MAP_URL), creator.user_id)
    await persist(db_session, scenario_columns(MAP_URL), creator.user_id)

    assert await _count(db_session) == 1


@pytest.mark.asyncio
async def test_a_scenario_that_is_publishing_is_not_overwritten(
    db_session, creator
) -> None:
    scenario = await persist(db_session, scenario_columns(MAP_URL), creator.user_id)
    scenario.status = "publishing"
    await db_session.flush()

    with pytest.raises(ScenarioAlreadyPublishingError):
        await persist(db_session, scenario_columns(MAP_URL), creator.user_id)
