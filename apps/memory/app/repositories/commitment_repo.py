"""Repository for memory_commitment and memory_commitment_status (child table)."""

from uuid import UUID

from app.models.eligibility import EligibilityContext
from app.models.facts import (
    CommitmentCreate,
    CommitmentRow,
    CommitmentStatusCreate,
    CommitmentStatusRow,
)
from app.repositories.eligibility_predicates import COMMITMENT_ELIGIBLE
from psycopg import AsyncConnection
from psycopg.rows import class_row, dict_row

CREATE_COMMITMENT_SQL = """
INSERT INTO memory_commitment (
    playthrough_id, kind, owner_entity_id, counterparty_entity_id,
    summary, opened_seq, opening_span_id, extraction_batch_id
) VALUES (
    %(playthrough_id)s, %(kind)s, %(owner_entity_id)s, %(counterparty_entity_id)s,
    %(summary)s, %(opened_seq)s, %(opening_span_id)s, %(extraction_batch_id)s
)
RETURNING *
"""

APPEND_COMMITMENT_STATUS_SQL = """
INSERT INTO memory_commitment_status (
    commitment_id, at_seq, status, evidence_span_id, event_id, extraction_batch_id
) VALUES (
    %(commitment_id)s, %(at_seq)s, %(status)s, %(evidence_span_id)s,
    %(event_id)s, %(extraction_batch_id)s
)
ON CONFLICT (commitment_id, at_seq) DO NOTHING
RETURNING *
"""

SELECT_COMMITMENT_STATUS_SQL = """
SELECT * FROM memory_commitment_status
WHERE commitment_id = %(commitment_id)s AND at_seq = %(at_seq)s
"""

_COMMITMENT_STATUS_COLUMNS_TEMPLATE = """
    {commitment}.commitment_id AS c_commitment_id,
    {commitment}.playthrough_id AS c_playthrough_id,
    {commitment}.kind AS c_kind,
    {commitment}.owner_entity_id AS c_owner_entity_id,
    {commitment}.counterparty_entity_id AS c_counterparty_entity_id,
    {commitment}.summary AS c_summary,
    {commitment}.opened_seq AS c_opened_seq,
    {commitment}.opening_span_id AS c_opening_span_id,
    {commitment}.extraction_batch_id AS c_extraction_batch_id,
    {status}.commitment_id AS s_commitment_id,
    {status}.at_seq AS s_at_seq,
    {status}.status AS s_status,
    {status}.evidence_span_id AS s_evidence_span_id,
    {status}.event_id AS s_event_id,
    {status}.extraction_batch_id AS s_extraction_batch_id
"""

LIST_COMMITMENTS_AT_SQL = (
    "SELECT"
    + _COMMITMENT_STATUS_COLUMNS_TEMPLATE.format(commitment="c", status="status")
    + """
FROM memory_commitment AS c
LEFT JOIN LATERAL (
    SELECT *
    FROM memory_commitment_status AS s
    WHERE s.commitment_id = c.commitment_id AND s.at_seq <= %(at_seq)s
    ORDER BY s.at_seq DESC
    LIMIT 1
) AS status ON true
WHERE c.playthrough_id = %(playthrough_id)s AND c.opened_seq <= %(at_seq)s
ORDER BY c.opened_seq
"""
)

LIST_ELIGIBLE_COMMITMENTS_SQL = (
    "SELECT"
    + _COMMITMENT_STATUS_COLUMNS_TEMPLATE.format(
        commitment="commitment", status="latest_status"
    )
    + f"""
FROM memory_commitment AS commitment
LEFT JOIN LATERAL (
    SELECT *
    FROM memory_commitment_status AS status_row
    WHERE status_row.commitment_id = commitment.commitment_id
        AND status_row.at_seq <= %(at_seq)s::integer
    ORDER BY status_row.at_seq DESC
    LIMIT 1
) AS latest_status ON true
WHERE {COMMITMENT_ELIGIBLE}
    AND (
        commitment.owner_entity_id = ANY(%(entity_ids)s::uuid[])
        OR commitment.counterparty_entity_id = ANY(%(entity_ids)s::uuid[])
    )
ORDER BY GREATEST(
        commitment.opened_seq, COALESCE(latest_status.at_seq, commitment.opened_seq)
    ) DESC,
    commitment.commitment_id DESC
LIMIT %(limit)s
"""
)


