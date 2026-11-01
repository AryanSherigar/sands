"""Repository for memory_extraction_batch."""

from uuid import UUID

from app.models.common import ExtractionBatchStatus, ScopeKind
from app.models.jobs import ExtractionBatchCreate, ExtractionBatchRow
from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

CREATE_BATCH_SQL = """
INSERT INTO memory_extraction_batch (
    scope_kind, scope_id, from_seq, to_seq, status, model, prompt_version, input_hash
) VALUES (
    %(scope_kind)s, %(scope_id)s, %(from_seq)s, %(to_seq)s, %(status)s,
    %(model)s, %(prompt_version)s, %(input_hash)s
)
ON CONFLICT (scope_kind, scope_id, from_seq, to_seq, prompt_version, model) DO NOTHING
RETURNING *
"""

SELECT_BATCH_BY_KEY_SQL = """
SELECT * FROM memory_extraction_batch
WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s
    AND from_seq = %(from_seq)s AND to_seq = %(to_seq)s
    AND prompt_version = %(prompt_version)s AND model = %(model)s
"""

GET_BATCH_SQL = "SELECT * FROM memory_extraction_batch WHERE batch_id = %(batch_id)s"

LIST_BATCHES_SQL = """
SELECT * FROM memory_extraction_batch
WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s
"""

LIST_BATCHES_WITH_STATUSES_SQL = LIST_BATCHES_SQL + " AND status = ANY(%(statuses)s)"

HAS_FAILED_BATCH_SQL = """
SELECT EXISTS (
    SELECT 1 FROM memory_extraction_batch
    WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s
        AND status = 'failed'
)
"""

CLAIM_PENDING_BATCH_SQL = """
WITH next_batch AS (
    SELECT batch_id
    FROM memory_extraction_batch
    WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s AND status = 'pending'
    ORDER BY created_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
UPDATE memory_extraction_batch AS batch
SET status = 'running',
    lease_expires_at = now() + make_interval(secs => %(lease_seconds)s),
    attempt_count = batch.attempt_count + 1,
    updated_at = now()
FROM next_batch
WHERE batch.batch_id = next_batch.batch_id
RETURNING batch.*
"""

RECORD_BATCH_OUTPUT_SQL = """
UPDATE memory_extraction_batch
SET status = 'extracted', raw_output = %(raw_output)s, validated_plan = %(validated_plan)s,
    input_tokens = %(input_tokens)s, output_tokens = %(output_tokens)s, updated_at = now()
WHERE batch_id = %(batch_id)s AND status = 'running'
RETURNING *
"""

MARK_BATCH_APPLIED_SQL = """
UPDATE memory_extraction_batch
SET status = 'applied', updated_at = now()
WHERE batch_id = %(batch_id)s AND status = 'extracted'
RETURNING *
"""

MARK_BATCH_FAILED_TERMINAL_SQL = """
UPDATE memory_extraction_batch
SET status = 'failed', error = %(error)s, updated_at = now()
WHERE batch_id = %(batch_id)s AND status = 'running'
RETURNING *
"""

MARK_BATCH_FAILED_RETRY_SQL = """
UPDATE memory_extraction_batch
SET status = 'pending', error = %(error)s, lease_expires_at = NULL, updated_at = now()
WHERE batch_id = %(batch_id)s AND status = 'running'
RETURNING *
"""

RESET_FAILED_BATCHES_SQL = """
UPDATE memory_extraction_batch
SET status = 'pending', attempt_count = 0, error = NULL, lease_expires_at = NULL, updated_at = now()
WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s AND status = 'failed'
RETURNING *
"""

SET_INPUT_HASH_SQL = """
UPDATE memory_extraction_batch SET input_hash = %(input_hash)s, updated_at = now()
WHERE batch_id = %(batch_id)s
"""

