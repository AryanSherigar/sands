"""Repository for world_snapshots. SQL lives only here."""

from uuid import UUID

from app.models.persistence import SnapshotRow
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

INSERT_SNAPSHOT_SQL = """
INSERT INTO world_snapshots (playthrough_id, turn, schema_version, world_hash, document)
VALUES (%(playthrough_id)s, %(turn)s, %(schema_version)s, %(world_hash)s, %(document)s)
ON CONFLICT (playthrough_id, turn) DO NOTHING
RETURNING turn
"""

SELECT_LATEST_SNAPSHOT_AT_OR_BEFORE_SQL = """
SELECT * FROM world_snapshots
WHERE playthrough_id = %(playthrough_id)s AND turn <= %(turn)s
ORDER BY turn DESC
LIMIT 1
"""
SELECT_SNAPSHOT_SQL = """
SELECT * FROM world_snapshots
WHERE playthrough_id = %(playthrough_id)s AND turn = %(turn)s
"""


async def insert_snapshot(
    connection: AsyncConnection,
    playthrough_id: UUID,
    turn: int,
    schema_version: int,
    world_hash: str,
    document: dict[str, object],
) -> bool:
    cursor = await connection.execute(
        INSERT_SNAPSHOT_SQL,
        {
            "playthrough_id": playthrough_id,
            "turn": turn,
            "schema_version": schema_version,
            "world_hash": world_hash,
            "document": Jsonb(document),
        },
    )
    return await cursor.fetchone() is not None


async def get_latest_snapshot_at_or_before(
    connection: AsyncConnection, playthrough_id: UUID, turn: int
) -> SnapshotRow | None:
    async with connection.cursor(row_factory=class_row(SnapshotRow)) as cursor:
        await cursor.execute(
            SELECT_LATEST_SNAPSHOT_AT_OR_BEFORE_SQL,
            {"playthrough_id": playthrough_id, "turn": turn},
        )
        return await cursor.fetchone()


async def get_snapshot(
    connection: AsyncConnection, playthrough_id: UUID, turn: int
) -> SnapshotRow | None:
    async with connection.cursor(row_factory=class_row(SnapshotRow)) as cursor:
        await cursor.execute(
            SELECT_SNAPSHOT_SQL, {"playthrough_id": playthrough_id, "turn": turn}
        )
        return await cursor.fetchone()
