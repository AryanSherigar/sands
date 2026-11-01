from uuid import UUID, uuid4

from app.engine.hashing import world_hash
from app.models.battle_progress import OperationGuard
from app.models.world_state import WorldState
from app.repositories import playthrough_repo, world_snapshot_repo, world_state_repo
from psycopg import AsyncConnection, sql
from strategy_contracts.scenario import StrategyScenario
from tests.engine.battles.builders import ATTACKER, battle_fixture, start_battle
from tests.repositories.helpers import OWNER_USER_ID

TABLES = (
    "world_state",
    "world_snapshots",
    "turn_hashes",
    "event_log",
    "simulation_operations",
    "simulation_commands",
    "battle_exchanges",
    "scenes",
    "intent_requests",
)


def mutation(
    operation_id: str, version: int, turn: int = 0, wave: int = 0
) -> OperationGuard:
    return OperationGuard(
        operation_id=operation_id,
        expected_world_version=version,
        expected_turn=turn,
        expected_wave=wave,
    )


async def seed_world(
    connection: AsyncConnection, world: WorldState, scenario: StrategyScenario
) -> UUID:
    await connection.set_autocommit(True)
    world.playthrough_id = uuid4()
    async with connection.transaction():
        await playthrough_repo.insert_playthrough(
            connection, world.playthrough_id, OWNER_USER_ID, scenario, 1
        )
        await world_state_repo.insert_world_state(
            connection,
            world.playthrough_id,
            world.schema_version,
            world.clock.turn,
            world_hash(world),
            world.model_dump(mode="json"),
        )
        await world_snapshot_repo.insert_snapshot(
            connection,
            world.playthrough_id,
            world.clock.turn,
            world.schema_version,
            world_hash(world),
            world.model_dump(mode="json"),
        )
    return world.playthrough_id


async def seed_battle(connection: AsyncConnection, orders: int = 6) -> UUID:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    world.factions[ATTACKER].orders_remaining = orders
    return await seed_world(connection, world, scenario)


async def table_counts(connection: AsyncConnection) -> dict[str, int]:
    counts = {}
    for table in TABLES:
        cursor = await connection.execute(
            sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
        )
        counts[table] = (await cursor.fetchone())[0]
    return counts


async def install_failure(connection: AsyncConnection, table: str) -> None:
    await connection.execute("""CREATE FUNCTION task5_fail_write() RETURNS trigger LANGUAGE plpgsql
        AS $$ BEGIN RAISE EXCEPTION 'injected persistence failure'; END $$""")
    await connection.execute(
        sql.SQL(
            "CREATE TRIGGER task5_failure BEFORE INSERT OR UPDATE ON {} "
            "FOR EACH ROW EXECUTE FUNCTION task5_fail_write()"
        ).format(sql.Identifier(table))
    )


async def remove_failure(connection: AsyncConnection, table: str) -> None:
    await connection.execute(
        sql.SQL("DROP TRIGGER task5_failure ON {}").format(sql.Identifier(table))
    )
    await connection.execute("DROP FUNCTION task5_fail_write()")
