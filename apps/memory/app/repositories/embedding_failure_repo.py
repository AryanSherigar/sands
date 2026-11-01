"""Repository for memory_embedding_failure (polymorphic, no FK to spans or facts)."""

from uuid import UUID

from app.models.common import EmbeddingTargetKind, ScopeKind
from app.models.jobs import EmbeddingFailureRow
from psycopg import AsyncConnection
from psycopg.rows import class_row

RECORD_FAILURES_SQL = """
INSERT INTO memory_embedding_failure (
    target_kind, target_id, model, model_version, attempt_count, last_error
)
SELECT %(target_kind)s, target_id, %(model)s, %(model_version)s, 1, %(error_code)s
FROM unnest(%(target_ids)s::uuid[]) AS target_id
GROUP BY target_id
ON CONFLICT (target_kind, target_id, model, model_version) DO UPDATE
SET attempt_count = memory_embedding_failure.attempt_count + 1,
    last_error = EXCLUDED.last_error,
    updated_at = now()
RETURNING *
"""

SELECT_FAILURE_COUNTS_SQL = """
SELECT target_id, attempt_count
FROM memory_embedding_failure
WHERE target_kind = %(target_kind)s
    AND target_id = ANY(%(target_ids)s::uuid[])
    AND model = %(model)s
    AND model_version = %(model_version)s
"""

RESET_PLAYTHROUGH_FAILURES_SQL = """
WITH deleted_spans AS (
    DELETE FROM memory_embedding_failure AS failure
    USING memory_span AS span
    WHERE failure.target_kind = 'span' AND failure.target_id = span.span_id
        AND span.scope_kind = 'playthrough' AND span.scope_id = %(playthrough_id)s
    RETURNING 1
), deleted_facts AS (
    DELETE FROM memory_embedding_failure AS failure
    USING memory_fact AS fact
    WHERE failure.target_kind = 'fact' AND failure.target_id = fact.fact_id
        AND fact.scope_kind = 'playthrough' AND fact.scope_id = %(playthrough_id)s
    RETURNING 1
)
SELECT (SELECT count(*) FROM deleted_spans) + (SELECT count(*) FROM deleted_facts)
"""


async def record_failures(
    connection: AsyncConnection,
    target_kind: EmbeddingTargetKind,
    target_ids: list[UUID],
    model: str,
    model_version: str,
    error_code: str,
) -> list[EmbeddingFailureRow]:
    if not target_ids:
        return []
    async with connection.cursor(row_factory=class_row(EmbeddingFailureRow)) as cursor:
        await cursor.execute(
            RECORD_FAILURES_SQL,
            {
                "target_kind": target_kind,
                "target_ids": target_ids,
                "model": model,
                "model_version": model_version,
                "error_code": error_code,
            },
        )
        return await cursor.fetchall()


async def get_failure_counts(
    connection: AsyncConnection,
    target_kind: EmbeddingTargetKind,
    target_ids: list[UUID],
    model: str,
    model_version: str,
) -> dict[UUID, int]:
    if not target_ids:
        return {}
    async with connection.cursor() as cursor:
        await cursor.execute(
            SELECT_FAILURE_COUNTS_SQL,
            {
                "target_kind": target_kind,
                "target_ids": target_ids,
                "model": model,
                "model_version": model_version,
            },
        )
        rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}


async def reset_playthrough_failures(
    connection: AsyncConnection, playthrough_id: UUID
) -> int:
    """Lets targets that were skipped as poison be embedded again ("Retry memory")."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            RESET_PLAYTHROUGH_FAILURES_SQL, {"playthrough_id": playthrough_id}
        )
        row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


DELETE_SCOPE_FAILURES_SQL = """
DELETE FROM memory_embedding_failure AS failure
WHERE (failure.target_kind = 'span' AND failure.target_id IN (
        SELECT span_id FROM memory_span
        WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s))
    OR (failure.target_kind = 'fact' AND failure.target_id IN (
        SELECT fact_id FROM memory_fact
        WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s))
"""


async def delete_scope_failures(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> int:
    """Must run before the scope's spans and facts are deleted: the join is the only
    link from a failure row to its scope."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            DELETE_SCOPE_FAILURES_SQL,
            {"scope_kind": scope_kind, "scope_id": scope_id},
        )
        return cursor.rowcount
