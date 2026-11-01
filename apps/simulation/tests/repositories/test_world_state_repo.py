from uuid import uuid4

import pytest
from app.engine.hashing import world_hash
from app.engine.world_document import world_from_document
from app.models.world_army import MarchState
from app.repositories import world_state_repo
from psycopg.errors import ForeignKeyViolation

from tests.models.builders import PLAYTHROUGH_ID, make_world
from tests.repositories.helpers import seed_playthrough

SCHEMA_VERSION = 1


async def _insert_world(connection, turn: int = 0, digest: str = "h0") -> None:
    await world_state_repo.insert_world_state(
        connection, PLAYTHROUGH_ID, SCHEMA_VERSION, turn, digest, {"a": 1}
    )


async def test_insert_for_unknown_playthrough_violates_foreign_key(
    db_connection,
) -> None:
    with pytest.raises(ForeignKeyViolation):
        await world_state_repo.insert_world_state(
            db_connection, uuid4(), SCHEMA_VERSION, 0, "h", {}
        )


async def test_insert_twice_reports_second_as_not_inserted(db_connection) -> None:
    await seed_playthrough(db_connection)
    first = await world_state_repo.insert_world_state(
        db_connection, PLAYTHROUGH_ID, SCHEMA_VERSION, 0, "h", {}
    )
    second = await world_state_repo.insert_world_state(
        db_connection, PLAYTHROUGH_ID, SCHEMA_VERSION, 0, "h", {}
    )
    assert (first, second) == (True, False)


async def test_world_survives_a_database_round_trip_with_the_same_hash(
    db_connection,
) -> None:
    await seed_playthrough(db_connection)
    world = make_world()
    digest = world_hash(world)
    await world_state_repo.insert_world_state(
        db_connection,
        PLAYTHROUGH_ID,
        world.schema_version,
        world.clock.turn,
        digest,
        world.model_dump(mode="json"),
    )
    row = await world_state_repo.get_world_state(db_connection, PLAYTHROUGH_ID)
    assert row is not None
    reloaded = world_from_document(row.document)
    assert reloaded == world
    assert world_hash(reloaded) == digest == row.world_hash


async def test_stale_writer_does_not_overwrite(db_connection) -> None:
    await seed_playthrough(db_connection)
    await _insert_world(db_connection)
    first = await world_state_repo.update_world_state(
        db_connection, PLAYTHROUGH_ID, 1, SCHEMA_VERSION, 1, "first", {"a": 2}
    )
    stale = await world_state_repo.update_world_state(
        db_connection, PLAYTHROUGH_ID, 1, SCHEMA_VERSION, 9, "stale", {"a": 9}
    )
    row = await world_state_repo.get_world_state(db_connection, PLAYTHROUGH_ID)
    assert first == 2
    assert stale is None
    assert (row.turn, row.world_hash, row.row_version) == (1, "first", 2)


async def test_get_with_lock_inside_a_transaction(db_connection) -> None:
    await seed_playthrough(db_connection)
    await _insert_world(db_connection)
    async with db_connection.transaction():
        row = await world_state_repo.get_world_state(
            db_connection, PLAYTHROUGH_ID, should_lock=True
        )
    assert row is not None
    assert row.row_version == 1


async def test_unknown_world_is_none(db_connection) -> None:
    assert await world_state_repo.get_world_state(db_connection, uuid4()) is None


async def test_world_with_a_march_in_flight_survives_the_database_round_trip(
    db_connection,
) -> None:
    await seed_playthrough(db_connection)
    world = make_world()
    world.armies["army_a"].march = MarchState(
        from_id="ashford",
        to_id="carrow_vale",
        route=["brennmoor"],
        leg_progress=70,
        is_halted=False,
    )
    digest = world_hash(world)
    await world_state_repo.insert_world_state(
        db_connection,
        PLAYTHROUGH_ID,
        world.schema_version,
        world.clock.turn,
        digest,
        world.model_dump(mode="json"),
    )
    row = await world_state_repo.get_world_state(db_connection, PLAYTHROUGH_ID)
    assert row is not None
    reloaded = world_from_document(row.document)
    assert reloaded.armies["army_a"].march == world.armies["army_a"].march
    assert world_hash(reloaded) == digest
