"""memory_span: batch idempotent create, sequence/label listing, scope isolation,
BM25 gating check, FK cascade from memory_source."""

from uuid import UUID

from app.models.common import ScopeKind
from app.repositories.span_repo import (
    create_spans,
    list_spans_by_labels,
    list_spans_by_sequence,
    search_spans_bm25,
)
from psycopg import AsyncConnection
from tests.repositories.helpers_evidence import (
    build_span,
    make_playthrough,
    make_source,
    make_template,
)

DRAGON_TEXT = "the dragon sleeps in the ancient cave"


async def test_create_spans_empty_list_returns_empty(
    db_connection: AsyncConnection,
) -> None:
    assert await create_spans(db_connection, []) == []


async def test_create_spans_inserts_batch_in_input_order(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    source = await make_source(
        db_connection, scope_kind="template", scope_id=template.template_id
    )
    spans = [
        build_span(
            source_id=source.source_id,
            scope_kind="template",
            scope_id=template.template_id,
            ordinal=ordinal,
            text=f"span {ordinal}",
        )
        for ordinal in (2, 0, 1)
    ]

    rows = await create_spans(db_connection, spans)

    assert [row.ordinal for row in rows] == [2, 0, 1]
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_span WHERE source_id = %s", (source.source_id,)
    )
    assert await cursor.fetchone() == (3,)


async def test_create_spans_idempotent_reinsert_returns_existing_no_duplicate(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    source = await make_source(
        db_connection, scope_kind="template", scope_id=template.template_id
    )
    span = build_span(
        source_id=source.source_id, scope_kind="template", scope_id=template.template_id
    )

    first = await create_spans(db_connection, [span])
    second = await create_spans(db_connection, [span])

    assert second[0].span_id == first[0].span_id
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_span WHERE source_id = %s", (source.source_id,)
    )
    assert await cursor.fetchone() == (1,)


async def test_create_spans_mixed_new_and_existing(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    source = await make_source(
        db_connection, scope_kind="template", scope_id=template.template_id
    )
    existing_span = build_span(
        source_id=source.source_id,
        scope_kind="template",
        scope_id=template.template_id,
        ordinal=0,
    )
    await create_spans(db_connection, [existing_span])
    new_span = build_span(
        source_id=source.source_id,
        scope_kind="template",
        scope_id=template.template_id,
        ordinal=1,
    )

    rows = await create_spans(db_connection, [existing_span, new_span])

    assert [row.ordinal for row in rows] == [0, 1]
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_span WHERE source_id = %s", (source.source_id,)
    )
    assert await cursor.fetchone() == (2,)


