"""Repository for event_log. SQL lives only here."""

from collections.abc import Sequence
from uuid import UUID

from app.models.world_events import EventLogEntry
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

EVENT_PAGE_LIMIT = 500

INSERT_EVENT_SQL = """
INSERT INTO event_log (
    playthrough_id, seq, turn, phase, kind, is_major, significance, cause, changes
)
VALUES (
    %(playthrough_id)s, %(seq)s, %(turn)s, %(phase)s, %(kind)s, %(is_major)s,
    %(significance)s, %(cause)s, %(changes)s
)
"""

SELECT_EVENTS_SQL = """
SELECT seq, turn, phase, kind, is_major, significance, cause, changes
FROM event_log
WHERE playthrough_id = %(playthrough_id)s
  AND seq > %(after_seq)s
  AND (%(turn)s::int IS NULL OR turn = %(turn)s::int)
ORDER BY seq
LIMIT %(limit)s
"""


def _event_parameters(playthrough_id: UUID, entry: EventLogEntry) -> dict[str, object]:
    return {
        "playthrough_id": playthrough_id,
        "seq": entry.seq,
        "turn": entry.turn,
        "phase": entry.phase.value,
        "kind": entry.kind,
        "is_major": entry.is_major,
        "significance": entry.significance,
        "cause": Jsonb(entry.cause.model_dump(mode="json")),
        "changes": Jsonb([change.model_dump(mode="json") for change in entry.changes]),
    }


async def append_events(
    connection: AsyncConnection,
    playthrough_id: UUID,
    entries: Sequence[EventLogEntry],
) -> int:
    if not entries:
        return 0
    async with connection.cursor() as cursor:
        await cursor.executemany(
            INSERT_EVENT_SQL,
            [_event_parameters(playthrough_id, entry) for entry in entries],
        )
    return len(entries)


async def list_events(
    connection: AsyncConnection,
    playthrough_id: UUID,
    *,
    after_seq: int = 0,
    turn: int | None = None,
    limit: int = EVENT_PAGE_LIMIT,
) -> list[EventLogEntry]:
    async with connection.cursor(row_factory=class_row(EventLogEntry)) as cursor:
        await cursor.execute(
            SELECT_EVENTS_SQL,
            {
                "playthrough_id": playthrough_id,
                "after_seq": after_seq,
                "turn": turn,
                "limit": limit,
            },
        )
        return await cursor.fetchall()
