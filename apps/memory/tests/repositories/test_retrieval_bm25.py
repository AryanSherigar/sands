"""Eligible BM25 search. The gate tests build corpora where the best-scoring matches
are ineligible, to prove eligible matches still fill the limit."""

from uuid import UUID, uuid4

from app.models.eligibility import EligibilityContext
from app.repositories import span_repo
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers

QUERY = "dragon"
ELIGIBLE_COUNT = 5
BULK_HIDDEN_COUNT = 1200
BULK_IN_WINDOW_COUNT = 400
BM25_INDEX_NAME = "memory_span_text_bm25_idx"

INSERT_BULK_SPANS_SQL = """
INSERT INTO memory_span (
    source_id, scope_kind, scope_id, sequence, ordinal, start_offset, end_offset,
    text, token_count, label, is_hidden, authored_fact_id
)
SELECT %(source_id)s, %(scope_kind)s, %(scope_id)s, %(sequence)s, generated, 0, 1,
    %(text)s::text || ' ' || generated, 1, 'BULK', %(is_hidden)s::boolean,
    CASE WHEN %(is_hidden)s::boolean THEN gen_random_uuid() END
FROM generate_series(1, %(count)s) AS generated
"""
INSERT_BULK_SOURCE_SQL = """
INSERT INTO memory_source (
    scope_kind, scope_id, source_kind, source_ref, sequence, content, content_hash
) VALUES (%(scope_kind)s, %(scope_id)s, %(source_kind)s, 'bulk', 0, 'c', 'h')
RETURNING source_id
"""


async def _insert_bulk_spans(
    connection: AsyncConnection,
    scope: helpers.Scope,
    *,
    source_kind: str,
    sequence: int,
    is_hidden: bool,
    count: int,
) -> None:
    cursor = await connection.execute(
        INSERT_BULK_SOURCE_SQL,
        {"scope_kind": scope[0], "scope_id": scope[1], "source_kind": source_kind},
    )
    row = await cursor.fetchone()
    assert row is not None
    await connection.execute(
        INSERT_BULK_SPANS_SQL,
        {
            "source_id": row[0],
            "scope_kind": scope[0],
            "scope_id": scope[1],
            "sequence": sequence,
            "text": "dragon dragon dragon dragon",
            "is_hidden": is_hidden,
            "count": count,
        },
    )


async def _add_eligible_dragon_spans(
    connection: AsyncConnection, world: helpers.World
) -> set[UUID]:
    ids: set[UUID] = set()
    for index in range(ELIGIBLE_COUNT):
        span = await helpers.add_span(
            connection,
            world.playthrough_scope,
            text=f"a dragon was seen near hill {index}",
            sequence=index + 1,
        )
        ids.add(span.span_id)
    return ids


async def _search(
    connection: AsyncConnection, ctx: EligibilityContext, limit: int
) -> list[UUID]:
    hits = await span_repo.search_eligible_spans_bm25(connection, ctx, QUERY, limit)
    return [row.span_id for row, _score in hits]


async def test_bm25_returns_eligible_matches_when_the_best_scores_are_ineligible(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    eligible = await _add_eligible_dragon_spans(db_connection, world)
    for index in range(20):
        await helpers.add_span(
            db_connection,
            world.playthrough_scope,
            text="dragon dragon dragon dragon secret",
            sequence=1,
            is_hidden=True,
            authored_fact_id=uuid4(),
        )
        await helpers.add_span(
            db_connection,
            world.playthrough_scope,
            text="dragon dragon dragon dragon fresh",
            sequence=29 - index % 3,
        )
    ctx = helpers.make_context(world)

    limited = await _search(db_connection, ctx, 3)
    everything = await _search(db_connection, ctx, 50)

    assert len(limited) == 3
    assert set(limited) <= eligible
    assert set(everything) == eligible


async def test_bm25_refills_past_the_default_index_limit_with_forced_index_scan(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    eligible = await _add_eligible_dragon_spans(db_connection, world)
    await _insert_bulk_spans(
        db_connection,
        world.template_scope,
        source_kind="authored_fact_text",
        sequence=0,
        is_hidden=True,
        count=BULK_HIDDEN_COUNT,
    )
    await _insert_bulk_spans(
        db_connection,
        world.playthrough_scope,
        source_kind="turn_narration",
        sequence=29,
        is_hidden=False,
        count=BULK_IN_WINDOW_COUNT,
    )
    await db_connection.execute("ANALYZE memory_span")
    await db_connection.execute("SET LOCAL enable_seqscan = off")
    ctx = helpers.make_context(world)

    plan = await _explain(db_connection, ctx)
    limited = await _search(db_connection, ctx, 3)
    everything = await _search(db_connection, ctx, 40)

    assert BM25_INDEX_NAME in plan
    assert len(limited) == 3
    assert set(limited) <= eligible
    assert set(everything) == eligible


async def _explain(connection: AsyncConnection, ctx: EligibilityContext) -> str:
    params = {**ctx.to_params(), "query_text": QUERY, "limit": 3}
    cursor = await connection.execute(
        "EXPLAIN " + span_repo.SEARCH_ELIGIBLE_SPANS_BM25_SQL, params
    )
    return "\n".join(row[0] for row in await cursor.fetchall())


async def test_bm25_non_matching_query_returns_nothing_not_zero_scores(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await _add_eligible_dragon_spans(db_connection, world)
    ctx = helpers.make_context(world)

    hits = await span_repo.search_eligible_spans_bm25(
        db_connection, ctx, "zeppelin", 10
    )

    assert hits == []


async def test_bm25_orders_best_first_with_negative_scores(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    weak = await helpers.add_span(
        db_connection, scope, text="one dragon among many other words here", sequence=1
    )
    strong = await helpers.add_span(
        db_connection, scope, text="dragon dragon dragon", sequence=2
    )
    await helpers.add_span(db_connection, scope, text="only a castle", sequence=3)

    hits = await span_repo.search_eligible_spans_bm25(
        db_connection, helpers.make_context(world), QUERY, 10
    )

    assert [row.span_id for row, _ in hits] == [strong.span_id, weak.span_id]
    scores = [score for _, score in hits]
    assert scores == sorted(scores)
    assert all(score < 0 for score in scores)


async def test_bm25_hidden_span_with_the_query_text_appears_only_after_reveal(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    secret_id = uuid4()
    span = await helpers.add_span(
        db_connection,
        world.template_scope,
        text="the dragon hoard lies beneath the mountain",
        sequence=0,
        source_kind="authored_fact_text",
        is_hidden=True,
        authored_fact_id=secret_id,
    )

    before = await _search(db_connection, helpers.make_context(world), 5)
    after = await _search(
        db_connection, helpers.make_context(world, revealed=[secret_id]), 5
    )

    assert before == []
    assert after == [span.span_id]


async def test_bm25_search_with_no_limit_returns_nothing(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await _add_eligible_dragon_spans(db_connection, world)

    assert await _search(db_connection, helpers.make_context(world), 0) == []
