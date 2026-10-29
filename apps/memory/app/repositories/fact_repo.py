"""memory_fact, memory_fact_source and memory_supersession. Facts are append-only;
supersession is an appended row scoped to one playthrough."""

from collections import defaultdict
from uuid import UUID

from app.models.common import ScopeKind
from app.models.eligibility import EligibilityContext
from app.models.evidence import SpanRow
from app.models.facts import (
    FactCreate,
    FactRow,
    FactSourceCreate,
    FactSourceRow,
    SupersessionCreate,
    SupersessionRow,
)
from app.models.retrieval_rows import GraphEdges
from app.repositories.eligibility_predicates import FACT_ELIGIBLE, SPAN_ELIGIBLE
from psycopg import AsyncConnection, AsyncCursor
from psycopg.rows import class_row, dict_row

INSERT_FACT = """
INSERT INTO memory_fact (
    scope_kind, scope_id, subject_entity_id, predicate, object_entity_id,
    object_literal, authority, assertion, speaker_entity_id, valid_from_seq,
    authored_fact_id, is_hidden, conditional, supersedes_authored_fact_id,
    extraction_batch_id, event_id
) VALUES (
    %(scope_kind)s, %(scope_id)s, %(subject_entity_id)s, %(predicate)s,
    %(object_entity_id)s, %(object_literal)s, %(authority)s, %(assertion)s,
    %(speaker_entity_id)s, %(valid_from_seq)s, %(authored_fact_id)s,
    %(is_hidden)s, %(conditional)s, %(supersedes_authored_fact_id)s,
    %(extraction_batch_id)s, %(event_id)s
)
RETURNING *
"""

INSERT_FACT_SOURCE = """
INSERT INTO memory_fact_source (fact_id, span_id)
VALUES (%(fact_id)s, %(span_id)s)
ON CONFLICT (fact_id, span_id) DO NOTHING
"""

SELECT_FACT_SOURCES = """
SELECT fact_id, span_id FROM memory_fact_source
WHERE fact_id = ANY(%(fact_ids)s::uuid[])
ORDER BY fact_id, span_id
"""

INSERT_SUPERSESSION = """
INSERT INTO memory_supersession (
    playthrough_id, fact_id, at_seq, superseding_fact_id, authority,
    evidence_span_id, extraction_batch_id, event_id
) VALUES (
    %(playthrough_id)s, %(fact_id)s, %(at_seq)s, %(superseding_fact_id)s,
    %(authority)s, %(evidence_span_id)s, %(extraction_batch_id)s, %(event_id)s
)
ON CONFLICT (playthrough_id, fact_id, at_seq) DO NOTHING
"""

SELECT_SUPERSESSIONS_BY_KEY = """
SELECT supersession.*
FROM unnest(
    %(playthrough_ids)s::uuid[], %(fact_ids)s::uuid[], %(at_seqs)s::int[]
) WITH ORDINALITY AS requested (playthrough_id, fact_id, at_seq, ordinal)
JOIN memory_supersession AS supersession
    ON supersession.playthrough_id = requested.playthrough_id
    AND supersession.fact_id = requested.fact_id
    AND supersession.at_seq = requested.at_seq
ORDER BY requested.ordinal
"""

VALID_FACTS_AT_PREDICATE = """
SELECT fact.* FROM memory_fact AS fact
WHERE (
    (fact.scope_kind = 'template' AND fact.scope_id = %(template_id)s)
    OR (fact.scope_kind = 'playthrough' AND fact.scope_id = %(playthrough_id)s)
)
AND fact.valid_from_seq <= %(at_seq)s
AND NOT EXISTS (
    SELECT 1 FROM memory_supersession AS supersession
    WHERE supersession.playthrough_id = %(playthrough_id)s
    AND supersession.fact_id = fact.fact_id
    AND supersession.at_seq <= %(at_seq)s
)
"""

VALID_FACTS_ORDER = """
ORDER BY fact.valid_from_seq, fact.created_at, fact.fact_id
"""

SUBJECT_FILTER = """
AND fact.subject_entity_id = ANY(%(entity_ids)s::uuid[])
"""

