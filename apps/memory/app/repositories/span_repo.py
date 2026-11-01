"""Repository for memory_span. SQL lives only here."""

from uuid import UUID

from app.models.common import ScopeKind
from app.models.eligibility import EligibilityContext
from app.models.evidence import SpanCreate, SpanRow
from app.models.retrieval_rows import SpanOrigin
from app.repositories.eligibility_predicates import SPAN_ELIGIBLE
from psycopg import AsyncConnection
from psycopg.rows import class_row, dict_row

INSERT_SPAN_SQL = """
INSERT INTO memory_span (
    source_id, scope_kind, scope_id, sequence, ordinal, start_offset, end_offset,
    text, token_count, label, entity_ids, is_hidden, authored_fact_id, conditional
) VALUES (
    %(source_id)s, %(scope_kind)s, %(scope_id)s, %(sequence)s, %(ordinal)s,
    %(start_offset)s, %(end_offset)s, %(text)s, %(token_count)s, %(label)s,
    %(entity_ids)s, %(is_hidden)s, %(authored_fact_id)s, %(conditional)s
)
ON CONFLICT (source_id, ordinal) DO NOTHING
"""

SELECT_SPANS_BY_SOURCE_ORDINAL_SQL = """
SELECT span.*
FROM unnest(%(source_ids)s::uuid[], %(ordinals)s::int[])
    WITH ORDINALITY AS requested (source_id, ordinal, request_order)
JOIN memory_span AS span
    ON span.source_id = requested.source_id AND span.ordinal = requested.ordinal
ORDER BY requested.request_order
"""

SELECT_SPANS_BY_SEQUENCE_SQL = """
SELECT * FROM memory_span
WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s
    AND sequence BETWEEN %(from_seq)s AND %(to_seq)s
ORDER BY sequence, ordinal
"""

SELECT_SPANS_BY_LABELS_SQL = """
SELECT * FROM memory_span
WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s
    AND label = ANY(%(labels)s)
ORDER BY sequence, ordinal
"""

SELECT_TEMPLATE_SPANS_IN_ORDER_SQL = """
SELECT span.*
FROM memory_span AS span
JOIN memory_source AS source ON source.source_id = span.source_id
WHERE span.scope_kind = 'template' AND span.scope_id = %(template_id)s
ORDER BY source.created_at, source.source_id, span.ordinal
"""

# NOTE: with a scope predicate present, planning falls back to a seq scan and the
# bm25 operator scores non-matching rows 0.0 instead of excluding them, so the
# score threshold below is what gates the result to actual matches, not the
# WHERE-less index-scan behaviour alone.
SEARCH_SPANS_BM25_SQL_TEMPLATE = """
SELECT *, text <@> to_bm25query(%s, 'memory_span_text_bm25_idx') AS bm25_score
FROM memory_span
WHERE (scope_kind, scope_id) IN ({scope_values})
    AND text <@> to_bm25query(%s, 'memory_span_text_bm25_idx') < 0
ORDER BY bm25_score
LIMIT %s
"""

LIST_EXACT_SPANS_SQL = f"""
SELECT span.* FROM memory_span AS span
WHERE {SPAN_ELIGIBLE}
    AND span.entity_ids && %(entity_ids)s::uuid[]
ORDER BY span.sequence DESC, span.span_id DESC
LIMIT %(limit)s
"""

# NOTE: the `< 0` gate stays in WHERE next to the eligibility fragments. Measured on
# pg_textsearch 1.4.0: the bm25 index scan keeps pulling candidates past filtered-out
# rows, so eligible matches still fill LIMIT. ORDER BY has no tiebreaker on purpose:
# a second sort key would stop the planner using the index order.
SEARCH_ELIGIBLE_SPANS_BM25_SQL = f"""
SELECT span.*,
    span.text <@> to_bm25query(%(query_text)s, 'memory_span_text_bm25_idx') AS bm25_score
FROM memory_span AS span
WHERE {SPAN_ELIGIBLE}
    AND span.text <@> to_bm25query(%(query_text)s, 'memory_span_text_bm25_idx') < 0
ORDER BY bm25_score
LIMIT %(limit)s
"""

