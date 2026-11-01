"""Repository for memory_event. SQL lives only here."""

from uuid import UUID

from app.models.evidence import EventCreate, EventRow
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

INSERT_EVENT_SQL = """
INSERT INTO memory_event (
    playthrough_id, sequence, turn_id, event_kind, event_key, is_accepted,
    payload, actor_participant_id
) VALUES (
    %(playthrough_id)s, %(sequence)s, %(turn_id)s, %(event_kind)s, %(event_key)s,
    %(is_accepted)s, %(payload)s, %(actor_participant_id)s
)
ON CONFLICT (turn_id, event_kind, event_key) DO NOTHING
"""

SELECT_EVENTS_BY_KEY_SQL = """
SELECT event.*
FROM unnest(%(turn_ids)s::uuid[], %(event_kinds)s::text[], %(event_keys)s::text[])
    WITH ORDINALITY AS requested (turn_id, event_kind, event_key, request_order)
JOIN memory_event AS event
    ON event.turn_id = requested.turn_id
    AND event.event_kind = requested.event_kind
    AND event.event_key = requested.event_key
ORDER BY requested.request_order
"""

SELECT_EVENTS_BY_SEQUENCE_SQL = """
SELECT * FROM memory_event
WHERE playthrough_id = %(playthrough_id)s
    AND sequence BETWEEN %(from_seq)s AND %(to_seq)s
ORDER BY sequence, event_id
"""


def _event_insert_params(events: list[EventCreate]) -> list[dict[str, object]]:
    rows = []
    for event in events:
        row = event.model_dump()
        row["payload"] = Jsonb(row["payload"])
        rows.append(row)
    return rows


def _event_key_params(events: list[EventCreate]) -> dict[str, list[object]]:
    return {
        "turn_ids": [event.turn_id for event in events],
        "event_kinds": [event.event_kind for event in events],
        "event_keys": [event.event_key for event in events],
    }


def _event_key(row: EventRow) -> tuple[UUID, str, str]:
    return row.turn_id, row.event_kind, row.event_key


async def create_events_with_status(
    connection: AsyncConnection, events: list[EventCreate]
) -> list[tuple[EventRow, bool]]:
    """Idempotent on (turn_id, event_kind, event_key); returns (row, is_inserted)
    in input order, where is_inserted is True only for rows this call created."""
    if not events:
        return []
    key_params = _event_key_params(events)
    async with connection.cursor(row_factory=class_row(EventRow)) as cursor:
        await cursor.execute(SELECT_EVENTS_BY_KEY_SQL, key_params)
        existing_keys = {_event_key(row) for row in await cursor.fetchall()}
        await cursor.executemany(INSERT_EVENT_SQL, _event_insert_params(events))
        await cursor.execute(SELECT_EVENTS_BY_KEY_SQL, key_params)
        rows = await cursor.fetchall()
    return [(row, _event_key(row) not in existing_keys) for row in rows]


async def create_events(
    connection: AsyncConnection, events: list[EventCreate]
) -> list[EventRow]:
    """Idempotent on (turn_id, event_kind, event_key); returns rows in input order."""
    rows_with_status = await create_events_with_status(connection, events)
    return [row for row, _is_inserted in rows_with_status]


async def list_events(
    connection: AsyncConnection, playthrough_id: UUID, from_seq: int, to_seq: int
) -> list[EventRow]:
    async with connection.cursor(row_factory=class_row(EventRow)) as cursor:
        await cursor.execute(
            SELECT_EVENTS_BY_SEQUENCE_SQL,
            {
                "playthrough_id": playthrough_id,
                "from_seq": from_seq,
                "to_seq": to_seq,
            },
        )
        return await cursor.fetchall()