PREDICATE_FILTER = """
AND fact.predicate = %(predicate)s
"""

RELATION_FILTER = """
AND fact.object_entity_id IS NOT NULL
AND (
    fact.subject_entity_id = ANY(%(entity_ids)s::uuid[])
    OR fact.object_entity_id = ANY(%(entity_ids)s::uuid[])
)
"""

SELECT_VALID_FACTS_AT = VALID_FACTS_AT_PREDICATE + VALID_FACTS_ORDER
SELECT_VALID_FACTS_AT_BY_PREDICATE = (
    VALID_FACTS_AT_PREDICATE + PREDICATE_FILTER + VALID_FACTS_ORDER
)
SELECT_VALID_SUBJECT_FACTS_AT = (
    VALID_FACTS_AT_PREDICATE + SUBJECT_FILTER + VALID_FACTS_ORDER
)
SELECT_VALID_SUBJECT_FACTS_AT_BY_PREDICATE = (
    VALID_FACTS_AT_PREDICATE + SUBJECT_FILTER + PREDICATE_FILTER + VALID_FACTS_ORDER
)
SELECT_VALID_RELATIONS_AT = (
    VALID_FACTS_AT_PREDICATE + RELATION_FILTER + VALID_FACTS_ORDER
)

ACCEPTED_FACTS_AFTER_PREDICATE = """
SELECT fact.* FROM memory_fact AS fact
WHERE fact.scope_kind = 'playthrough' AND fact.scope_id = %(playthrough_id)s
AND fact.subject_entity_id = %(subject_entity_id)s
AND fact.predicate = %(predicate)s
AND fact.authority = 'accepted'
AND fact.valid_from_seq > %(after_seq)s
"""

SELECT_ACCEPTED_FACTS_AFTER = (
    ACCEPTED_FACTS_AFTER_PREDICATE + "ORDER BY fact.valid_from_seq ASC\n"
)

LIST_ELIGIBLE_FACTS_FOR_ENTITIES_SQL = f"""
SELECT fact.* FROM memory_fact AS fact
WHERE {FACT_ELIGIBLE}
    AND (
        fact.subject_entity_id = ANY(%(entity_ids)s::uuid[])
        OR fact.object_entity_id = ANY(%(entity_ids)s::uuid[])
    )
ORDER BY fact.valid_from_seq DESC, fact.fact_id DESC
LIMIT %(limit)s
"""

LIST_ELIGIBLE_LITERAL_FACTS_SQL = f"""
SELECT fact.* FROM memory_fact AS fact
WHERE {FACT_ELIGIBLE}
    AND fact.object_entity_id IS NULL
    AND fact.subject_entity_id = ANY(%(entity_ids)s::uuid[])
ORDER BY fact.valid_from_seq DESC, fact.fact_id DESC
LIMIT %(limit)s
"""

GET_ELIGIBLE_FACTS_BY_IDS_SQL = f"""
SELECT fact.* FROM memory_fact AS fact
WHERE fact.fact_id = ANY(%(fact_ids)s::uuid[])
    AND {FACT_ELIGIBLE}
ORDER BY fact.valid_from_seq DESC, fact.fact_id DESC
"""

LIST_GRAPH_EDGE_ROWS_SQL = f"""
WITH eligible_edges AS (
    SELECT fact.*, endpoint.entity_id AS frontier_entity_id
    FROM memory_fact AS fact
    CROSS JOIN LATERAL (
        SELECT fact.subject_entity_id AS entity_id
        UNION
        SELECT fact.object_entity_id
    ) AS endpoint
    WHERE fact.object_entity_id IS NOT NULL
        AND endpoint.entity_id = ANY(%(frontier_entity_ids)s::uuid[])
        AND {FACT_ELIGIBLE}
),
ranked_edges AS (
    SELECT eligible_edges.*,
        row_number() OVER (
            PARTITION BY frontier_entity_id
            ORDER BY valid_from_seq DESC, fact_id DESC
        ) AS edge_rank,
        count(*) OVER (PARTITION BY frontier_entity_id) AS edge_count
    FROM eligible_edges
)
SELECT * FROM ranked_edges WHERE edge_rank <= %(hub_edge_cap)s
"""

