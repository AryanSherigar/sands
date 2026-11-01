"""Vector search: exact cosine scan over eligible span and fact embeddings."""

import math
from uuid import uuid4

from app.repositories import embedding_repo
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers

MODEL_B = ("model-b", "v1")
MODEL_B_DIM = 5
QUERY = [1.0, 0.0, 0.0]


async def _search(
    connection: AsyncConnection,
    world: helpers.World,
    limit: int = 20,
    **context_options: object,
):
    ctx = helpers.make_context(world, **context_options)  # type: ignore[arg-type]
    return await embedding_repo.search_eligible_embeddings(
        connection, ctx, *helpers.DEFAULT_MODEL, QUERY, limit
    )


async def test_vector_hits_are_ordered_by_cosine_distance_then_target_id(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await helpers.register_model(db_connection)
    scope = world.playthrough_scope
    near = await helpers.add_span(db_connection, scope, text="near", sequence=1)
    middle = await helpers.add_span(db_connection, scope, text="middle", sequence=1)
    far = await helpers.add_span(db_connection, scope, text="far", sequence=1)
    tied = [
        await helpers.add_span(db_connection, scope, text=f"tie{i}", sequence=1)
        for i in range(2)
    ]
    await helpers.add_embedding(db_connection, "span", near.span_id, scope, [1, 0, 0])
    await helpers.add_embedding(db_connection, "span", middle.span_id, scope, [1, 1, 0])
    await helpers.add_embedding(db_connection, "span", far.span_id, scope, [0, 1, 0])
    for span in tied:
        await helpers.add_embedding(
            db_connection, "span", span.span_id, scope, [1, 2, 0]
        )

    hits = await _search(db_connection, world)

    tie_ids = sorted(span.span_id for span in tied)
    assert [hit.target_id for hit in hits] == [
        near.span_id,
        middle.span_id,
        *tie_ids,
        far.span_id,
    ]
    assert hits[0].distance == 0
    assert math.isclose(hits[1].distance, 1 - 1 / math.sqrt(2))
    assert math.isclose(hits[-1].distance, 1.0)
    assert {hit.target_kind for hit in hits} == {"span"}


async def test_vector_limit_applies_after_eligibility_and_refills(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await helpers.register_model(db_connection)
    scope = world.playthrough_scope
    for _ in range(3):
        hidden = await helpers.add_span(
            db_connection, scope, text="secret", sequence=1, is_hidden=True,
            authored_fact_id=uuid4(),
        )  # fmt: skip
        await helpers.add_embedding(
            db_connection, "span", hidden.span_id, scope, [1, 0, 0]
        )
        inside = await helpers.add_span(
            db_connection, scope, text="recent", sequence=29
        )
        await helpers.add_embedding(
            db_connection, "span", inside.span_id, scope, [1, 0, 0]
        )
    eligible_ids = []
    for index in range(3):
        span = await helpers.add_span(db_connection, scope, text="old", sequence=1)
        await helpers.add_embedding(
            db_connection, "span", span.span_id, scope, [1, 0.1 * (index + 1), 0]
        )
        eligible_ids.append(span.span_id)

    hits = await _search(db_connection, world, limit=3)

    assert [hit.target_id for hit in hits] == eligible_ids


async def test_vector_search_returns_span_and_fact_targets(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await helpers.register_model(db_connection)
    scope = world.playthrough_scope
    mira = await helpers.add_entity(db_connection, scope, "Mira")
    span = await helpers.add_span(db_connection, scope, text="old", sequence=1)
    fact = await helpers.add_fact(db_connection, scope, mira, "age", object_literal="3")
    await helpers.add_embedding(db_connection, "span", span.span_id, scope, [1, 0, 0])
    await helpers.add_embedding(db_connection, "fact", fact.fact_id, scope, [1, 1, 0])

    hits = await _search(db_connection, world)

    assert [(hit.target_kind, hit.target_id) for hit in hits] == [
        ("span", span.span_id),
        ("fact", fact.fact_id),
    ]


async def test_vector_search_ignores_embeddings_of_a_model_with_another_dimension(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await helpers.register_model(db_connection)
    await helpers.register_model(db_connection, MODEL_B, MODEL_B_DIM)
    scope = world.playthrough_scope
    mira = await helpers.add_entity(db_connection, scope, "Mira")
    span = await helpers.add_span(db_connection, scope, text="old", sequence=1)
    fact = await helpers.add_fact(db_connection, scope, mira, "age", object_literal="3")
    for kind, target_id in (("span", span.span_id), ("fact", fact.fact_id)):
        await helpers.add_embedding(db_connection, kind, target_id, scope, [1, 0, 0])
        await helpers.add_embedding(
            db_connection, kind, target_id, scope, [1, 0, 0, 0, 1], model=MODEL_B
        )

    hits_a = await _search(db_connection, world)
    hits_b = await embedding_repo.search_eligible_embeddings(
        db_connection,
        helpers.make_context(world),
        *MODEL_B,
        [1.0, 0.0, 0.0, 0.0, 1.0],
        20,
    )

    assert {hit.target_id for hit in hits_a} == {span.span_id, fact.fact_id}
    assert {hit.target_id for hit in hits_b} == {span.span_id, fact.fact_id}
    assert len(hits_a) == len(hits_b) == 2


async def test_vector_search_with_a_query_of_the_wrong_dimension_finds_nothing(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await helpers.register_model(db_connection)
    span = await helpers.add_span(
        db_connection, world.playthrough_scope, text="old", sequence=1
    )
    await helpers.add_embedding(
        db_connection, "span", span.span_id, world.playthrough_scope, [1, 0, 0]
    )

    hits = await embedding_repo.search_eligible_embeddings(
        db_connection,
        helpers.make_context(world),
        *helpers.DEFAULT_MODEL,
        [1.0, 0.0],
        20,
    )

    assert hits == []


async def test_vector_search_of_an_unknown_model_or_empty_query_returns_nothing(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await helpers.register_model(db_connection)
    span = await helpers.add_span(
        db_connection, world.playthrough_scope, text="old", sequence=1
    )
    await helpers.add_embedding(
        db_connection, "span", span.span_id, world.playthrough_scope, [1, 0, 0]
    )
    ctx = helpers.make_context(world)

    unknown = await embedding_repo.search_eligible_embeddings(
        db_connection, ctx, "nope", "v9", QUERY, 20
    )
    empty = await embedding_repo.search_eligible_embeddings(
        db_connection, ctx, *helpers.DEFAULT_MODEL, [], 20
    )
    no_limit = await _search(db_connection, world, limit=0)

    assert unknown == []
    assert empty == []
    assert no_limit == []


async def test_vector_search_excludes_embeddings_whose_own_scope_is_foreign(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    await helpers.register_model(db_connection)
    span = await helpers.add_span(
        db_connection, world.playthrough_scope, text="old", sequence=1
    )
    await helpers.add_embedding(
        db_connection, "span", span.span_id, world.sibling_scope, [1, 0, 0]
    )

    assert await _search(db_connection, world) == []