async def test_list_spans_by_sequence_filters_range(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    source = await make_source(
        db_connection, scope_kind="template", scope_id=template.template_id
    )
    spans = [
        build_span(
            source_id=source.source_id,
            scope_kind="template",
            scope_id=template.template_id,
            ordinal=ordinal,
            sequence=sequence,
        )
        for ordinal, sequence in enumerate((1, 5, 9))
    ]
    created = await create_spans(db_connection, spans)

    rows = await list_spans_by_sequence(
        db_connection, "template", template.template_id, 1, 5
    )

    assert {row.span_id for row in rows} == {created[0].span_id, created[1].span_id}


async def test_list_spans_by_labels_filters_by_label(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    source = await make_source(
        db_connection, scope_kind="template", scope_id=template.template_id
    )
    matching = build_span(
        source_id=source.source_id,
        scope_kind="template",
        scope_id=template.template_id,
        ordinal=0,
        label="L1",
    )
    other = build_span(
        source_id=source.source_id,
        scope_kind="template",
        scope_id=template.template_id,
        ordinal=1,
        label="L2",
    )
    created = await create_spans(db_connection, [matching, other])

    rows = await list_spans_by_labels(
        db_connection, "template", template.template_id, ["L1"]
    )

    assert [row.span_id for row in rows] == [created[0].span_id]


async def _create_scoped_span_with_text(
    connection: AsyncConnection, source_ref: str, text: str
) -> tuple:
    template = await make_template(connection)
    source = await make_source(
        connection,
        scope_kind="template",
        scope_id=template.template_id,
        source_ref=source_ref,
    )
    span = build_span(
        source_id=source.source_id,
        scope_kind="template",
        scope_id=template.template_id,
        text=text,
    )
    created = await create_spans(connection, [span])
    return template, created


async def _setup_two_scoped_spans(
    connection: AsyncConnection,
) -> tuple:
    template_a, created_a = await _create_scoped_span_with_text(
        connection, "a", "identical text"
    )
    template_b, created_b = await _create_scoped_span_with_text(
        connection, "b", "identical text"
    )
    return template_a, template_b, created_a, created_b


async def test_list_spans_by_sequence_scope_isolation(
    db_connection: AsyncConnection,
) -> None:
    template_a, template_b, created_a, created_b = await _setup_two_scoped_spans(
        db_connection
    )

    rows_a = await list_spans_by_sequence(
        db_connection, "template", template_a.template_id, 0, 100
    )
    rows_b = await list_spans_by_sequence(
        db_connection, "template", template_b.template_id, 0, 100
    )

    assert [row.span_id for row in rows_a] == [created_a[0].span_id]
    assert [row.span_id for row in rows_b] == [created_b[0].span_id]


async def _seed_bm25_scope(
    db_connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID, *, text: str
) -> None:
    source = await make_source(
        db_connection,
        scope_kind=scope_kind,
        scope_id=scope_id,
        source_ref=f"{scope_kind}-{scope_id}",
    )
    span = build_span(
        source_id=source.source_id, scope_kind=scope_kind, scope_id=scope_id, text=text
    )
    await create_spans(db_connection, [span])


async def _setup_bm25_scopes_for_search(
    connection: AsyncConnection,
) -> tuple:
    template_1 = await make_template(connection)
    template_2 = await make_template(connection)
    playthrough_1 = await make_source_playthrough(connection)
    playthrough_2 = await make_source_playthrough(connection)

    await _seed_bm25_scope(
        connection, "template", template_1.template_id, text=DRAGON_TEXT
    )
    await _seed_bm25_scope(
        connection, "template", template_2.template_id, text=DRAGON_TEXT
    )
    await _seed_bm25_scope(
        connection,
        "playthrough",
        playthrough_1,
        text="the dragon dragon dragon roars",
    )
    await _seed_bm25_scope(connection, "playthrough", playthrough_2, text=DRAGON_TEXT)
    return template_1, playthrough_1


async def test_search_spans_bm25_scopes_and_ranks(
    db_connection: AsyncConnection,
) -> None:
    template_1, playthrough_1 = await _setup_bm25_scopes_for_search(db_connection)

    results = await search_spans_bm25(
        db_connection,
        [("template", template_1.template_id), ("playthrough", playthrough_1)],
        "dragon",
        limit=10,
    )

    scopes = {(row.scope_kind, row.scope_id) for row, _score in results}
    assert scopes == {
        ("template", template_1.template_id),
        ("playthrough", playthrough_1),
    }
    assert len(results) == 2
    scores = [score for _row, score in results]
    assert scores == sorted(scores)


async def test_search_spans_bm25_non_matching_query_returns_nothing(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    await _seed_bm25_scope(
        db_connection, "template", template.template_id, text=DRAGON_TEXT
    )

    results = await search_spans_bm25(
        db_connection, [("template", template.template_id)], "wizard", limit=10
    )

    assert results == []


async def test_search_spans_bm25_empty_scopes_returns_nothing(
    db_connection: AsyncConnection,
) -> None:
    assert await search_spans_bm25(db_connection, [], "dragon", limit=10) == []


async def test_deleting_source_cascades_to_its_spans(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    source = await make_source(
        db_connection, scope_kind="template", scope_id=template.template_id
    )
    span = build_span(
        source_id=source.source_id, scope_kind="template", scope_id=template.template_id
    )
    await create_spans(db_connection, [span])

    await db_connection.execute(
        "DELETE FROM memory_source WHERE source_id = %s", (source.source_id,)
    )

    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_span WHERE source_id = %s", (source.source_id,)
    )
    assert await cursor.fetchone() == (0,)


async def make_source_playthrough(db_connection: AsyncConnection) -> UUID:
    row = await make_playthrough(db_connection)
    return row.playthrough_id
