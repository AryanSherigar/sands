from app.repositories import world_snapshot_repo

from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough

SCHEMA_VERSION = 1


async def _insert(connection, turn: int, document: dict[str, object] | None = None):
    return await world_snapshot_repo.insert_snapshot(
        connection,
        PLAYTHROUGH_ID,
        turn,
        SCHEMA_VERSION,
        f"hash{turn}",
        document if document is not None else {"turn": turn},
    )


async def test_latest_snapshot_at_or_before_a_turn(db_connection) -> None:
    await seed_playthrough(db_connection)
    for turn in (0, 5, 10):
        await _insert(db_connection, turn)
    latest = world_snapshot_repo.get_latest_snapshot_at_or_before
    assert (await latest(db_connection, PLAYTHROUGH_ID, 7)).turn == 5
    assert (await latest(db_connection, PLAYTHROUGH_ID, 0)).turn == 0
    assert (await latest(db_connection, PLAYTHROUGH_ID, 99)).turn == 10


async def test_no_snapshot_before_the_first_is_none(db_connection) -> None:
    await seed_playthrough(db_connection)
    await _insert(db_connection, 5)
    result = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, PLAYTHROUGH_ID, 4
    )
    assert result is None


async def test_second_insert_keeps_the_first_document(db_connection) -> None:
    await seed_playthrough(db_connection)
    assert await _insert(db_connection, 5, {"v": 1}) is True
    assert await _insert(db_connection, 5, {"v": 2}) is False
    row = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, PLAYTHROUGH_ID, 5
    )
    assert row.document == {"v": 1}
