from app.repositories import turn_hash_repo

from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough


async def test_insert_reports_duplicates(db_connection) -> None:
    await seed_playthrough(db_connection)
    first = await turn_hash_repo.insert_turn_hash(db_connection, PLAYTHROUGH_ID, 1, "a")
    second = await turn_hash_repo.insert_turn_hash(
        db_connection, PLAYTHROUGH_ID, 1, "b"
    )
    assert (first, second) == (True, False)


async def test_hashes_list_in_turn_order(db_connection) -> None:
    await seed_playthrough(db_connection)
    for turn in (3, 1, 2):
        await turn_hash_repo.insert_turn_hash(
            db_connection, PLAYTHROUGH_ID, turn, f"h{turn}"
        )
    rows = await turn_hash_repo.list_turn_hashes(db_connection, PLAYTHROUGH_ID)
    assert [(row.turn, row.world_hash) for row in rows] == [
        (1, "h1"),
        (2, "h2"),
        (3, "h3"),
    ]
