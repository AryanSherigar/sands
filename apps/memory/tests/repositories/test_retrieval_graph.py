"""Graph branch queries: one hop over eligible relation facts, the hub rule, neighbour
facts and one representative eligible source span per edge."""

from uuid import UUID, uuid4

from app.repositories import fact_repo
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers

HUB_EDGE_CAP = 20


async def _edges(
    connection: AsyncConnection,
    world: helpers.World,
    frontier: list[UUID],
    *,
    player_entity_id: UUID | None = None,
    should_expand_hubs: bool = True,
    **context_options: object,
):
    ctx = helpers.make_context(world, **context_options)  # type: ignore[arg-type]
    return await fact_repo.list_graph_edges(
        connection,
        ctx,
        frontier,
        hub_edge_cap=HUB_EDGE_CAP,
        player_entity_id=player_entity_id,
        should_expand_hubs=should_expand_hubs,
    )


async def _make_star(
    connection: AsyncConnection,
    world: helpers.World,
    hub_id: UUID,
    edge_count: int,
    *,
    first_seq: int = 1,
) -> list[UUID]:
    fact_ids = []
    for index in range(edge_count):
        leaf = await helpers.add_entity(
            connection, world.playthrough_scope, f"Leaf{index}"
        )
        fact = await helpers.add_fact(
            connection,
            world.playthrough_scope,
            hub_id,
            "knows",
            object_entity_id=leaf,
            valid_from_seq=first_seq + index,
        )
        fact_ids.append(fact.fact_id)
    return fact_ids