RELEASE_BATCH_SQL = """
UPDATE memory_extraction_batch
SET status = 'pending', attempt_count = GREATEST(attempt_count - 1, 0),
    lease_expires_at = NULL, updated_at = now()
WHERE batch_id = %(batch_id)s AND status = 'running'
RETURNING *
"""

RELEASE_EXPIRED_LEASES_SQL = """
UPDATE memory_extraction_batch
SET status = 'pending', lease_expires_at = NULL, error = 'lease_expired',
    updated_at = now()
WHERE status = 'running' AND lease_expires_at < now()
RETURNING batch_id
"""

LIST_DUE_PENDING_BATCHES_SQL = """
SELECT * FROM memory_extraction_batch
WHERE (%(scope_id)s::uuid IS NULL OR scope_id = %(scope_id)s::uuid)
    AND (
        status = 'extracted'
        OR (
            status = 'pending'
            AND (
                attempt_count = 0
                OR updated_at <= now() - make_interval(
                    secs => (%(delay_seconds)s::int[])[
                        LEAST(attempt_count, cardinality(%(delay_seconds)s::int[]))
                    ]
                )
            )
        )
    )
ORDER BY created_at
"""

RECORD_APPLY_FAILURE_SQL = """
UPDATE memory_extraction_batch
SET attempt_count = attempt_count + 1,
    status = CASE WHEN attempt_count + 1 >= %(max_attempts)s THEN 'failed' ELSE 'extracted' END,
    error = 'apply_failed', updated_at = now()
WHERE batch_id = %(batch_id)s AND status IN ('extracted', 'pending')
RETURNING *
"""

MARK_BATCH_EXTRACTED_SQL = """
UPDATE memory_extraction_batch
SET status = 'extracted', error = NULL, updated_at = now()
WHERE batch_id = %(batch_id)s AND status = 'pending' AND validated_plan IS NOT NULL
RETURNING *
"""

MARK_BATCH_APPLIED_ANY_SQL = """
UPDATE memory_extraction_batch
SET status = 'applied', error = %(error)s, updated_at = now()
WHERE batch_id = %(batch_id)s AND status IN ('extracted', 'pending', 'running')
RETURNING *
"""


async def create_batch(
    connection: AsyncConnection, batch: ExtractionBatchCreate
) -> ExtractionBatchRow:
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(CREATE_BATCH_SQL, batch.model_dump())
        row = await cursor.fetchone()
        if row is not None:
            return row
        await cursor.execute(SELECT_BATCH_BY_KEY_SQL, batch.model_dump())
        existing = await cursor.fetchone()
    if existing is None:
        raise RuntimeError("Batch insert conflicted but no existing row was found.")
    return existing


async def get_batch(
    connection: AsyncConnection, batch_id: UUID
) -> ExtractionBatchRow | None:
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(GET_BATCH_SQL, {"batch_id": batch_id})
        return await cursor.fetchone()


async def list_batches(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    statuses: list[ExtractionBatchStatus] | None,
) -> list[ExtractionBatchRow]:
    params: dict[str, object] = {"scope_kind": scope_kind, "scope_id": scope_id}
    query = LIST_BATCHES_SQL
    if statuses is not None:
        query = LIST_BATCHES_WITH_STATUSES_SQL
        params["statuses"] = statuses
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(query, params)
        return await cursor.fetchall()


async def claim_pending_batch(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    lease_seconds: int,
) -> ExtractionBatchRow | None:
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(
            CLAIM_PENDING_BATCH_SQL,
            {
                "scope_kind": scope_kind,
                "scope_id": scope_id,
                "lease_seconds": lease_seconds,
            },
        )
        return await cursor.fetchone()


