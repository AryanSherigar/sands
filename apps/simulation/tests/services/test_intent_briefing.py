from app.config import Settings
from app.models.world_battle import BattleStatus
from app.repositories import intent_request_repo
from app.services.intent_briefing import schedule_intent_requests
from psycopg import AsyncConnection
from tests.engine.battles.builders import DEFENDER, battle_fixture, start_battle
from tests.repositories.helpers import seed_playthrough


async def test_scheduling_is_optional_and_coalesces_turn_requests(
    db_connection: AsyncConnection,
) -> None:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    world.battles[0].status = BattleStatus.AWAITING_COMMANDS
    await seed_playthrough(db_connection, world.playthrough_id)
    settings = Settings(
        intent_provider_enabled=True,
        intent_provider_url="https://provider.invalid/intent",
        intent_provider_api_key="test-only",
        intent_provider_model="fake-model",
    )

    await schedule_intent_requests(db_connection, world, scenario, settings)
    await schedule_intent_requests(db_connection, world, scenario, settings)

    frozen = await intent_request_repo.freeze_intents(
        db_connection, world.playthrough_id, world.clock.turn, 1
    )
    assert len(frozen) == 1
    assert next(iter(frozen.values())).faction_id == DEFENDER


async def test_missing_provider_credentials_do_not_create_or_delay_requests(
    db_connection: AsyncConnection,
) -> None:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    world.battles[0].status = BattleStatus.AWAITING_COMMANDS
    await seed_playthrough(db_connection, world.playthrough_id)

    await schedule_intent_requests(db_connection, world, scenario, Settings())

    cursor = await db_connection.execute(
        "SELECT count(*) FROM intent_requests WHERE playthrough_id = %s",
        (world.playthrough_id,),
    )
    assert await cursor.fetchone() == (0,)
