"""By-id lookups, span origins, failed-batch flag and the read-only snapshot: each
must apply the same eligibility as the branch queries they serve."""

from uuid import uuid4

import psycopg
import pytest
from app.models.common import ExtractionBatchStatus
from app.models.jobs import ExtractionBatchCreate
from app.repositories import (
    extraction_batch_repo,
    fact_repo,
    snapshot_repo,
    span_repo,
)
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers
from tests.repositories.retrieval_corpus import (
    Corpus,
    build_corpus,
    fact_labels_via_exact,
    put_fact,
    put_span,
    span_labels_via_exact,
)

CONTEXT_VARIANTS = [
    {},
    {"has_template": False},
    {"should_include_hidden": True},
    {"at_seq": 8},
]


async def populate(connection: AsyncConnection, corpus: Corpus) -> None:
    world = corpus.world
    revealed, active = uuid4(), uuid4()
    for scope in (world.template_scope, world.playthrough_scope):
        await put_span(connection, corpus, scope, f"{scope[0]}-plain", sequence=2)
        await put_span(connection, corpus, scope, f"{scope[0]}-hot", sequence=29)
        await put_span(
            connection,
            corpus,
            scope,
            f"{scope[0]}-hidden",
            sequence=1,
            is_hidden=True,
            authored_fact_id=uuid4(),
        )
        await put_span(
            connection,
            corpus,
            scope,
            f"{scope[0]}-conditional",
            sequence=1,
            conditional=True,
            authored_fact_id=uuid4(),
        )
        await put_fact(connection, corpus, scope, f"{scope[0]}-fact")
        await put_fact(
            connection,
            corpus,
            scope,
            f"{scope[0]}-hidden-fact",
            is_hidden=True,
            authored_fact_id=revealed,
        )
        await put_fact(
            connection,
            corpus,
            scope,
            f"{scope[0]}-conditional-fact",
            conditional=True,
            authored_fact_id=active,
        )
    for scope in (world.sibling_scope, world.foreign_scope):
        await put_span(connection, corpus, scope, f"{scope[0]}-foreign", sequence=2)
        await put_fact(connection, corpus, scope, f"{scope[0]}-foreign-fact")


@pytest.mark.parametrize("options", CONTEXT_VARIANTS, ids=str)
async def test_span_lookup_by_id_matches_the_exact_branch_eligibility(
    db_connection: AsyncConnection, options: dict
) -> None:
    corpus = await build_corpus(db_connection)
    await populate(db_connection, corpus)
    ctx = helpers.make_context(corpus.world, **options)

    rows = await span_repo.get_eligible_spans_by_ids(
        db_connection, ctx, list(corpus.span_labels)
    )

    expected = await span_labels_via_exact(db_connection, corpus, ctx)
    assert {corpus.span_labels[row.span_id] for row in rows} == expected
    assert expected


@pytest.mark.parametrize("options", CONTEXT_VARIANTS, ids=str)
async def test_fact_lookup_by_id_matches_the_exact_branch_eligibility(
    db_connection: AsyncConnection, options: dict
) -> None:
    corpus = await build_corpus(db_connection)
    await populate(db_connection, corpus)
    ctx = helpers.make_context(corpus.world, **options)

    rows = await fact_repo.get_eligible_facts_by_ids(
        db_connection, ctx, list(corpus.fact_labels)
    )

    expected = await fact_labels_via_exact(db_connection, corpus, ctx)
    assert {corpus.fact_labels[row.fact_id] for row in rows} == expected
    assert expected


