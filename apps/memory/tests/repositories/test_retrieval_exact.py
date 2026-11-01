"""Exact-match retrieval: spans by entity_ids overlap and facts by subject/object."""

from uuid import uuid4

from app.repositories import fact_repo, span_repo
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers

SEED_COUNT_LIMIT = 3


async def test_exact_spans_are_ordered_newest_first_with_span_id_tiebreak(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    entity_id = await helpers.add_entity(db_connection, scope, "Mira")
    older = await helpers.add_span(
        db_connection, scope, text="old", sequence=3, entity_ids=[entity_id]
    )
    tied = [
        await helpers.add_span(
            db_connection, scope, text=f"tie {i}", sequence=8, entity_ids=[entity_id]
        )
        for i in range(3)
    ]

    rows = await span_repo.list_exact_spans(
        db_connection, helpers.make_context(world), [entity_id], 10
    )

    expected_ties = sorted((row.span_id for row in tied), reverse=True)
    assert [row.span_id for row in rows] == [*expected_ties, older.span_id]


async def test_exact_spans_match_only_seed_entities_and_respect_the_limit(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    mira = await helpers.add_entity(db_connection, scope, "Mira")
    bram = await helpers.add_entity(db_connection, scope, "Bram")
    for sequence in range(1, 6):
        await helpers.add_span(
            db_connection, scope, text="m", sequence=sequence, entity_ids=[mira]
        )
    await helpers.add_span(
        db_connection, scope, text="b", sequence=2, entity_ids=[bram]
    )
    await helpers.add_span(db_connection, scope, text="untagged", sequence=2)
    ctx = helpers.make_context(world)

    limited = await span_repo.list_exact_spans(db_connection, ctx, [mira], 2)
    both = await span_repo.list_exact_spans(db_connection, ctx, [mira, bram], 50)

    assert [row.sequence for row in limited] == [5, 4]
    assert {row.text for row in both} == {"m", "b"}
    assert len(both) == 6


async def test_exact_spans_refill_the_limit_after_eligibility(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    entity_id = await helpers.add_entity(db_connection, scope, "Mira")
    for sequence in range(1, 4):
        await helpers.add_span(
            db_connection,
            scope,
            text=f"kept {sequence}",
            sequence=sequence,
            entity_ids=[entity_id],
        )
    for sequence in range(25, 29):
        await helpers.add_span(
            db_connection,
            scope,
            text=f"in window {sequence}",
            sequence=sequence,
            entity_ids=[entity_id],
        )
    await helpers.add_span(
        db_connection,
        scope,
        text="hidden newest",
        sequence=1,
        is_hidden=True,
        entity_ids=[entity_id],
    )

    rows = await span_repo.list_exact_spans(
        db_connection, helpers.make_context(world), [entity_id], SEED_COUNT_LIMIT
    )

    assert [row.text for row in rows] == ["kept 3", "kept 2", "kept 1"]


async def test_exact_queries_with_no_seeds_or_no_limit_return_nothing(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    entity_id = await helpers.add_entity(db_connection, scope, "Mira")
    await helpers.add_span(
        db_connection, scope, text="m", sequence=1, entity_ids=[entity_id]
    )
    await helpers.add_fact(db_connection, scope, entity_id, "is", object_literal="x")
    ctx = helpers.make_context(world)

    assert await span_repo.list_exact_spans(db_connection, ctx, [], 5) == []
    assert await span_repo.list_exact_spans(db_connection, ctx, [entity_id], 0) == []
    facts = fact_repo.list_eligible_facts_for_entities
    assert await facts(db_connection, ctx, [], 5) == []
    assert await facts(db_connection, ctx, [entity_id], 0) == []


async def test_exact_facts_match_subject_or_object_and_include_literal_facts(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    mira = await helpers.add_entity(db_connection, scope, "Mira")
    bram = await helpers.add_entity(db_connection, scope, "Bram")
    cara = await helpers.add_entity(db_connection, scope, "Cara")
    await helpers.add_fact(db_connection, scope, mira, "age", object_literal="30")
    await helpers.add_fact(db_connection, scope, bram, "knows", object_entity_id=mira)
    await helpers.add_fact(db_connection, scope, cara, "age", object_literal="9")

    rows = await fact_repo.list_eligible_facts_for_entities(
        db_connection, helpers.make_context(world), [mira], 10
    )

    assert {row.predicate for row in rows} == {"age", "knows"}
    assert {row.subject_entity_id for row in rows} == {mira, bram}


async def test_exact_facts_are_ordered_newest_first_with_fact_id_tiebreak(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    mira = await helpers.add_entity(db_connection, scope, "Mira")
    older = await helpers.add_fact(
        db_connection, scope, mira, "old", object_literal="x", valid_from_seq=2
    )
    tied = [
        await helpers.add_fact(
            db_connection, scope, mira, f"tie{i}", object_literal="x", valid_from_seq=9
        )
        for i in range(3)
    ]
    ctx = helpers.make_context(world)

    rows = await fact_repo.list_eligible_facts_for_entities(
        db_connection, ctx, [mira], 10
    )
    limited = await fact_repo.list_eligible_facts_for_entities(
        db_connection, ctx, [mira], 2
    )

    expected_ties = sorted((row.fact_id for row in tied), reverse=True)
    assert [row.fact_id for row in rows] == [*expected_ties, older.fact_id]
    assert [row.fact_id for row in limited] == expected_ties[:2]


async def test_exact_facts_refill_the_limit_after_eligibility(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    mira = await helpers.add_entity(db_connection, scope, "Mira")
    for index in range(3):
        await helpers.add_fact(
            db_connection,
            scope,
            mira,
            f"kept{index}",
            object_literal="x",
            valid_from_seq=index,
        )
    for index in range(4):
        await helpers.add_fact(
            db_connection,
            scope,
            mira,
            f"hidden{index}",
            object_literal="x",
            valid_from_seq=20 + index,
            is_hidden=True,
            authored_fact_id=uuid4(),
        )

    rows = await fact_repo.list_eligible_facts_for_entities(
        db_connection, helpers.make_context(world), [mira], SEED_COUNT_LIMIT
    )

    assert [row.predicate for row in rows] == ["kept2", "kept1", "kept0"]
