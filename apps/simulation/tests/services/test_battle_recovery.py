import asyncio
from uuid import UUID, uuid4

import pytest
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import DeceiveCommand, ReconCommand
from app.models.battle_intelligence import MissionTarget
from app.models.battle_progress import CampaignState, MutationResponse, OperationGuard
from app.repositories import battle_exchange_repo, world_snapshot_repo, world_state_repo
from app.services.battle_service import BattleService
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from psycopg import AsyncConnection
from psycopg.errors import RaiseException
from tests.engine.battles.builders import ATTACKER, DEFENDER
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import (
    install_failure,
    mutation,
    remove_failure,
    seed_battle,
    table_counts,
)


async def test_wave2_lost_response_restart_and_stale_operation(
    db_connection: AsyncConnection, migrated_test_database_url: str
) -> None:
    identity = await seed_battle(db_connection)
    service = CampaignService(db_connection)
    opened = await service.begin(identity, OWNER_USER_ID, mutation("begin", 1))
    first = await service.advance(
        identity, OWNER_USER_ID, mutation("wave1", opened.world_version, wave=1)
    )
    second_guard = mutation("wave2", first.world_version, wave=2)
    second = await service.advance(identity, OWNER_USER_ID, second_guard)
    before = await table_counts(db_connection)
    await verify_restart(migrated_test_database_url, identity, second_guard, second)
    assert await table_counts(db_connection) == before
    assert before["battle_exchanges"] == 2 and before["world_snapshots"] == 1
    third = await advance_on_fresh_connection(
        migrated_test_database_url,
        identity,
        mutation("wave3", second.world_version, wave=3),
    )
    fourth = await advance_on_fresh_connection(
        migrated_test_database_url,
        identity,
        mutation("wave4", third.world_version, wave=4),
    )
    assert fourth.turn == 1 and fourth.status == "turn_completed"
    assert (await table_counts(db_connection))["battle_exchanges"] == 4
    next_turn = await begin_on_fresh_connection(
        migrated_test_database_url,
        identity,
        mutation("begin-next", fourth.world_version, turn=1),
    )
    next_wave = await advance_on_fresh_connection(
        migrated_test_database_url,
        identity,
        mutation("wave-next", next_turn.world_version, turn=1, wave=1),
    )
    assert next_wave.turn == 1 and next_wave.wave == 1
    loaded = await load_state_on_fresh_connection(migrated_test_database_url, identity)
    assert loaded.battles[0].total_exchanges == 5
    with pytest.raises(CommandError, match="stale"):
        await service.advance(
            identity,
            OWNER_USER_ID,
            second_guard.model_copy(update={"operation_id": "other"}),
        )
    receipt = await battle_exchange_repo.list_exchanges(
        db_connection, identity, "battle_1"
    )
    assert len(receipt) == 5
    assert receipt[1].output_hash == second.world_hash


async def test_authorization_precedes_receipt_lookup(
    db_connection: AsyncConnection,
) -> None:
    identity = await seed_battle(db_connection)
    request = mutation("begin", 1)
    await CampaignService(db_connection).begin(identity, OWNER_USER_ID, request)
    for resource in (identity, uuid4()):
        with pytest.raises(PlaythroughNotFoundError):
            await CampaignService(db_connection).begin(resource, uuid4(), request)


async def _accept_on_connection(
    database_url: str,
    identity: UUID,
    operation_id: str,
    command: DeceiveCommand | ReconCommand,
) -> MutationResponse:
    async with await AsyncConnection.connect(
        database_url, autocommit=True
    ) as connection:
        return await CommandService(connection).accept(
            identity, OWNER_USER_ID, mutation(operation_id, 2, wave=1), command
        )


async def test_concurrent_identical_retry_returns_first_committed_result(
    db_connection: AsyncConnection, migrated_test_database_url: str
) -> None:
    identity = await seed_battle(db_connection, orders=1)
    await CampaignService(db_connection).begin(
        identity, OWNER_USER_ID, mutation("begin", 1)
    )
    command = DeceiveCommand(faction_id=ATTACKER, battle_id="battle_1")
    results = await asyncio.gather(
        *[
            _accept_on_connection(migrated_test_database_url, identity, "same", command)
            for _ in range(2)
        ]
    )
    assert results[0] == results[1]
    assert results[0].orders_remaining == 0
    assert (await table_counts(db_connection))["simulation_commands"] == 1


async def test_concurrent_different_last_point_commands_spend_once(
    db_connection: AsyncConnection, migrated_test_database_url: str
) -> None:
    identity = await seed_battle(db_connection, orders=1)
    await CampaignService(db_connection).begin(
        identity, OWNER_USER_ID, mutation("begin", 1)
    )
    commands = competing_commands()
    results = await asyncio.gather(
        *[
            _accept_on_connection(
                migrated_test_database_url, identity, f"op{index}", command
            )
            for index, command in enumerate(commands)
        ],
        return_exceptions=True,
    )
    assert sum(isinstance(result, CommandError) for result in results) == 1
    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert (
        await BattleService(db_connection).load_state(identity, OWNER_USER_ID)
    ).orders_remaining == 0


