from uuid import uuid4

from app.config import Settings
from app.models.world_faction import StanceState
from app.repositories import stance_request_repo
from app.services.stance_scheduling import schedule_stance_requests
from psycopg import AsyncConnection
from strategy_contracts.scenario import StrategyScenario
from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough
from tests.services.stance_fixtures import (
    AI_FACTION,
    ready_settings,
    single_stance_scenario,
    world_with_ai_leader,
)

SELECT_ROWS = (
    "SELECT request_id, state, due_turn FROM stance_requests ORDER BY request_id"
)


async def _rows(connection: AsyncConnection) -> list[tuple[str, str, int]]:
    cursor = await connection.execute(SELECT_ROWS)
    return await cursor.fetchall()


async def test_schedules_for_next_turn_and_is_idempotent(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    world = world_with_ai_leader()
    for _ in range(2):
        await schedule_stance_requests(
            db_connection, world, StrategyScenario(), ready_settings()
        )
    assert await _rows(db_connection) == [("stance:mira:1", "pending", 1)]


async def test_scheduling_does_not_mutate_the_world(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    world = world_with_ai_leader()
    before = world.model_copy(deep=True)
    await schedule_stance_requests(
        db_connection, world, StrategyScenario(), ready_settings()
    )
    assert world == before


async def test_event_leaders_are_scheduled_early(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    world = world_with_ai_leader()
    world.factions[AI_FACTION].stance = StanceState(option_id="turtle", chosen_turn=0)
    world.clock.turn = 1
    await schedule_stance_requests(
        db_connection, world, StrategyScenario(), ready_settings()
    )
    assert await _rows(db_connection) == []
    await schedule_stance_requests(
        db_connection,
        world,
        StrategyScenario(),
        ready_settings(),
        event_leaders=["mira"],
    )
    assert await _rows(db_connection) == [("stance:mira:2", "pending", 2)]


async def test_single_stance_menu_does_not_call_provider(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await schedule_stance_requests(
        db_connection,
        world_with_ai_leader(),
        single_stance_scenario(),
        ready_settings(),
    )
    assert await _rows(db_connection) == [("stance:mira:1", "fallback", 1)]
    assert await stance_request_repo.claim_requests(db_connection, uuid4(), 5) == []
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert frozen["mira"].option_id == "turtle"
    assert frozen["mira"].reason_code == "single_option"


async def test_provider_disabled_still_creates_fallback_rows(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await schedule_stance_requests(
        db_connection, world_with_ai_leader(), StrategyScenario(), Settings()
    )
    assert await _rows(db_connection) == [("stance:mira:1", "fallback", 1)]
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert frozen["mira"].reason_code == "provider_disabled"
