"""Exact and graph branch behaviour below the service: ordering, caps, hubs, and
what each branch collects."""

from uuid import uuid4

from app.services.retrieval_branches import run_exact_branch
from app.services.retrieval_graph import run_graph_branch
from app.services.retrieval_types import CandidatePool
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers
from tests.services.retrieval_service_helpers import (
    add_entity,
    add_fact,
    add_span,
    make_settings,
)


def keys(candidates: list) -> list[tuple[str, int]]:
    return [(candidate.kind, candidate.sequence) for candidate in candidates]


async def test_exact_merges_kinds_by_sequence_descending_and_caps_the_total(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    await add_fact(
        db_connection, scope, mara, "a", object_literal="x", valid_from_seq=4
    )
    await add_fact(
        db_connection, scope, mara, "b", object_literal="x", valid_from_seq=8
    )
    await add_span(
        db_connection,
        scope,
        "s6",
        sequence=6,
        entity_ids=[mara.entity_id],
        is_embedded=False,
    )
    await add_span(
        db_connection,
        scope,
        "s2",
        sequence=2,
        entity_ids=[mara.entity_id],
        is_embedded=False,
    )
    await helpers.add_commitment(
        db_connection, world.playthrough_id, mara.entity_id, opened_seq=7
    )
    ctx = helpers.make_context(world, at_seq=20, window=0)

    uncapped = await run_exact_branch(
        db_connection, ctx, [mara.entity_id], CandidatePool(), make_settings()
    )
    capped = await run_exact_branch(
        db_connection,
        ctx,
        [mara.entity_id],
        CandidatePool(),
        make_settings(branch_candidate_cap=3),
    )

    assert keys(uncapped)[:3] == [("fact", 8), ("commitment", 7), ("span", 6)]
    sequences = [seq for _kind, seq in keys(uncapped)]
    assert sequences == sorted(sequences, reverse=True)
    assert len(capped) == 3
    assert keys(capped) == keys(uncapped)[:3]


async def test_exact_can_leave_spans_out(db_connection: AsyncConnection) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    await add_span(
        db_connection,
        scope,
        "s",
        sequence=2,
        entity_ids=[mara.entity_id],
        is_embedded=False,
    )
    ctx = helpers.make_context(world)

    result = await run_exact_branch(
        db_connection,
        ctx,
        [mara.entity_id],
        CandidatePool(),
        make_settings(),
        should_include_spans=False,
    )

    assert result == []


async def test_exact_includes_recently_resolved_commitments_and_graph_only_open_ones(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    orin = await add_entity(db_connection, scope, "Orin")
    await add_fact(db_connection, scope, mara, "trusts", object_entity=orin)
    open_one = await helpers.add_commitment(
        db_connection, world.playthrough_id, orin.entity_id, opened_seq=3
    )
    done = await helpers.add_commitment(
        db_connection, world.playthrough_id, orin.entity_id, opened_seq=4
    )
    await helpers.add_commitment_status(
        db_connection, done.commitment_id, 6, "fulfilled"
    )
    ctx = helpers.make_context(world, at_seq=10, window=0)
    settings = make_settings()

    exact_pool, graph_pool = CandidatePool(), CandidatePool()
    exact = await run_exact_branch(
        db_connection, ctx, [orin.entity_id], exact_pool, settings
    )
    graph = await run_graph_branch(
        db_connection,
        ctx,
        [mara.entity_id],
        player_entity_id=None,
        pool=graph_pool,
        settings=settings,
    )

    assert {c.item_id for c in exact if c.kind == "commitment"} == {
        open_one.commitment_id,
        done.commitment_id,
    }
    assert {c.item_id for c in graph if c.kind == "commitment"} == {
        open_one.commitment_id
    }


async def test_graph_ranks_hop_one_before_a_newer_hop_two_edge(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    a, b, c = [await add_entity(db_connection, scope, name) for name in "ABC"]
    near = await add_fact(
        db_connection, scope, a, "knows", object_entity=b, valid_from_seq=1
    )
    far = await add_fact(
        db_connection, scope, b, "knows", object_entity=c, valid_from_seq=9
    )
    ctx = helpers.make_context(world)

    ranked = await run_graph_branch(
        db_connection,
        ctx,
        [a.entity_id],
        player_entity_id=None,
        pool=CandidatePool(),
        settings=make_settings(),
        should_include_spans=False,
    )

    assert [candidate.item_id for candidate in ranked] == [near.fact_id, far.fact_id]


async def test_a_seed_hub_keeps_only_its_newest_edges(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    hub = await add_entity(db_connection, scope, "Hub")
    for number in range(25):
        leaf = await add_entity(db_connection, scope, f"Leaf{number}")
        await add_fact(
            db_connection,
            scope,
            hub,
            "hosts",
            object_entity=leaf,
            valid_from_seq=number,
        )
    ctx = helpers.make_context(world)

    ranked = await run_graph_branch(
        db_connection,
        ctx,
        [hub.entity_id],
        player_entity_id=None,
        pool=CandidatePool(),
        settings=make_settings(),
        should_include_spans=False,
    )

    assert len(ranked) == 20
    assert [c.sequence for c in ranked] == list(range(24, 4, -1))


async def test_the_player_as_a_seed_is_a_hub_too(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    player = await add_entity(db_connection, scope, "Hero", is_player=True)
    for number in range(8):
        leaf = await add_entity(db_connection, scope, f"Leaf{number}")
        await add_fact(db_connection, scope, player, "met", object_entity=leaf)
    ctx = helpers.make_context(world)
    pool = CandidatePool()

    ranked = await run_graph_branch(
        db_connection,
        ctx,
        [player.entity_id],
        player_entity_id=player.entity_id,
        pool=pool,
        settings=make_settings(hub_edge_cap=3),
        should_include_spans=False,
    )

    assert len(ranked) == 3


async def test_graph_adds_one_eligible_representative_span_per_edge(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    a, b = [await add_entity(db_connection, scope, name) for name in "AB"]
    edge = await add_fact(db_connection, scope, a, "knows", object_entity=b)
    visible = await add_span(
        db_connection, scope, "proof one", sequence=2, is_embedded=False
    )
    hidden = await add_span(
        db_connection,
        world.template_scope,
        "secret proof",
        sequence=0,
        is_hidden=True,
        authored_fact_id=uuid4(),
        source_kind="authored_lore",
        is_embedded=False,
    )
    await helpers.link_fact_source(db_connection, edge.fact_id, hidden.span_id)
    await helpers.link_fact_source(db_connection, edge.fact_id, visible.span_id)
    ctx = helpers.make_context(world)

    ranked = await run_graph_branch(
        db_connection,
        ctx,
        [a.entity_id],
        player_entity_id=None,
        pool=CandidatePool(),
        settings=make_settings(),
    )

    span_ids = [c.item_id for c in ranked if c.kind == "span"]
    assert span_ids == [visible.span_id]


async def test_graph_without_seeds_returns_nothing(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    ctx = helpers.make_context(world)

    ranked = await run_graph_branch(
        db_connection,
        ctx,
        [],
        player_entity_id=None,
        pool=CandidatePool(),
        settings=make_settings(),
    )

    assert ranked == []
