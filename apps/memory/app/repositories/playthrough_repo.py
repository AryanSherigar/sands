"""Repository for memory_playthrough. SQL lives only here."""

from uuid import UUID

from app.models.purge import PlaythroughScope
from app.models.templates import (
    ParticipantPayload,
    PlaythroughCreate,
    PlaythroughRow,
)
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

INSERT_PLAYTHROUGH_SQL = """
INSERT INTO memory_playthrough (
    playthrough_id, template_id, player_entity_id, participants, tracked_fields
)
VALUES (
    %(playthrough_id)s, %(template_id)s, %(player_entity_id)s,
    %(participants)s, %(tracked_fields)s
)
ON CONFLICT (playthrough_id) DO NOTHING
RETURNING *
"""

SELECT_PLAYTHROUGH_BY_ID_SQL = (
    "SELECT * FROM memory_playthrough WHERE playthrough_id = %(playthrough_id)s"
)

ADVANCE_WATERMARKS_SQL = """
UPDATE memory_playthrough
SET ingested_seq = GREATEST(ingested_seq, COALESCE(%(ingested_seq)s, ingested_seq)),
    indexed_seq = GREATEST(indexed_seq, COALESCE(%(indexed_seq)s, indexed_seq)),
    extracted_seq = GREATEST(
        extracted_seq, COALESCE(%(extracted_seq)s, extracted_seq)
    ),
    latest_seq_seen = GREATEST(
        latest_seq_seen, COALESCE(%(latest_seq_seen)s, latest_seq_seen)
    )
WHERE playthrough_id = %(playthrough_id)s
RETURNING *
"""

SELECT_PARTICIPANTS_FOR_UPDATE_SQL = """
SELECT participants FROM memory_playthrough
WHERE playthrough_id = %(playthrough_id)s
FOR NO KEY UPDATE
"""

UPDATE_PARTICIPANTS_SQL = """
UPDATE memory_playthrough SET participants = %(participants)s
WHERE playthrough_id = %(playthrough_id)s
"""

SET_FLUSH_REQUESTED_SQL = """
UPDATE memory_playthrough
SET flush_requested_through_seq = GREATEST(
    COALESCE(flush_requested_through_seq, %(through_seq)s), %(through_seq)s
)
WHERE playthrough_id = %(playthrough_id)s
RETURNING *
"""

LIST_PLAYTHROUGHS_BEHIND_INDEX_SQL = """
SELECT * FROM memory_playthrough
WHERE indexed_seq < ingested_seq
    AND (%(playthrough_id)s::uuid IS NULL OR playthrough_id = %(playthrough_id)s::uuid)
ORDER BY created_at, playthrough_id
"""

LIST_PLAYTHROUGHS_DUE_FOR_EXTRACTION_SQL = """
SELECT * FROM memory_playthrough AS playthrough
WHERE ingested_seq > extracted_seq
    AND (%(playthrough_id)s::uuid IS NULL OR playthrough_id = %(playthrough_id)s::uuid)
    AND (
        ingested_seq - extracted_seq >= %(batch_turns)s
        OR COALESCE(flush_requested_through_seq, 0) > extracted_seq
    )
    AND NOT EXISTS (
        SELECT 1 FROM memory_extraction_batch AS batch
        WHERE batch.scope_kind = 'playthrough'
            AND batch.scope_id = playthrough.playthrough_id
            AND batch.status IN ('pending', 'running', 'extracted', 'failed')
    )
ORDER BY created_at, playthrough_id
"""


def _insert_params(playthrough: PlaythroughCreate) -> dict[str, object]:
    params: dict[str, object] = playthrough.model_dump(
        exclude={"participants", "tracked_fields"}
    )
    params["participants"] = Jsonb(playthrough.model_dump(mode="json")["participants"])
    params["tracked_fields"] = playthrough.tracked_fields
    return params


async def register_playthrough(
    connection: AsyncConnection, playthrough: PlaythroughCreate
) -> PlaythroughRow:
    """Idempotent on playthrough_id. template_id may be null (template_missing)."""
    async with connection.cursor(row_factory=class_row(PlaythroughRow)) as cursor:
        await cursor.execute(INSERT_PLAYTHROUGH_SQL, _insert_params(playthrough))
        inserted = await cursor.fetchone()
        if inserted is not None:
            return inserted
        await cursor.execute(
            SELECT_PLAYTHROUGH_BY_ID_SQL,
            {"playthrough_id": playthrough.playthrough_id},
        )
        existing = await cursor.fetchone()
    assert existing is not None
    return existing


async def get_playthrough(
    connection: AsyncConnection, playthrough_id: UUID
) -> PlaythroughRow | None:
    async with connection.cursor(row_factory=class_row(PlaythroughRow)) as cursor:
        await cursor.execute(
            SELECT_PLAYTHROUGH_BY_ID_SQL, {"playthrough_id": playthrough_id}
        )
        return await cursor.fetchone()