LIST_REPRESENTATIVE_SOURCE_SPANS_SQL = f"""
SELECT DISTINCT ON (link.fact_id) link.fact_id AS linked_fact_id, span.*
FROM memory_fact_source AS link
JOIN memory_span AS span ON span.span_id = link.span_id
WHERE link.fact_id = ANY(%(fact_ids)s::uuid[])
    AND {SPAN_ELIGIBLE}
ORDER BY link.fact_id, span.sequence, span.span_id
"""


async def _fetch_every_result_set(cursor: AsyncCursor[FactRow]) -> list[FactRow]:
    rows: list[FactRow] = []
    has_result = True
    while has_result:
        rows.extend(await cursor.fetchall())
        has_result = cursor.nextset() is True
    return rows


async def create_facts(
    connection: AsyncConnection, facts: list[FactCreate]
) -> list[FactRow]:
    """Plain appends in input order; re-delivery safety comes from batch artifacts."""
    if not facts:
        return []
    params = [fact.model_dump() for fact in facts]
    async with connection.cursor(row_factory=class_row(FactRow)) as cursor:
        await cursor.executemany(INSERT_FACT, params, returning=True)
        return await _fetch_every_result_set(cursor)


async def add_fact_sources(
    connection: AsyncConnection, links: list[FactSourceCreate]
) -> None:
    if not links:
        return
    params = [link.model_dump() for link in links]
    async with connection.cursor() as cursor:
        await cursor.executemany(INSERT_FACT_SOURCE, params)


async def _select_fact_source_rows(
    connection: AsyncConnection, fact_ids: list[UUID]
) -> list[FactSourceRow]:
    async with connection.cursor(row_factory=class_row(FactSourceRow)) as cursor:
        await cursor.execute(SELECT_FACT_SOURCES, {"fact_ids": fact_ids})
        return await cursor.fetchall()


def _group_span_ids_by_fact(rows: list[FactSourceRow]) -> dict[UUID, list[UUID]]:
    span_ids_by_fact: defaultdict[UUID, list[UUID]] = defaultdict(list)
    for row in rows:
        span_ids_by_fact[row.fact_id].append(row.span_id)
    return dict(span_ids_by_fact)


async def get_fact_sources(
    connection: AsyncConnection, fact_ids: list[UUID]
) -> dict[UUID, list[UUID]]:
    """Span ids per fact; facts with no source are absent from the result."""
    rows = await _select_fact_source_rows(connection, fact_ids)
    return _group_span_ids_by_fact(rows)


def _supersession_key_params(
    rows: list[SupersessionCreate],
) -> dict[str, list[UUID] | list[int]]:
    return {
        "playthrough_ids": [row.playthrough_id for row in rows],
        "fact_ids": [row.fact_id for row in rows],
        "at_seqs": [row.at_seq for row in rows],
    }


async def add_supersessions(
    connection: AsyncConnection, rows: list[SupersessionCreate]
) -> list[SupersessionRow]:
    """Idempotent on (playthrough_id, fact_id, at_seq): an existing row wins and is
    returned unchanged, in input order."""
    if not rows:
        return []
    params = [row.model_dump() for row in rows]
    async with connection.cursor(row_factory=class_row(SupersessionRow)) as cursor:
        await cursor.executemany(INSERT_SUPERSESSION, params)
        await cursor.execute(
            SELECT_SUPERSESSIONS_BY_KEY, _supersession_key_params(rows)
        )
        return await cursor.fetchall()


async def _select_facts(
    connection: AsyncConnection, statement: str, params: dict[str, object]
) -> list[FactRow]:
    async with connection.cursor(row_factory=class_row(FactRow)) as cursor:
        await cursor.execute(statement, params)
        return await cursor.fetchall()


def _validity_params(
    playthrough_id: UUID, template_id: UUID | None, at_seq: int
) -> dict[str, object]:
    return {
        "playthrough_id": playthrough_id,
        "template_id": template_id,
        "at_seq": at_seq,
    }


