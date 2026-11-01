"""Serialize ingestion and remember immutable relay deliveries."""

from uuid import UUID

from psycopg import AsyncConnection

LOCK_PLAYTHROUGH = "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))"
SELECT_DELIVERY = (
    "SELECT payload_hash FROM memory_ingest_delivery "
    "WHERE playthrough_id = %s AND delivery_id = %s"
)
INSERT_DELIVERY = (
    "INSERT INTO memory_ingest_delivery (playthrough_id, delivery_id, payload_hash) "
    "VALUES (%s, %s, %s)"
)


async def lock_ingestion(connection: AsyncConnection, playthrough_id: UUID) -> None:
    await connection.execute(LOCK_PLAYTHROUGH, (f"ingest:{playthrough_id}",))


async def get_payload_hash(
    connection: AsyncConnection, playthrough_id: UUID, delivery_id: UUID
) -> str | None:
    cursor = await connection.execute(SELECT_DELIVERY, (playthrough_id, delivery_id))
    row = await cursor.fetchone()
    return row[0] if row is not None else None


async def record_delivery(
    connection: AsyncConnection,
    playthrough_id: UUID,
    delivery_id: UUID,
    payload_hash: str,
) -> None:
    await connection.execute(
        INSERT_DELIVERY, (playthrough_id, delivery_id, payload_hash)
    )


async def is_purged(connection: AsyncConnection, playthrough_id: UUID) -> bool:
    cursor = await connection.execute(
        "SELECT 1 FROM memory_purged_playthrough WHERE playthrough_id = %s",
        (playthrough_id,),
    )
    return await cursor.fetchone() is not None


async def mark_purged(connection: AsyncConnection, playthrough_id: UUID) -> None:
    await connection.execute(
        "INSERT INTO memory_purged_playthrough (playthrough_id) VALUES (%s) "
        "ON CONFLICT (playthrough_id) DO NOTHING",
        (playthrough_id,),
    )