@pytest.mark.parametrize("options", CONTEXT_VARIANTS, ids=str)
async def test_literal_fact_listing_is_eligible_and_excludes_relations(
    db_connection: AsyncConnection, options: dict
) -> None:
    corpus = await build_corpus(db_connection)
    await populate(db_connection, corpus)
    world = corpus.world
    scope = world.playthrough_scope
    literal = await helpers.add_fact(
        db_connection,
        scope,
        corpus.probe_ids[scope],
        "has_scar",
        object_literal="left cheek",
        valid_from_seq=1,
    )
    hidden_literal = await helpers.add_fact(
        db_connection,
        scope,
        corpus.probe_ids[scope],
        "hides",
        object_literal="a key",
        is_hidden=True,
        authored_fact_id=uuid4(),
    )
    ctx = helpers.make_context(world, **options)

    rows = await fact_repo.list_eligible_literal_facts_for_entities(
        db_connection, ctx, corpus.all_probe_ids, 100
    )

    ids = {row.fact_id for row in rows}
    assert all(row.object_entity_id is None for row in rows)
    assert literal.fact_id in ids
    is_hidden_visible = hidden_literal.fact_id in ids
    assert is_hidden_visible == options.get("should_include_hidden", False)


async def test_empty_id_lists_return_nothing(db_connection: AsyncConnection) -> None:
    corpus = await build_corpus(db_connection)
    ctx = helpers.make_context(corpus.world)

    assert await span_repo.get_eligible_spans_by_ids(db_connection, ctx, []) == []
    assert await fact_repo.get_eligible_facts_by_ids(db_connection, ctx, []) == []
    assert await span_repo.get_span_origins(db_connection, ctx, []) == {}
    assert (
        await fact_repo.list_eligible_literal_facts_for_entities(
            db_connection, ctx, [], 5
        )
        == []
    )


async def test_span_origins_cover_eligible_spans_only(
    db_connection: AsyncConnection,
) -> None:
    corpus = await build_corpus(db_connection)
    world = corpus.world
    visible = await put_span(
        db_connection,
        corpus,
        world.template_scope,
        "lore",
        sequence=0,
        source_kind="authored_lore",
    )
    turn = await put_span(
        db_connection, corpus, world.playthrough_scope, "old", sequence=3
    )
    in_window = await put_span(
        db_connection, corpus, world.playthrough_scope, "hot", sequence=29
    )
    hidden = await put_span(
        db_connection,
        corpus,
        world.template_scope,
        "secret",
        sequence=0,
        source_kind="authored_lore",
        is_hidden=True,
        authored_fact_id=uuid4(),
    )
    foreign = await put_span(db_connection, corpus, world.foreign_scope, "alien")
    ctx = helpers.make_context(world)

    origins = await span_repo.get_span_origins(
        db_connection, ctx, [visible, turn, in_window, hidden, foreign]
    )

    assert set(origins) == {visible, turn}
    assert origins[visible].source_kind == "authored_lore"
    assert origins[turn].source_kind == "turn_narration"
    assert origins[turn].actor_participant_id is None


async def add_batch(
    connection: AsyncConnection, playthrough_id, status: ExtractionBatchStatus
) -> None:
    await extraction_batch_repo.create_batch(
        connection,
        ExtractionBatchCreate(
            scope_kind="playthrough",
            scope_id=playthrough_id,
            from_seq=1,
            to_seq=2,
            status=status,
            model="m",
            prompt_version=str(uuid4()),
            input_hash="h",
        ),
    )


async def test_has_failed_batch_is_true_only_for_a_failed_batch_of_that_scope(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    check = extraction_batch_repo.has_failed_batch
    await add_batch(db_connection, world.playthrough_id, "applied")
    await add_batch(db_connection, world.sibling_playthrough_id, "failed")

    assert await check(db_connection, "playthrough", world.playthrough_id) is False

    await add_batch(db_connection, world.playthrough_id, "failed")

    assert await check(db_connection, "playthrough", world.playthrough_id) is True
    assert (
        await check(db_connection, "playthrough", world.foreign_playthrough_id) is False
    )


async def test_read_only_snapshot_rejects_writes_and_reports_repeatable_read(
    migrated_test_database_url: str,
) -> None:
    connection = await AsyncConnection.connect(migrated_test_database_url)
    async with connection, connection.transaction():
        await snapshot_repo.begin_read_only_snapshot(connection)
        cursor = await connection.execute("SHOW transaction_isolation")
        isolation = (await cursor.fetchone())[0]
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            await connection.execute("CREATE TEMP TABLE probe (id int)")
    assert isolation == "repeatable read"