async def advance_watermarks(
    connection: AsyncConnection,
    playthrough_id: UUID,
    *,
    ingested_seq: int | None = None,
    indexed_seq: int | None = None,
    extracted_seq: int | None = None,
    latest_seq_seen: int | None = None,
) -> PlaythroughRow | None:
    """GREATEST against the current value, so a watermark never moves backwards."""
    async with connection.cursor(row_factory=class_row(PlaythroughRow)) as cursor:
        await cursor.execute(
            ADVANCE_WATERMARKS_SQL,
            {
                "playthrough_id": playthrough_id,
                "ingested_seq": ingested_seq,
                "indexed_seq": indexed_seq,
                "extracted_seq": extracted_seq,
                "latest_seq_seen": latest_seq_seen,
            },
        )
        return await cursor.fetchone()


async def get_participants_for_update(
    connection: AsyncConnection, playthrough_id: UUID
) -> list[ParticipantPayload] | None:
    """Locks the row for the rest of the transaction; None when unregistered."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            SELECT_PARTICIPANTS_FOR_UPDATE_SQL, {"playthrough_id": playthrough_id}
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    return [ParticipantPayload.model_validate(item) for item in row[0]]


async def set_participants(
    connection: AsyncConnection,
    playthrough_id: UUID,
    participants: list[ParticipantPayload],
) -> None:
    payload = [item.model_dump(mode="json") for item in participants]
    await connection.execute(
        UPDATE_PARTICIPANTS_SQL,
        {"playthrough_id": playthrough_id, "participants": Jsonb(payload)},
    )


async def set_flush_requested(
    connection: AsyncConnection, playthrough_id: UUID, through_seq: int
) -> PlaythroughRow | None:
    async with connection.cursor(row_factory=class_row(PlaythroughRow)) as cursor:
        await cursor.execute(
            SET_FLUSH_REQUESTED_SQL,
            {"playthrough_id": playthrough_id, "through_seq": through_seq},
        )
        return await cursor.fetchone()


async def list_playthroughs_behind_index(
    connection: AsyncConnection, playthrough_id: UUID | None = None
) -> list[PlaythroughRow]:
    async with connection.cursor(row_factory=class_row(PlaythroughRow)) as cursor:
        await cursor.execute(
            LIST_PLAYTHROUGHS_BEHIND_INDEX_SQL, {"playthrough_id": playthrough_id}
        )
        return await cursor.fetchall()


async def list_playthroughs_due_for_extraction(
    connection: AsyncConnection, batch_turns: int, playthrough_id: UUID | None
) -> list[PlaythroughRow]:
    async with connection.cursor(row_factory=class_row(PlaythroughRow)) as cursor:
        await cursor.execute(
            LIST_PLAYTHROUGHS_DUE_FOR_EXTRACTION_SQL,
            {"batch_turns": batch_turns, "playthrough_id": playthrough_id},
        )
        return await cursor.fetchall()


LOCK_PLAYTHROUGH_FOR_UPDATE_SQL = (
    "SELECT playthrough_id FROM memory_playthrough "
    "WHERE playthrough_id = %(playthrough_id)s FOR UPDATE"
)
LOCK_PLAYTHROUGH_FOR_SHARE_SQL = (
    "SELECT playthrough_id FROM memory_playthrough "
    "WHERE playthrough_id = %(playthrough_id)s FOR SHARE"
)
DELETE_PLAYTHROUGH_SQL = (
    "DELETE FROM memory_playthrough WHERE playthrough_id = %(playthrough_id)s"
)
COUNT_PLAYTHROUGHS_FOR_TEMPLATE_SQL = (
    "SELECT count(*) FROM memory_playthrough WHERE template_id = %(template_id)s"
)
LIST_PLAYTHROUGH_SCOPES_SQL = (
    "SELECT playthrough_id, created_at FROM memory_playthrough "
    "ORDER BY created_at, playthrough_id"
)


async def lock_playthrough_for_update(
    connection: AsyncConnection, playthrough_id: UUID
) -> bool:
    """Waits for any transaction holding the share lock (an in-flight extraction apply)."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            LOCK_PLAYTHROUGH_FOR_UPDATE_SQL, {"playthrough_id": playthrough_id}
        )
        return await cursor.fetchone() is not None


async def lock_playthrough_for_share(
    connection: AsyncConnection, playthrough_id: UUID
) -> bool:
    async with connection.cursor() as cursor:
        await cursor.execute(
            LOCK_PLAYTHROUGH_FOR_SHARE_SQL, {"playthrough_id": playthrough_id}
        )
        return await cursor.fetchone() is not None


async def delete_playthrough(connection: AsyncConnection, playthrough_id: UUID) -> bool:
    async with connection.cursor() as cursor:
        await cursor.execute(DELETE_PLAYTHROUGH_SQL, {"playthrough_id": playthrough_id})
        return cursor.rowcount > 0


async def count_playthroughs_for_template(
    connection: AsyncConnection, template_id: UUID
) -> int:
    async with connection.cursor() as cursor:
        await cursor.execute(
            COUNT_PLAYTHROUGHS_FOR_TEMPLATE_SQL, {"template_id": template_id}
        )
        row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def list_playthrough_scopes(
    connection: AsyncConnection,
) -> list[PlaythroughScope]:
    async with connection.cursor(row_factory=class_row(PlaythroughScope)) as cursor:
        await cursor.execute(LIST_PLAYTHROUGH_SCOPES_SQL)
        return await cursor.fetchall()