@pytest.mark.parametrize(
    "table",
    [
        "simulation_commands",
        "event_log",
        "battle_exchanges",
        "world_state",
        "world_snapshots",
        "turn_hashes",
        "simulation_operations",
    ],
)
async def test_final_wave_write_failures_roll_back_every_effect(
    db_connection: AsyncConnection, table: str
) -> None:
    identity, service, response = await prepare_final_wave(db_connection)
    before = await table_counts(db_connection)
    row_before = await world_state_repo.get_world_state(db_connection, identity)
    await install_failure(db_connection, table)
    request = mutation("wave4", response.world_version, wave=4)
    try:
        with pytest.raises(RaiseException, match="injected persistence failure"):
            await service.advance(identity, OWNER_USER_ID, request)
    finally:
        await remove_failure(db_connection, table)
    assert await table_counts(db_connection) == before
    assert await world_state_repo.get_world_state(db_connection, identity) == row_before
    completed = await service.advance(identity, OWNER_USER_ID, request)
    assert completed.turn == 1 and completed.status == "turn_completed"
    assert (await table_counts(db_connection))["world_snapshots"] == 2
    snapshot = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, identity, 1
    )
    assert snapshot.world_hash == completed.world_hash


async def test_cancellation_before_commit_rolls_back_wave(
    db_connection: AsyncConnection,
) -> None:
    identity = await seed_battle(db_connection)
    service = CampaignService(db_connection)
    await service.begin(identity, OWNER_USER_ID, mutation("begin", 1))
    before = await table_counts(db_connection)
    row_before = await world_state_repo.get_world_state(db_connection, identity)
    await db_connection.execute("""CREATE FUNCTION task5_cancel_write() RETURNS trigger LANGUAGE plpgsql
        AS $$ BEGIN PERFORM pg_sleep(5); RETURN NEW; END $$""")
    await db_connection.execute("""CREATE TRIGGER task5_cancellation BEFORE INSERT ON simulation_operations
        FOR EACH ROW EXECUTE FUNCTION task5_cancel_write()""")
    try:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(
                service.advance(identity, OWNER_USER_ID, mutation("wave1", 2, wave=1)),
                timeout=0.1,
            )
    finally:
        await db_connection.execute(
            "DROP TRIGGER task5_cancellation ON simulation_operations"
        )
        await db_connection.execute("DROP FUNCTION task5_cancel_write()")
    assert await table_counts(db_connection) == before
    assert await world_state_repo.get_world_state(db_connection, identity) == row_before
    assert (
        await service.advance(identity, OWNER_USER_ID, mutation("wave1", 2, wave=1))
    ).wave == 1


async def verify_restart(
    database_url: str, identity: UUID, guard: OperationGuard, expected: MutationResponse
) -> None:
    async with await AsyncConnection.connect(database_url, autocommit=True) as fresh:
        assert (
            await CampaignService(fresh).advance(identity, OWNER_USER_ID, guard)
            == expected
        )
        assert (
            await BattleService(fresh).load_state(identity, OWNER_USER_ID)
        ).world_hash == expected.world_hash


async def advance_on_fresh_connection(
    database_url: str, identity: UUID, guard: OperationGuard
) -> MutationResponse:
    async with await AsyncConnection.connect(database_url, autocommit=True) as fresh:
        return await CampaignService(fresh).advance(identity, OWNER_USER_ID, guard)


async def begin_on_fresh_connection(
    database_url: str, identity: UUID, guard: OperationGuard
) -> MutationResponse:
    async with await AsyncConnection.connect(database_url, autocommit=True) as fresh:
        return await CampaignService(fresh).begin(identity, OWNER_USER_ID, guard)


async def load_state_on_fresh_connection(
    database_url: str, identity: UUID
) -> CampaignState:
    async with await AsyncConnection.connect(database_url, autocommit=True) as fresh:
        return await BattleService(fresh).load_state(identity, OWNER_USER_ID)


def competing_commands() -> list[DeceiveCommand | ReconCommand]:
    return [
        DeceiveCommand(faction_id=ATTACKER, battle_id="battle_1"),
        ReconCommand(
            faction_id=ATTACKER,
            battle_id="battle_1",
            subject_faction_id=DEFENDER,
            target=MissionTarget.COMPOSITION,
        ),
    ]


async def prepare_final_wave(
    db_connection: AsyncConnection,
) -> tuple[UUID, CampaignService, MutationResponse]:
    identity = await seed_battle(db_connection)
    service = CampaignService(db_connection)
    response = await service.begin(identity, OWNER_USER_ID, mutation("begin", 1))
    for wave in range(1, 4):
        response = await service.advance(
            identity,
            OWNER_USER_ID,
            mutation(f"wave{wave}", response.world_version, wave=wave),
        )
    response = await CommandService(db_connection).accept(
        identity,
        OWNER_USER_ID,
        mutation("final-deception", response.world_version, wave=4),
        DeceiveCommand(faction_id=ATTACKER, battle_id="battle_1"),
    )
    return identity, service, response
