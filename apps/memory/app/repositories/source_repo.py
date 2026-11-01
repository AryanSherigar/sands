"""Repository for memory_source. SQL lives only here."""

from uuid import UUID

from app.models.common import ScopeKind, SourceKind
from app.models.evidence import SourceCreate, SourceRow
from psycopg import AsyncConnection
from psycopg.rows import class_row

INSERT_SOURCE_SQL = """
INSERT INTO memory_source
    (scope_kind, scope_id, source_kind, source_ref, sequence,
     actor_participant_id, content, content_hash)
VALUES
    (%(scope_kind)s, %(scope_id)s, %(source_kind)s, %(source_ref)s, %(sequence)s,
     %(actor_participant_id)s, %(content)s, %(content_hash)s)
ON CONFLICT (scope_kind, scope_id, source_kind, source_ref) DO NOTHING
RETURNING *
"""

SELECT_SOURCE_BY_REF_SQL = """
SELECT * FROM memory_source
WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s
    AND source_kind = %(source_kind)s AND source_ref = %(source_ref)s
"""

SELECT_SOURCES_BY_SEQUENCE_SQL = """
SELECT * FROM memory_source
WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s
    AND sequence BETWEEN %(from_seq)s AND %(to_seq)s
ORDER BY sequence, source_id
"""

GET_CONTIGUOUS_SEQUENCE_SQL = """
WITH distinct_sequences AS (
    SELECT DISTINCT sequence FROM memory_source
    WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s
        AND source_kind = %(source_kind)s AND sequence >= %(start_seq)s
),
numbered AS (
    SELECT sequence, sequence - ROW_NUMBER() OVER (ORDER BY sequence) AS island
    FROM distinct_sequences
)
SELECT max(sequence) FROM numbered
WHERE island = (SELECT island FROM numbered WHERE sequence = %(start_seq)s)
"""


async def create_source_with_status(
    connection: AsyncConnection, source: SourceCreate
) -> tuple[SourceRow, bool]:
    """Idempotent on (scope_kind, scope_id, source_kind, source_ref); the bool is
    True only when this call inserted the row."""
    async with connection.cursor(row_factory=class_row(SourceRow)) as cursor:
        await cursor.execute(INSERT_SOURCE_SQL, source.model_dump())
        inserted = await cursor.fetchone()
        if inserted is not None:
            return inserted, True
        await cursor.execute(
            SELECT_SOURCE_BY_REF_SQL,
            {
                "scope_kind": source.scope_kind,
                "scope_id": source.scope_id,
                "source_kind": source.source_kind,
                "source_ref": source.source_ref,
            },
        )
        existing = await cursor.fetchone()
    assert existing is not None
    return existing, False


async def get_source_by_ref(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    source_kind: SourceKind,
    source_ref: str,
) -> SourceRow | None:
    async with connection.cursor(row_factory=class_row(SourceRow)) as cursor:
        await cursor.execute(
            SELECT_SOURCE_BY_REF_SQL,
            {
                "scope_kind": scope_kind,
                "scope_id": scope_id,
                "source_kind": source_kind,
                "source_ref": source_ref,
            },
        )
        return await cursor.fetchone()


async def create_source(connection: AsyncConnection, source: SourceCreate) -> SourceRow:
    """Idempotent on (scope_kind, scope_id, source_kind, source_ref)."""
    row, _is_inserted = await create_source_with_status(connection, source)
    return row


async def get_contiguous_sequence(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    source_kind: SourceKind,
    start_seq: int = 1,
) -> int:
    """Highest N such that every sequence in [start_seq, N] has at least one
    source of `source_kind` in this scope; start_seq - 1 if start_seq is missing."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            GET_CONTIGUOUS_SEQUENCE_SQL,
            {
                "scope_kind": scope_kind,
                "scope_id": scope_id,
                "source_kind": source_kind,
                "start_seq": start_seq,
            },
        )
        row = await cursor.fetchone()
    highest = row[0] if row is not None else None
    return highest if highest is not None else start_seq - 1


async def list_sources(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    from_seq: int,
    to_seq: int,
) -> list[SourceRow]:
    async with connection.cursor(row_factory=class_row(SourceRow)) as cursor:
        await cursor.execute(
            SELECT_SOURCES_BY_SEQUENCE_SQL,
            {
                "scope_kind": scope_kind,
                "scope_id": scope_id,
                "from_seq": from_seq,
                "to_seq": to_seq,
            },
        )
        return await cursor.fetchall()


DELETE_SCOPE_SOURCES_SQL = (
    "DELETE FROM memory_source "
    "WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s"
)


async def delete_scope_sources(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> int:
    """Cascades to the scope's spans and their fact links."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            DELETE_SCOPE_SOURCES_SQL, {"scope_kind": scope_kind, "scope_id": scope_id}
        )
        return cursor.rowcount