def _valid_facts_at_statement(
    *, has_subject_filter: bool, has_predicate_filter: bool
) -> str:
    if has_subject_filter and has_predicate_filter:
        return SELECT_VALID_SUBJECT_FACTS_AT_BY_PREDICATE
    if has_subject_filter:
        return SELECT_VALID_SUBJECT_FACTS_AT
    if has_predicate_filter:
        return SELECT_VALID_FACTS_AT_BY_PREDICATE
    return SELECT_VALID_FACTS_AT


async def list_valid_facts_at(
    connection: AsyncConnection,
    playthrough_id: UUID,
    template_id: UUID | None,
    at_seq: int,
    *,
    subject_entity_ids: list[UUID] | None = None,
    predicate: str | None = None,
) -> list[FactRow]:
    """Facts valid for the playthrough at `at_seq` (data-model §3.4 "Validity at N").

    `template_id` None reads the playthrough scope only (template_missing). Hidden
    and conditional eligibility is not applied here; callers filter on the
    returned `is_hidden`, `conditional` and `authored_fact_id`.
    """
    params = _validity_params(playthrough_id, template_id, at_seq)
    if subject_entity_ids is not None:
        params["entity_ids"] = subject_entity_ids
    if predicate is not None:
        params["predicate"] = predicate
    statement = _valid_facts_at_statement(
        has_subject_filter=subject_entity_ids is not None,
        has_predicate_filter=predicate is not None,
    )
    return await _select_facts(connection, statement, params)


async def list_accepted_facts_after(
    connection: AsyncConnection,
    playthrough_id: UUID,
    subject_entity_id: UUID,
    predicate: str,
    after_seq: int,
) -> list[FactRow]:
    params = {
        "playthrough_id": playthrough_id,
        "subject_entity_id": subject_entity_id,
        "predicate": predicate,
        "after_seq": after_seq,
    }
    return await _select_facts(connection, SELECT_ACCEPTED_FACTS_AFTER, params)


async def list_valid_relations_at(
    connection: AsyncConnection,
    playthrough_id: UUID,
    template_id: UUID | None,
    at_seq: int,
    entity_ids: list[UUID],
) -> list[FactRow]:
    """Valid entity-to-entity facts touching any of `entity_ids` as subject or object:
    one hop of the graph, with no traversal or hub handling."""
    params = _validity_params(playthrough_id, template_id, at_seq)
    params["entity_ids"] = entity_ids
    return await _select_facts(connection, SELECT_VALID_RELATIONS_AT, params)


async def list_eligible_facts_for_entities(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    entity_ids: list[UUID],
    limit: int,
) -> list[FactRow]:
    """Eligible facts (relation and literal) with any of `entity_ids` as subject or
    object, newest first. Serves the exact branch and neighbour expansion alike."""
    if not entity_ids or limit <= 0:
        return []
    params = {**ctx.to_params(), "entity_ids": entity_ids, "limit": limit}
    return await _select_facts(connection, LIST_ELIGIBLE_FACTS_FOR_ENTITIES_SQL, params)


async def list_eligible_literal_facts_for_entities(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    entity_ids: list[UUID],
    limit: int,
) -> list[FactRow]:
    """Eligible facts with no object entity (attributes) about any of `entity_ids`,
    newest first. Relation facts are excluded so a neighbour's own edges cannot add
    a hop the graph traversal did not take."""
    if not entity_ids or limit <= 0:
        return []
    params = {**ctx.to_params(), "entity_ids": entity_ids, "limit": limit}
    return await _select_facts(connection, LIST_ELIGIBLE_LITERAL_FACTS_SQL, params)


async def get_eligible_facts_by_ids(
    connection: AsyncConnection, ctx: EligibilityContext, fact_ids: list[UUID]
) -> list[FactRow]:
    """The subset of `fact_ids` that passes every eligibility predicate, newest
    first. An ineligible id is simply absent, never an error."""
    if not fact_ids:
        return []
    params = {**ctx.to_params(), "fact_ids": fact_ids}
    return await _select_facts(connection, GET_ELIGIBLE_FACTS_BY_IDS_SQL, params)


