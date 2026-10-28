"""Repository for world_state. SQL lives only here."""

from uuid import UUID

from app.models.persistence import WorldStateRow
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

INSERT_WORLD_STATE_SQL = """
INSERT INTO world_state (playthrough_id, schema_version, turn, world_hash, document)
VALUES (%(playthrough_id)s, %(schema_version)s, %(turn)s, %(world_hash)s, %(document)s)
ON CONFLICT (playthrough_id) DO NOTHING
RETURNING playthrough_id
"""

SELECT_WORLD_STATE_SQL = (
    "SELECT * FROM world_state WHERE playthrough_id = %(playthrough_id)s"
)
SELECT_WORLD_STATE_FOR_UPDATE_SQL = SELECT_WORLD_STATE_SQL + " FOR UPDATE"

UPDATE_WORLD_STATE_SQL = """
UPDATE world_state
SET row_version = row_version + 1,
    schema_version = %(schema_version)s,
    turn = %(turn)s,
    world_hash = %(world_hash)s,
    document = %(document)s,
    updated_at = now()
WHERE playthrough_id = %(playthrough_id)s AND row_version = %(expected_row_version)s
RETURNING row_version
"""


async def insert_world_state(
    connection: AsyncConnection,
    playthrough_id: UUID,
    schema_version: int,
    turn: int,
    world_hash: str,
    document: dict[str, object],
) -> bool:
    cursor = await connection.execute(
        INSERT_WORLD_STATE_SQL,
        {
            "playthrough_id": playthrough_id,
            "schema_version": schema_version,
            "turn": turn,
            "world_hash": world_hash,
            "document": Jsonb(document),
        },
    )
    return await cursor.fetchone() is not None


async def get_world_state(
    connection: AsyncConnection, playthrough_id: UUID, *, should_lock: bool = False
) -> WorldStateRow | None:
    query = SELECT_WORLD_STATE_FOR_UPDATE_SQL if should_lock else SELECT_WORLD_STATE_SQL
    async with connection.cursor(row_factory=class_row(WorldStateRow)) as cursor:
        await cursor.execute(query, {"playthrough_id": playthrough_id})
        return await cursor.fetchone()


async def update_world_state(
    connection: AsyncConnection,
    playthrough_id: UUID,
    expected_row_version: int,
    schema_version: int,
    turn: int,
    world_hash: str,
    document: dict[str, object],
) -> int | None:
    cursor = await connection.execute(
        UPDATE_WORLD_STATE_SQL,
        {
            "playthrough_id": playthrough_id,
            "expected_row_version": expected_row_version,
            "schema_version": schema_version,
            "turn": turn,
            "world_hash": world_hash,
            "document": Jsonb(document),
        },
    )
    row = await cursor.fetchone()
    return None if row is None else row[0]