async def record_batch_output(
    connection: AsyncConnection,
    batch_id: UUID,
    raw_output: dict[str, object],
    validated_plan: dict[str, object],
    input_tokens: int,
    output_tokens: int,
) -> ExtractionBatchRow | None:
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(
            RECORD_BATCH_OUTPUT_SQL,
            {
                "batch_id": batch_id,
                "raw_output": Jsonb(raw_output),
                "validated_plan": Jsonb(validated_plan),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        )
        return await cursor.fetchone()


async def mark_batch_applied(
    connection: AsyncConnection, batch_id: UUID
) -> ExtractionBatchRow | None:
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(MARK_BATCH_APPLIED_SQL, {"batch_id": batch_id})
        return await cursor.fetchone()


async def mark_batch_failed(
    connection: AsyncConnection, batch_id: UUID, error: str, is_terminal: bool
) -> ExtractionBatchRow | None:
    query = (
        MARK_BATCH_FAILED_TERMINAL_SQL if is_terminal else MARK_BATCH_FAILED_RETRY_SQL
    )
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(query, {"batch_id": batch_id, "error": error})
        return await cursor.fetchone()


async def reset_failed_batches(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> list[ExtractionBatchRow]:
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(
            RESET_FAILED_BATCHES_SQL, {"scope_kind": scope_kind, "scope_id": scope_id}
        )
        return await cursor.fetchall()


async def has_failed_batch(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> bool:
    async with connection.cursor() as cursor:
        await cursor.execute(
            HAS_FAILED_BATCH_SQL, {"scope_kind": scope_kind, "scope_id": scope_id}
        )
        row = await cursor.fetchone()
    assert row is not None
    return bool(row[0])


async def set_input_hash(
    connection: AsyncConnection, batch_id: UUID, input_hash: str
) -> None:
    await connection.execute(
        SET_INPUT_HASH_SQL, {"batch_id": batch_id, "input_hash": input_hash}
    )


async def release_batch(
    connection: AsyncConnection, batch_id: UUID
) -> ExtractionBatchRow | None:
    """Back to pending without counting the attempt (rate limit, config abort)."""
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(RELEASE_BATCH_SQL, {"batch_id": batch_id})
        return await cursor.fetchone()


async def release_expired_leases(connection: AsyncConnection) -> int:
    async with connection.cursor() as cursor:
        await cursor.execute(RELEASE_EXPIRED_LEASES_SQL)
        return len(await cursor.fetchall())


async def list_due_pending_batches(
    connection: AsyncConnection, delay_seconds: list[int], scope_id: UUID | None
) -> list[ExtractionBatchRow]:
    """Pending batches whose backoff has elapsed, plus extracted batches awaiting apply."""
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(
            LIST_DUE_PENDING_BATCHES_SQL,
            {"delay_seconds": delay_seconds, "scope_id": scope_id},
        )
        return await cursor.fetchall()


async def record_apply_failure(
    connection: AsyncConnection, batch_id: UUID, max_attempts: int
) -> ExtractionBatchRow | None:
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(
            RECORD_APPLY_FAILURE_SQL,
            {"batch_id": batch_id, "max_attempts": max_attempts},
        )
        return await cursor.fetchone()


async def mark_batch_extracted(
    connection: AsyncConnection, batch_id: UUID
) -> ExtractionBatchRow | None:
    """Pending batch that already holds a validated plan (apply retry after a reset)."""
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(MARK_BATCH_EXTRACTED_SQL, {"batch_id": batch_id})
        return await cursor.fetchone()


async def mark_batch_applied_with_note(
    connection: AsyncConnection, batch_id: UUID, error: str | None
) -> ExtractionBatchRow | None:
    async with connection.cursor(row_factory=class_row(ExtractionBatchRow)) as cursor:
        await cursor.execute(
            MARK_BATCH_APPLIED_ANY_SQL, {"batch_id": batch_id, "error": error}
        )
        return await cursor.fetchone()


DELETE_SCOPE_BATCHES_SQL = (
    "DELETE FROM memory_extraction_batch "
    "WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s"
)


async def delete_scope_batches(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> int:
    async with connection.cursor() as cursor:
        await cursor.execute(
            DELETE_SCOPE_BATCHES_SQL, {"scope_kind": scope_kind, "scope_id": scope_id}
        )
        return cursor.rowcount