GET_ELIGIBLE_SPANS_BY_IDS_SQL = f"""
SELECT span.* FROM memory_span AS span
WHERE span.span_id = ANY(%(span_ids)s::uuid[])
    AND {SPAN_ELIGIBLE}
ORDER BY span.sequence DESC, span.span_id DESC
"""

GET_SPAN_ORIGINS_SQL = f"""
SELECT span.span_id, origin.source_kind, origin.actor_participant_id
FROM memory_span AS span
JOIN memory_source AS origin ON origin.source_id = span.source_id
WHERE span.span_id = ANY(%(span_ids)s::uuid[])
    AND {SPAN_ELIGIBLE}
"""

FIRST_UNEMBEDDED_SEQUENCE_SQL = """
SELECT MIN(s.sequence)
FROM memory_span AS s
WHERE s.scope_kind = 'playthrough' AND s.scope_id = %(playthrough_id)s
    AND NOT EXISTS (
        SELECT 1 FROM memory_embedding AS e
        WHERE e.target_kind = 'span' AND e.target_id = s.span_id
            AND e.model = %(model)s AND e.model_version = %(model_version)s
    )
    AND NOT EXISTS (
        SELECT 1 FROM memory_embedding_failure AS f
        WHERE f.target_kind = 'span' AND f.target_id = s.span_id
            AND f.model = %(model)s AND f.model_version = %(model_version)s
            AND f.attempt_count >= %(failure_limit)s
    )
"""


def _span_key_params(spans: list[SpanCreate]) -> dict[str, list[object]]:
    return {
        "source_ids": [span.source_id for span in spans],
        "ordinals": [span.ordinal for span in spans],
    }


async def create_spans(
    connection: AsyncConnection, spans: list[SpanCreate]
) -> list[SpanRow]:
    """Idempotent on (source_id, ordinal); returns rows in input order."""
    if not spans:
        return []
    params = [span.model_dump() for span in spans]
    async with connection.cursor(row_factory=class_row(SpanRow)) as cursor:
        await cursor.executemany(INSERT_SPAN_SQL, params)
        await cursor.execute(
            SELECT_SPANS_BY_SOURCE_ORDINAL_SQL, _span_key_params(spans)
        )
        return await cursor.fetchall()


async def list_spans_by_sequence(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    from_seq: int,
    to_seq: int,
) -> list[SpanRow]:
    async with connection.cursor(row_factory=class_row(SpanRow)) as cursor:
        await cursor.execute(
            SELECT_SPANS_BY_SEQUENCE_SQL,
            {
                "scope_kind": scope_kind,
                "scope_id": scope_id,
                "from_seq": from_seq,
                "to_seq": to_seq,
            },
        )
        return await cursor.fetchall()


async def list_spans_by_labels(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    labels: list[str],
) -> list[SpanRow]:
    async with connection.cursor(row_factory=class_row(SpanRow)) as cursor:
        await cursor.execute(
            SELECT_SPANS_BY_LABELS_SQL,
            {"scope_kind": scope_kind, "scope_id": scope_id, "labels": labels},
        )
        return await cursor.fetchall()


def _bm25_search_params(
    scopes: list[tuple[ScopeKind, UUID]], query_text: str, limit: int
) -> list[object]:
    params: list[object] = [query_text]
    for scope_kind, scope_id in scopes:
        params.extend([scope_kind, scope_id])
    params.extend([query_text, limit])
    return params


