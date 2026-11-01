"""memory_source: idempotent create, sequence-range listing, scope isolation."""

from uuid import UUID

from app.models.evidence import SourceCreate
from app.repositories.source_repo import (
    create_source,
    create_source_with_status,
    get_contiguous_sequence,
    get_source_by_ref,
    list_sources,
)
from psycopg import AsyncConnection
from tests.repositories.helpers_evidence import make_source, make_template


async def test_create_source_idempotent_reinsert_returns_existing_no_duplicate(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    scope_id = template.template_id
    first = await make_source(
        db_connection, scope_kind="template", scope_id=scope_id, source_ref="ref-a"
    )

    second = await make_source(
        db_connection, scope_kind="template", scope_id=scope_id, source_ref="ref-a"
    )

    assert second.source_id == first.source_id
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_source WHERE scope_id = %s", (scope_id,)
    )
    assert await cursor.fetchone() == (1,)


async def test_create_source_returns_row(db_connection: AsyncConnection) -> None:
    template = await make_template(db_connection)

    row = await create_source(
        db_connection,
        SourceCreate(
            scope_kind="template",
            scope_id=template.template_id,
            source_kind="authored_lore",
            source_ref="ref-direct",
            sequence=0,
            content="content",
            content_hash="hash",
        ),
    )

    assert row.scope_kind == "template"
    assert row.scope_id == template.template_id
    assert row.source_id is not None


async def _setup_sources_at_sequences(
    connection: AsyncConnection,
) -> tuple:
    template = await make_template(connection)
    scope_id = template.template_id
    early = await make_source(
        connection,
        scope_kind="template",
        scope_id=scope_id,
        source_ref="early",
        sequence=1,
    )
    mid = await make_source(
        connection,
        scope_kind="template",
        scope_id=scope_id,
        source_ref="mid",
        sequence=5,
    )
    late = await make_source(
        connection,
        scope_kind="template",
        scope_id=scope_id,
        source_ref="late",
        sequence=9,
    )
    return scope_id, early, mid, late


async def test_list_sources_filters_by_sequence_range(
    db_connection: AsyncConnection,
) -> None:
    scope_id, early, mid, late = await _setup_sources_at_sequences(db_connection)

    rows = await list_sources(db_connection, "template", scope_id, 1, 5)

    assert [row.source_id for row in rows] == [early.source_id, mid.source_id]
    assert late.source_id not in [row.source_id for row in rows]


async def test_list_sources_scope_isolation(db_connection: AsyncConnection) -> None:
    template_a = await make_template(db_connection)
    template_b = await make_template(db_connection)
    source_a = await make_source(
        db_connection,
        scope_kind="template",
        scope_id=template_a.template_id,
        source_ref="shared-ref",
        content="identical text",
    )
    source_b = await make_source(
        db_connection,
        scope_kind="template",
        scope_id=template_b.template_id,
        source_ref="shared-ref",
        content="identical text",
    )

    rows_a = await list_sources(
        db_connection, "template", template_a.template_id, 0, 100
    )
    rows_b = await list_sources(
        db_connection, "template", template_b.template_id, 0, 100
    )

    assert [row.source_id for row in rows_a] == [source_a.source_id]
    assert [row.source_id for row in rows_b] == [source_b.source_id]


async def test_create_source_with_status_reports_inserted_then_not_inserted(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    source = SourceCreate(
        scope_kind="template",
        scope_id=template.template_id,
        source_kind="authored_lore",
        source_ref="ref-status",
        sequence=0,
        content="content",
        content_hash="hash",
    )

    first_row, first_is_inserted = await create_source_with_status(
        db_connection, source
    )
    second_row, second_is_inserted = await create_source_with_status(
        db_connection, source
    )

    assert first_is_inserted is True
    assert second_is_inserted is False
    assert second_row.source_id == first_row.source_id


async def _make_sources_at_sequences(
    connection: AsyncConnection, scope_id: UUID, sequences: tuple[int, ...]
) -> None:
    for sequence in sequences:
        await make_source(
            connection,
            scope_kind="template",
            scope_id=scope_id,
            source_kind="turn_action",
            source_ref=f"seq-{sequence}",
            sequence=sequence,
        )


async def test_get_contiguous_sequence_full_run(db_connection: AsyncConnection) -> None:
    template = await make_template(db_connection)
    await _make_sources_at_sequences(db_connection, template.template_id, (1, 2, 3))

    result = await get_contiguous_sequence(
        db_connection, "template", template.template_id, "turn_action"
    )

    assert result == 3


async def test_get_contiguous_sequence_gap_after_one(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    await _make_sources_at_sequences(db_connection, template.template_id, (1, 3))

    result = await get_contiguous_sequence(
        db_connection, "template", template.template_id, "turn_action"
    )

    assert result == 1


async def test_get_contiguous_sequence_missing_start(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    await _make_sources_at_sequences(db_connection, template.template_id, (2, 3))

    result = await get_contiguous_sequence(
        db_connection, "template", template.template_id, "turn_action"
    )

    assert result == 0


async def test_get_contiguous_sequence_empty_scope(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)

    result = await get_contiguous_sequence(
        db_connection, "template", template.template_id, "turn_action"
    )

    assert result == 0


async def test_get_contiguous_sequence_ignores_other_scope_and_kind(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    other_template = await make_template(db_connection)
    await _make_sources_at_sequences(db_connection, template.template_id, (1, 2, 3))
    await _make_sources_at_sequences(
        db_connection, other_template.template_id, (1, 2, 3, 4)
    )
    await make_source(
        db_connection,
        scope_kind="template",
        scope_id=template.template_id,
        source_kind="authored_lore",
        source_ref="other-kind",
        sequence=4,
    )

    result = await get_contiguous_sequence(
        db_connection, "template", template.template_id, "turn_action"
    )

    assert result == 3


async def test_get_source_by_ref_returns_row_or_none(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    scope_id = template.template_id
    created = await make_source(
        db_connection, scope_kind="template", scope_id=scope_id, source_ref="ref-a"
    )

    found = await get_source_by_ref(
        db_connection, "template", scope_id, created.source_kind, "ref-a"
    )
    missing = await get_source_by_ref(
        db_connection, "template", scope_id, created.source_kind, "ref-missing"
    )

    assert found is not None
    assert found.source_id == created.source_id
    assert missing is None