async def create_commitment(
    connection: AsyncConnection, commitment: CommitmentCreate
) -> CommitmentRow:
    async with connection.cursor(row_factory=class_row(CommitmentRow)) as cursor:
        await cursor.execute(CREATE_COMMITMENT_SQL, commitment.model_dump())
        row = await cursor.fetchone()
    if row is None:
        raise RuntimeError("Commitment insert did not return a row.")
    return row


async def append_commitment_status(
    connection: AsyncConnection, status: CommitmentStatusCreate
) -> CommitmentStatusRow:
    async with connection.cursor(row_factory=class_row(CommitmentStatusRow)) as cursor:
        await cursor.execute(APPEND_COMMITMENT_STATUS_SQL, status.model_dump())
        row = await cursor.fetchone()
        if row is not None:
            return row
        await cursor.execute(
            SELECT_COMMITMENT_STATUS_SQL,
            {"commitment_id": status.commitment_id, "at_seq": status.at_seq},
        )
        existing = await cursor.fetchone()
    if existing is None:
        raise RuntimeError(
            "Commitment status insert conflicted but no existing row was found."
        )
    return existing


def _build_commitment(row: dict[str, object]) -> CommitmentRow:
    return CommitmentRow(
        commitment_id=row["c_commitment_id"],
        playthrough_id=row["c_playthrough_id"],
        kind=row["c_kind"],
        owner_entity_id=row["c_owner_entity_id"],
        counterparty_entity_id=row["c_counterparty_entity_id"],
        summary=row["c_summary"],
        opened_seq=row["c_opened_seq"],
        opening_span_id=row["c_opening_span_id"],
        extraction_batch_id=row["c_extraction_batch_id"],
    )


def _build_commitment_status(row: dict[str, object]) -> CommitmentStatusRow | None:
    if row["s_commitment_id"] is None:
        return None
    return CommitmentStatusRow(
        commitment_id=row["s_commitment_id"],
        at_seq=row["s_at_seq"],
        status=row["s_status"],
        evidence_span_id=row["s_evidence_span_id"],
        event_id=row["s_event_id"],
        extraction_batch_id=row["s_extraction_batch_id"],
    )


async def list_commitments_at(
    connection: AsyncConnection, playthrough_id: UUID, at_seq: int
) -> list[tuple[CommitmentRow, CommitmentStatusRow | None]]:
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            LIST_COMMITMENTS_AT_SQL,
            {"playthrough_id": playthrough_id, "at_seq": at_seq},
        )
        rows = await cursor.fetchall()
    return [(_build_commitment(row), _build_commitment_status(row)) for row in rows]


async def list_eligible_commitments(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    seed_entity_ids: list[UUID],
    *,
    recent_resolution_turns: int,
    limit: int,
) -> list[tuple[CommitmentRow, CommitmentStatusRow | None]]:
    """Commitments of this playthrough opened by `ctx.at_seq` whose owner or
    counterparty is a seed and whose latest status at `ctx.at_seq` is open (or absent)
    or was resolved within `recent_resolution_turns`. Most recently active first."""
    if not seed_entity_ids or limit <= 0:
        return []
    params = {
        **ctx.to_params(),
        "entity_ids": seed_entity_ids,
        "commitment_recent_resolution_turns": recent_resolution_turns,
        "limit": limit,
    }
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(LIST_ELIGIBLE_COMMITMENTS_SQL, params)
        rows = await cursor.fetchall()
    return [(_build_commitment(row), _build_commitment_status(row)) for row in rows]