async def test_chain_hop_one_from_a_gives_a_b_and_frontier_b_gives_b_c(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    a, b, c = [await helpers.add_entity(db_connection, scope, n) for n in "ABC"]
    edge_ab = await helpers.add_fact(
        db_connection, scope, a, "knows", object_entity_id=b, valid_from_seq=1
    )
    edge_bc = await helpers.add_fact(
        db_connection, scope, b, "knows", object_entity_id=c, valid_from_seq=2
    )

    hop_one = await _edges(db_connection, world, [a])
    hop_two = await _edges(db_connection, world, [b])

    assert [edge.fact_id for edge in hop_one.edges] == [edge_ab.fact_id]
    assert hop_one.hub_entity_ids == frozenset()
    assert [edge.fact_id for edge in hop_two.edges] == [
        edge_bc.fact_id,
        edge_ab.fact_id,
    ]
    assert hop_two.edges[0].object_entity_id == c


async def test_edge_touching_two_frontier_entities_is_returned_once(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    a = await helpers.add_entity(db_connection, scope, "A")
    b = await helpers.add_entity(db_connection, scope, "B")
    await helpers.add_fact(db_connection, scope, a, "knows", object_entity_id=b)
    await helpers.add_fact(db_connection, scope, a, "loop", object_entity_id=a)

    result = await _edges(db_connection, world, [a, b])

    assert sorted(edge.predicate for edge in result.edges) == ["knows", "loop"]


async def test_literal_facts_are_not_edges(db_connection: AsyncConnection) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    a = await helpers.add_entity(db_connection, scope, "A")
    await helpers.add_fact(db_connection, scope, a, "age", object_literal="30")

    result = await _edges(db_connection, world, [a])

    assert result.edges == []
    assert result.hub_entity_ids == frozenset()


async def test_entity_with_more_than_the_cap_is_a_hub_and_keeps_its_newest_edges(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    hub = await helpers.add_entity(db_connection, world.playthrough_scope, "Hub")
    fact_ids = await _make_star(db_connection, world, hub, 25)

    result = await _edges(db_connection, world, [hub])

    assert result.hub_entity_ids == frozenset({hub})
    assert [edge.fact_id for edge in result.edges] == fact_ids[:4:-1]
    assert len(result.edges) == HUB_EDGE_CAP


async def test_entity_with_exactly_the_cap_is_not_a_hub(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    hub = await helpers.add_entity(db_connection, world.playthrough_scope, "Busy")
    await _make_star(db_connection, world, hub, HUB_EDGE_CAP)

    result = await _edges(db_connection, world, [hub])

    assert result.hub_entity_ids == frozenset()
    assert len(result.edges) == HUB_EDGE_CAP


async def test_ineligible_edges_do_not_count_toward_the_hub_threshold(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    hub = await helpers.add_entity(db_connection, scope, "Busy")
    await _make_star(db_connection, world, hub, 19)
    for index in range(6):
        leaf = await helpers.add_entity(db_connection, scope, f"Secret{index}")
        await helpers.add_fact(
            db_connection, scope, hub, "hides", object_entity_id=leaf,
            is_hidden=True, authored_fact_id=uuid4(),
        )  # fmt: skip

    result = await _edges(db_connection, world, [hub])

    assert result.hub_entity_ids == frozenset()
    assert len(result.edges) == 19
    assert all(edge.predicate == "knows" for edge in result.edges)


async def test_hub_is_not_expanded_when_expansion_is_disabled(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    hub = await helpers.add_entity(db_connection, scope, "Hub")
    quiet = await helpers.add_entity(db_connection, scope, "Quiet")
    other = await helpers.add_entity(db_connection, scope, "Other")
    await _make_star(db_connection, world, hub, 25)
    quiet_edge = await helpers.add_fact(
        db_connection, scope, quiet, "knows", object_entity_id=other
    )

    result = await _edges(db_connection, world, [hub, quiet], should_expand_hubs=False)

    assert result.hub_entity_ids == frozenset({hub})
    assert [edge.fact_id for edge in result.edges] == [quiet_edge.fact_id]


async def test_player_entity_is_always_a_hub_even_with_one_edge(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    player = await helpers.add_entity(db_connection, scope, "Player", is_player=True)
    other = await helpers.add_entity(db_connection, scope, "Other")
    edge = await helpers.add_fact(
        db_connection, scope, player, "knows", object_entity_id=other
    )

    expanded = await _edges(db_connection, world, [player], player_entity_id=player)
    contained = await _edges(
        db_connection,
        world,
        [player],
        player_entity_id=player,
        should_expand_hubs=False,
    )
    plain = await _edges(db_connection, world, [other])

    assert expanded.hub_entity_ids == frozenset({player})
    assert [row.fact_id for row in expanded.edges] == [edge.fact_id]
    assert contained.hub_entity_ids == frozenset({player})
    assert contained.edges == []
    assert plain.hub_entity_ids == frozenset()


async def test_empty_frontier_returns_nothing(db_connection: AsyncConnection) -> None:
    world = await helpers.build_world(db_connection)

    result = await _edges(db_connection, world, [])

    assert result.edges == []
    assert result.hub_entity_ids == frozenset()


async def test_hidden_unrevealed_edge_is_not_returned_and_is_after_reveal(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.template_scope
    a = await helpers.add_entity(db_connection, scope, "A")
    b = await helpers.add_entity(db_connection, scope, "B")
    secret_id = uuid4()
    edge = await helpers.add_fact(
        db_connection, scope, a, "secretly_serves", object_entity_id=b,
        is_hidden=True, authored_fact_id=secret_id,
    )  # fmt: skip

    hidden = await _edges(db_connection, world, [a])
    revealed = await _edges(db_connection, world, [a], revealed=[secret_id])

    assert hidden.edges == []
    assert [row.fact_id for row in revealed.edges] == [edge.fact_id]


async def test_edge_whose_far_endpoint_is_out_of_scope_is_not_returned(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    a = await helpers.add_entity(db_connection, scope, "A")
    stranger = await helpers.add_entity(db_connection, world.sibling_scope, "Stranger")
    template_entity = await helpers.add_entity(db_connection, world.template_scope, "T")
    await helpers.add_fact(db_connection, scope, a, "knows", object_entity_id=stranger)
    template_edge = await helpers.add_fact(
        db_connection, scope, a, "visits", object_entity_id=template_entity
    )

    result = await _edges(db_connection, world, [a])

    assert [edge.fact_id for edge in result.edges] == [template_edge.fact_id]


async def test_superseded_edge_is_not_returned(db_connection: AsyncConnection) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    a = await helpers.add_entity(db_connection, scope, "A")
    b = await helpers.add_entity(db_connection, scope, "B")
    edge = await helpers.add_fact(db_connection, scope, a, "allied", object_entity_id=b)
    await helpers.supersede_fact(db_connection, world.playthrough_id, edge.fact_id, 10)

    before = await _edges(db_connection, world, [a], at_seq=9)
    after = await _edges(db_connection, world, [a], at_seq=10)

    assert [row.fact_id for row in before.edges] == [edge.fact_id]
    assert after.edges == []


# --- representative source spans ----------------------------------------------


async def _edge_with_sources(connection: AsyncConnection, world: helpers.World) -> UUID:
    scope = world.playthrough_scope
    a = await helpers.add_entity(connection, scope, "A")
    b = await helpers.add_entity(connection, scope, "B")
    edge = await helpers.add_fact(connection, scope, a, "knows", object_entity_id=b)
    return edge.fact_id


async def test_representative_span_is_the_lowest_eligible_sequence(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    edge_id = await _edge_with_sources(db_connection, world)
    in_window = await helpers.add_span(db_connection, scope, text="recent", sequence=29)
    hidden = await helpers.add_span(
        db_connection, scope, text="secret", sequence=1, is_hidden=True
    )
    later = await helpers.add_span(db_connection, scope, text="later", sequence=9)
    earliest = await helpers.add_span(db_connection, scope, text="earliest", sequence=4)
    sibling = await helpers.add_span(
        db_connection, world.sibling_scope, text="other", sequence=2
    )
    for span in (in_window, hidden, later, earliest, sibling):
        await helpers.link_fact_source(db_connection, edge_id, span.span_id)

    spans = await fact_repo.get_representative_source_spans(
        db_connection, helpers.make_context(world), [edge_id]
    )

    assert list(spans) == [edge_id]
    assert spans[edge_id].span_id == earliest.span_id


async def test_representative_span_ties_break_on_lowest_span_id(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    edge_id = await _edge_with_sources(db_connection, world)
    tied = [
        await helpers.add_span(db_connection, scope, text=f"t{i}", sequence=4)
        for i in range(3)
    ]
    for span in tied:
        await helpers.link_fact_source(db_connection, edge_id, span.span_id)

    spans = await fact_repo.get_representative_source_spans(
        db_connection, helpers.make_context(world), [edge_id]
    )

    assert spans[edge_id].span_id == min(span.span_id for span in tied)


async def test_edges_without_an_eligible_source_span_are_absent(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    no_source = await _edge_with_sources(db_connection, world)
    only_recent = await _edge_with_sources(db_connection, world)
    recent = await helpers.add_span(db_connection, scope, text="recent", sequence=29)
    await helpers.link_fact_source(db_connection, only_recent, recent.span_id)
    ok_edge = await _edge_with_sources(db_connection, world)
    ok_span = await helpers.add_span(db_connection, scope, text="ok", sequence=2)
    await helpers.link_fact_source(db_connection, ok_edge, ok_span.span_id)

    spans = await fact_repo.get_representative_source_spans(
        db_connection,
        helpers.make_context(world),
        [no_source, only_recent, ok_edge],
    )

    assert list(spans) == [ok_edge]


async def test_representative_span_for_no_edges_returns_nothing(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)

    spans = await fact_repo.get_representative_source_spans(
        db_connection, helpers.make_context(world), []
    )

    assert spans == {}