def _split_graph_row(row: dict[str, object]) -> tuple[FactRow, UUID, int]:
    frontier_entity_id = row.pop("frontier_entity_id")
    edge_count = row.pop("edge_count")
    row.pop("edge_rank")
    return FactRow(**row), frontier_entity_id, edge_count


def _find_hub_entity_ids(
    entries: list[tuple[FactRow, UUID, int]],
    frontier_entity_ids: list[UUID],
    hub_edge_cap: int,
    player_entity_id: UUID | None,
) -> frozenset[UUID]:
    hub_ids = {
        entity_id
        for _fact, entity_id, edge_count in entries
        if edge_count > hub_edge_cap
    }
    if player_entity_id is not None and player_entity_id in frontier_entity_ids:
        hub_ids.add(player_entity_id)
    return frozenset(hub_ids)


def _collect_edges(
    entries: list[tuple[FactRow, UUID, int]],
    hub_entity_ids: frozenset[UUID],
    should_expand_hubs: bool,
) -> list[FactRow]:
    edges_by_id: dict[UUID, FactRow] = {}
    for fact, entity_id, _edge_count in entries:
        if entity_id in hub_entity_ids and not should_expand_hubs:
            continue
        edges_by_id[fact.fact_id] = fact
    return sorted(
        edges_by_id.values(),
        key=lambda edge: (edge.valid_from_seq, edge.fact_id),
        reverse=True,
    )


async def _fetch_graph_entries(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    frontier_entity_ids: list[UUID],
    hub_edge_cap: int,
) -> list[tuple[FactRow, UUID, int]]:
    params = {
        **ctx.to_params(),
        "frontier_entity_ids": frontier_entity_ids,
        "hub_edge_cap": hub_edge_cap,
    }
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(LIST_GRAPH_EDGE_ROWS_SQL, params)
        rows = await cursor.fetchall()
    return [_split_graph_row(row) for row in rows]


async def list_graph_edges(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    frontier_entity_ids: list[UUID],
    *,
    hub_edge_cap: int,
    player_entity_id: UUID | None,
    should_expand_hubs: bool = True,
) -> GraphEdges:
    """One hop over eligible relation facts touching the frontier.

    A frontier entity with more than `hub_edge_cap` eligible edges is a hub, as is
    `player_entity_id` when it is in the frontier. With `should_expand_hubs` (hop 1)
    a hub keeps its `hub_edge_cap` newest edges; without it (hop 2) a hub adds no
    edges. Only eligible edges count toward the threshold. The service decides which
    entities form the next frontier; this function never recurses.
    """
    if not frontier_entity_ids or hub_edge_cap <= 0:
        return GraphEdges(edges=[], hub_entity_ids=frozenset())
    entries = await _fetch_graph_entries(
        connection, ctx, frontier_entity_ids, hub_edge_cap
    )
    hub_ids = _find_hub_entity_ids(
        entries, frontier_entity_ids, hub_edge_cap, player_entity_id
    )
    edges = _collect_edges(entries, hub_ids, should_expand_hubs)
    return GraphEdges(edges=edges, hub_entity_ids=hub_ids)


async def get_representative_source_spans(
    connection: AsyncConnection, ctx: EligibilityContext, fact_ids: list[UUID]
) -> dict[UUID, SpanRow]:
    """One eligible source span per fact (lowest sequence, then span_id); facts with
    no eligible source span are absent. The window rule applies to the span."""
    if not fact_ids:
        return {}
    params = {**ctx.to_params(), "fact_ids": fact_ids}
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(LIST_REPRESENTATIVE_SOURCE_SPANS_SQL, params)
        rows = await cursor.fetchall()
    return {row["linked_fact_id"]: SpanRow(**row) for row in rows}


DELETE_SCOPE_FACTS_SQL = (
    "DELETE FROM memory_fact "
    "WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s"
)


async def delete_scope_facts(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> int:
    async with connection.cursor() as cursor:
        await cursor.execute(
            DELETE_SCOPE_FACTS_SQL, {"scope_kind": scope_kind, "scope_id": scope_id}
        )
        return cursor.rowcount
