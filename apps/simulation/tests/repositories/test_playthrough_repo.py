from uuid import uuid4

from app.repositories import playthrough_repo
from strategy_contracts.examples import load_three_crowns

from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import (
    OWNER_USER_ID,
    SCENARIO_SCHEMA_VERSION,
)


async def test_insert_then_repeat(db_connection) -> None:
    args = (
        db_connection,
        PLAYTHROUGH_ID,
        OWNER_USER_ID,
        load_three_crowns(),
        SCENARIO_SCHEMA_VERSION,
    )
    assert await playthrough_repo.insert_playthrough(*args) is True
    assert await playthrough_repo.insert_playthrough(*args) is False


async def test_get_returns_the_stored_scenario(db_connection) -> None:
    await playthrough_repo.insert_playthrough(
        db_connection,
        PLAYTHROUGH_ID,
        OWNER_USER_ID,
        load_three_crowns(),
        SCENARIO_SCHEMA_VERSION,
    )
    row = await playthrough_repo.get_playthrough(db_connection, PLAYTHROUGH_ID)
    assert row is not None
    assert row.owner_user_id == OWNER_USER_ID
    assert row.scenario == load_three_crowns()


async def test_unknown_playthrough_is_none(db_connection) -> None:
    assert await playthrough_repo.get_playthrough(db_connection, uuid4()) is None
