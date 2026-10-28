"""Repository for turn_hashes. SQL lives only here."""

from uuid import UUID

from app.models.persistence import TurnHashRow
from psycopg import AsyncConnection
from psycopg.rows import class_row

INSERT_TURN_HASH_SQL = """
INSERT INTO turn_hashes (playthrough_id, turn, world_hash)
VALUES (%(playthrough_id)s, %(turn)s, %(world_hash)s)
ON CONFLICT (playthrough_id, turn) DO NOTHING
RETURNING turn
"""

SELECT_TURN_HASHES_SQL = (
    "SELECT * FROM turn_hashes WHERE playthrough_id = %(playthrough_id)s ORDER BY turn"
)


async def insert_turn_hash(
    connection: AsyncConnection, playthrough_id: UUID, turn: int, world_hash: str
) -> bool:
    cursor = await connection.execute(
        INSERT_TURN_HASH_SQL,
        {"playthrough_id": playthrough_id, "turn": turn, "world_hash": world_hash},
    )
    return await cursor.fetchone() is not None


async def list_turn_hashes(
    connection: AsyncConnection, playthrough_id: UUID
) -> list[TurnHashRow]:
    async with connection.cursor(row_factory=class_row(TurnHashRow)) as cursor:
        await cursor.execute(SELECT_TURN_HASHES_SQL, {"playthrough_id": playthrough_id})
        return await cursor.fetchall()
