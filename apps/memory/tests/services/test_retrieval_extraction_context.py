"""extraction_context(): exact and graph branches only, hidden authored facts
included, bounded by a token cap."""

from uuid import uuid4

import pytest
from app.exceptions.ingest_exceptions import PlaythroughNotRegisteredError
from app.services.packing import estimate_tokens
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.repositories import helpers_retrieval as helpers
from tests.repositories.helpers_retrieval import World
from tests.services.retrieval_service_helpers import (
    FakeQueryEmbedder,
    add_entity,
    add_fact,
    add_span,
    build_service,
)

CHARS_PER_TOKEN = 3


async def test_hidden_authored_facts_are_included_but_conditional_ones_are_not(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.template_scope
    moon = await add_entity(db_connection, scope, "Moonstone", authored_id=uuid4())
    await add_fact(
        db_connection,
        scope,
        moon,
        "is",
        object_literal="cursed",
        is_hidden=True,
        authored_fact_id=uuid4(),
    )
    await add_fact(
        db_connection,
        scope,
        moon,
        "glows",
        object_literal="blue",
        conditional=True,
        authored_fact_id=uuid4(),
    )
    await add_fact(db_connection, scope, moon, "weighs", object_literal="a pound")
    await db_connection.commit()
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    context = await service.extraction_context(
        retrieval_world.playthrough_id, [moon.entity_id], 5
    )

    assert sorted(context.lines) == ["Moonstone is cursed", "Moonstone weighs a pound"]
    assert context.truncated is False
    assert moon.entity_id in context.entity_ids


async def test_the_same_hidden_fact_is_absent_from_retrieve_until_revealed(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    from tests.services.retrieval_service_helpers import make_request

    scope = retrieval_world.template_scope
    moon = await add_entity(db_connection, scope, "Moonstone", authored_id=uuid4())
    await add_fact(
        db_connection,
        scope,
        moon,
        "is",
        object_literal="cursed",
        is_hidden=True,
        authored_fact_id=uuid4(),
    )
    await db_connection.commit()
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    response = await service.retrieve(make_request(retrieval_world, "Moonstone"))
    context = await service.extraction_context(
        retrieval_world.playthrough_id, [moon.entity_id], 5
    )

    assert response.items == []
    assert context.lines == ["Moonstone is cursed"]


async def test_facts_are_read_at_the_requested_sequence(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    mara = await add_entity(db_connection, world.playthrough_scope, "Mara")
    await add_fact(
        db_connection,
        world.playthrough_scope,
        mara,
        "arrives",
        object_literal="late",
        valid_from_seq=20,
    )
    replaced = await add_fact(
        db_connection, world.playthrough_scope, mara, "lives_in", object_literal="Vale"
    )
    await helpers.supersede_fact(
        db_connection, world.playthrough_id, replaced.fact_id, 20
    )
    await db_connection.commit()
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    async def lines_at(at_seq: int) -> list[str]:
        result = await service.extraction_context(
            world.playthrough_id, [mara.entity_id], at_seq
        )
        return sorted(result.lines)

    assert await lines_at(15) == ["Mara lives in Vale"]
    assert await lines_at(25) == ["Mara arrives late"]


async def test_spans_are_not_part_of_the_extraction_context(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    other = await add_entity(db_connection, scope, "Orin")
    fact = await add_fact(db_connection, scope, mara, "knows", object_entity=other)
    await add_span(
        db_connection,
        scope,
        "Mara talks to Orin",
        sequence=5,
        entity_ids=[mara.entity_id],
    )
    await helpers.link_fact_source(
        db_connection,
        fact.fact_id,
        (await add_span(db_connection, scope, "proof of knowing", sequence=2)).span_id,
    )
    await db_connection.commit()
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    context = await service.extraction_context(
        retrieval_world.playthrough_id, [mara.entity_id], 10
    )

    assert context.lines == ["Mara knows Orin"]


async def test_one_hop_neighbour_facts_join_the_context(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    orin = await add_entity(db_connection, scope, "Orin")
    await add_fact(db_connection, scope, mara, "trusts", object_entity=orin)
    await add_fact(db_connection, scope, orin, "wears", object_literal="a ring")
    await db_connection.commit()
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    context = await service.extraction_context(
        retrieval_world.playthrough_id, [mara.entity_id], 10
    )

    assert sorted(context.lines) == ["Mara trusts Orin", "Orin wears a ring"]
    assert set(context.entity_ids) == {mara.entity_id, orin.entity_id}


async def add_ten_facts(connection: AsyncConnection, world: World):
    mara = await add_entity(connection, world.playthrough_scope, "Mara")
    for number in range(10):
        await add_fact(
            connection,
            world.playthrough_scope,
            mara,
            f"trait{number}",
            object_literal="x" * 25,
            valid_from_seq=number,
        )
    await connection.commit()
    return mara


async def test_the_cap_bounds_the_output_and_flags_truncation(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    mara = await add_ten_facts(db_connection, retrieval_world)
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    small = await service.extraction_context(
        retrieval_world.playthrough_id, [mara.entity_id], 20, token_cap=30
    )
    large = await service.extraction_context(
        retrieval_world.playthrough_id, [mara.entity_id], 20, token_cap=500
    )

    used = sum(estimate_tokens(line, CHARS_PER_TOKEN) for line in small.lines)
    assert small.truncated is True
    assert used == small.token_count <= 30
    assert 0 < len(small.lines) < 10
    assert large.truncated is False
    assert len(large.lines) == 10


async def test_exact_and_graph_items_may_fill_the_whole_extraction_cap(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    mara = await add_ten_facts(db_connection, retrieval_world)
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    context = await service.extraction_context(
        retrieval_world.playthrough_id, [mara.entity_id], 20, token_cap=200
    )

    assert len(context.lines) == 10
    assert context.truncated is False
    assert context.token_count > 0.4 * 200


async def test_the_default_cap_comes_from_settings(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    mara = await add_ten_facts(db_connection, retrieval_world)
    service = build_service(
        retrieval_pool, FakeQueryEmbedder(), extraction_context_tokens=30
    )

    context = await service.extraction_context(
        retrieval_world.playthrough_id, [mara.entity_id], 20
    )

    assert context.truncated is True
    assert context.token_count <= 30


async def test_seeds_and_facts_of_other_scopes_never_leak(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    own = await add_entity(db_connection, world.playthrough_scope, "Mara")
    await add_fact(
        db_connection, world.playthrough_scope, own, "is", object_literal="mine"
    )
    alien = await add_entity(db_connection, world.sibling_scope, "Mara")
    await add_fact(
        db_connection, world.sibling_scope, alien, "is", object_literal="theirs"
    )
    await db_connection.commit()
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    context = await service.extraction_context(
        world.playthrough_id, [own.entity_id, alien.entity_id, uuid4()], 10
    )

    assert context.lines == ["Mara is mine"]
    assert context.entity_ids == [own.entity_id]


async def test_no_seeds_gives_an_empty_untruncated_context(
    retrieval_pool: AsyncConnectionPool, retrieval_world: World
) -> None:
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    context = await service.extraction_context(retrieval_world.playthrough_id, [], 10)

    assert (context.lines, context.entity_ids) == ([], [])
    assert (context.token_count, context.truncated) == (0, False)


async def test_an_unregistered_playthrough_raises_not_registered(
    retrieval_pool: AsyncConnectionPool, retrieval_world: World
) -> None:
    service = build_service(retrieval_pool, FakeQueryEmbedder())

    with pytest.raises(PlaythroughNotRegisteredError):
        await service.extraction_context(uuid4(), [uuid4()], 10)