async def search_spans_bm25(
    connection: AsyncConnection,
    scopes: list[tuple[ScopeKind, UUID]],
    query_text: str,
    limit: int,
) -> list[tuple[SpanRow, float]]:
    """Gating BM25 check: scoped and ranked best-first (score ascending, lower is
    better); a non-matching query returns nothing."""
    if not scopes:
        return []
    scope_values = ", ".join("(%s, %s)" for _ in scopes)
    sql_text = SEARCH_SPANS_BM25_SQL_TEMPLATE.format(scope_values=scope_values)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(sql_text, _bm25_search_params(scopes, query_text, limit))
        rows = await cursor.fetchall()
    results: list[tuple[SpanRow, float]] = []
    for row in rows:
        score = row.pop("bm25_score")
        results.append((SpanRow(**row), score))
    return results


async def list_exact_spans(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    seed_entity_ids: list[UUID],
    limit: int,
) -> list[SpanRow]:
    """Eligible spans tagged with any seed entity, newest first."""
    if not seed_entity_ids or limit <= 0:
        return []
    params = {**ctx.to_params(), "entity_ids": seed_entity_ids, "limit": limit}
    async with connection.cursor(row_factory=class_row(SpanRow)) as cursor:
        await cursor.execute(LIST_EXACT_SPANS_SQL, params)
        return await cursor.fetchall()


async def search_eligible_spans_bm25(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    query_text: str,
    limit: int,
) -> list[tuple[SpanRow, float]]:
    """Eligible BM25 matches, best first (score ascending, lower is better). A blank
    query or a query matching nothing returns no rows, never 0.0-scored ones."""
    if not query_text.strip() or limit <= 0:
        return []
    params = {**ctx.to_params(), "query_text": query_text, "limit": limit}
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(SEARCH_ELIGIBLE_SPANS_BM25_SQL, params)
        rows = await cursor.fetchall()
    return [(SpanRow(**row), row["bm25_score"]) for row in rows]


async def first_unembedded_sequence(
    connection: AsyncConnection,
    playthrough_id: UUID,
    model: str,
    model_version: str,
    failure_limit: int,
) -> int | None:
    params = {
        "playthrough_id": playthrough_id,
        "model": model,
        "model_version": model_version,
        "failure_limit": failure_limit,
    }
    async with connection.cursor() as cursor:
        await cursor.execute(FIRST_UNEMBEDDED_SEQUENCE_SQL, params)
        row = await cursor.fetchone()
    assert row is not None
    return row[0]


async def get_eligible_spans_by_ids(
    connection: AsyncConnection, ctx: EligibilityContext, span_ids: list[UUID]
) -> list[SpanRow]:
    """The subset of `span_ids` that passes every eligibility predicate, newest first.
    An ineligible id is simply absent, never an error."""
    if not span_ids:
        return []
    params = {**ctx.to_params(), "span_ids": span_ids}
    async with connection.cursor(row_factory=class_row(SpanRow)) as cursor:
        await cursor.execute(GET_ELIGIBLE_SPANS_BY_IDS_SQL, params)
        return await cursor.fetchall()


async def get_span_origins(
    connection: AsyncConnection, ctx: EligibilityContext, span_ids: list[UUID]
) -> dict[UUID, SpanOrigin]:
    """Source kind and actor per eligible span; ineligible ids are absent."""
    if not span_ids:
        return {}
    params = {**ctx.to_params(), "span_ids": span_ids}
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(GET_SPAN_ORIGINS_SQL, params)
        rows = await cursor.fetchall()
    return {
        row["span_id"]: SpanOrigin(
            source_kind=row["source_kind"],
            actor_participant_id=row["actor_participant_id"],
        )
        for row in rows
    }


async def list_template_spans_in_order(
    connection: AsyncConnection, template_id: UUID
) -> list[SpanRow]:
    """Stable order (source, ordinal): enrichment chunk N must map to the same spans
    on every sweep."""
    async with connection.cursor(row_factory=class_row(SpanRow)) as cursor:
        await cursor.execute(
            SELECT_TEMPLATE_SPANS_IN_ORDER_SQL, {"template_id": template_id}
        )
        return await cursor.fetchall()
