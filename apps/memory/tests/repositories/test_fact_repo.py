"""fact_repo against a real Postgres: validity at N, overlay supersession, scope
isolation, relation edges and idempotent child-row inserts."""

from dataclasses import dataclass
from uuid import UUID

from app.models.common import ScopeKind
from app.models.facts import FactCreate, FactRow, FactSourceCreate
from app.repositories import fact_repo
from psycopg import AsyncConnection
from tests.repositories.helpers_facts import (
    COUNT_FACT_SOURCES_FOR_FACT,
    COUNT_FACTS_BY_ID,
    COUNT_SUPERSESSIONS_FOR_FACT,
    PLAYTHROUGH_SCOPE,
    TEMPLATE_SCOPE,
    count_rows,
    delete_playthrough,
    insert_entity,
    insert_playthrough,
    insert_span,
    insert_template,
    make_fact,
    make_supersession,
)

FACT_VALID_FROM = 10
SUPERSESSION_AT = 20
OVERLAY_SUPERSESSION_AT = 5
OVERLAY_CHECKED_SEQUENCES = (0, 4, 5, 6, 50)
WINDOW_EXPECTATIONS = ((9, False), (15, True), (20, False), (25, False))
RELATION_EXPECTATIONS = (
    (SUPERSESSION_AT - 1, True),
    (SUPERSESSION_AT, False),
    (SUPERSESSION_AT + 1, False),
)


@dataclass(frozen=True)
class World:
    template_id: UUID
    playthrough_id: UUID
    mira_id: UUID
    guild_id: UUID


async def _make_world(connection: AsyncConnection) -> World:
    template_id = await insert_template(connection)
    playthrough_id = await insert_playthrough(connection, template_id)
    mira_id = await insert_entity(connection, TEMPLATE_SCOPE, template_id, "Mira")
    guild_id = await insert_entity(connection, TEMPLATE_SCOPE, template_id, "Red Guild")
    return World(template_id, playthrough_id, mira_id, guild_id)


async def _create_one(connection: AsyncConnection, fact: FactCreate) -> FactRow:
    rows = await fact_repo.create_facts(connection, [fact])
    return rows[0]


async def _template_attribute(
    connection: AsyncConnection, world: World, literal: str
) -> FactRow:
    fact = make_fact(
        TEMPLATE_SCOPE, world.template_id, world.mira_id, "rank", object_literal=literal
    )
    return await _create_one(connection, fact)


async def _template_edge(connection: AsyncConnection, world: World) -> FactRow:
    fact = make_fact(
        TEMPLATE_SCOPE,
        world.template_id,
        world.mira_id,
        "member_of",
        object_entity_id=world.guild_id,
    )
    return await _create_one(connection, fact)


async def _playthrough_location(
    connection: AsyncConnection, world: World, literal: str, valid_from_seq: int
) -> FactRow:
    fact = make_fact(
        PLAYTHROUGH_SCOPE,
        world.playthrough_id,
        world.mira_id,
        "located_in",
        object_literal=literal,
        valid_from_seq=valid_from_seq,
    )
    return await _create_one(connection, fact)


async def _supersede(
    connection: AsyncConnection,
    playthrough_id: UUID,
    fact_id: UUID,
    at_seq: int,
    superseding_fact_id: UUID | None = None,
) -> None:
    row = make_supersession(playthrough_id, fact_id, at_seq, superseding_fact_id)
    await fact_repo.add_supersessions(connection, [row])


def _ids(rows: list[FactRow]) -> set[UUID]:
    return {row.fact_id for row in rows}


async def _valid_ids_at(
    connection: AsyncConnection,
    playthrough_id: UUID,
    template_id: UUID | None,
    at_seq: int,
) -> set[UUID]:
    rows = await fact_repo.list_valid_facts_at(
        connection, playthrough_id, template_id, at_seq
    )
    return _ids(rows)


async def _world_valid_ids_at(
    connection: AsyncConnection, world: World, at_seq: int
) -> set[UUID]:
    return await _valid_ids_at(
        connection, world.playthrough_id, world.template_id, at_seq
    )


async def test_create_facts_returns_rows_in_input_order(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    facts = [
        make_fact(TEMPLATE_SCOPE, world.template_id, world.mira_id, "is_a"),
        make_fact(
            TEMPLATE_SCOPE,
            world.template_id,
            world.mira_id,
            "member_of",
            object_entity_id=world.guild_id,
        ),
    ]

    rows = await fact_repo.create_facts(db_connection, facts)

    assert [row.predicate for row in rows] == ["is_a", "member_of"]
    assert rows[1].object_entity_id == world.guild_id
    assert await fact_repo.create_facts(db_connection, []) == []


async def test_supersession_bounds_validity_window(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    fact = await _playthrough_location(
        db_connection, world, "the docks", FACT_VALID_FROM
    )
    await _supersede(db_connection, world.playthrough_id, fact.fact_id, SUPERSESSION_AT)

    for at_seq, is_expected in WINDOW_EXPECTATIONS:
        valid_ids = await _world_valid_ids_at(db_connection, world, at_seq)
        assert (fact.fact_id in valid_ids) == is_expected


async def test_template_fact_superseded_in_one_playthrough_stays_valid_in_another(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    other_playthrough_id = await insert_playthrough(db_connection, world.template_id)
    fact = await _template_edge(db_connection, world)
    await _supersede(
        db_connection, world.playthrough_id, fact.fact_id, OVERLAY_SUPERSESSION_AT
    )

    for at_seq in OVERLAY_CHECKED_SEQUENCES:
        other_ids = await _valid_ids_at(
            db_connection, other_playthrough_id, world.template_id, at_seq
        )
        first_ids = await _world_valid_ids_at(db_connection, world, at_seq)
        assert fact.fact_id in other_ids
        assert (fact.fact_id in first_ids) == (at_seq < OVERLAY_SUPERSESSION_AT)


async def test_authored_chain_at_seq_zero_hides_fact_from_turn_zero(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    other_playthrough_id = await insert_playthrough(db_connection, world.template_id)
    old_fact = await _template_attribute(db_connection, world, "apprentice")
    new_fact = await _template_attribute(db_connection, world, "master")
    await _supersede(
        db_connection, world.playthrough_id, old_fact.fact_id, 0, new_fact.fact_id
    )

    other_ids = await _valid_ids_at(
        db_connection, other_playthrough_id, world.template_id, 0
    )
    assert await _world_valid_ids_at(db_connection, world, 0) == {new_fact.fact_id}
    assert other_ids == {old_fact.fact_id, new_fact.fact_id}


async def test_superseding_fact_replaces_predecessor_at_same_sequence(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    predecessor = await _playthrough_location(
        db_connection, world, "the docks", FACT_VALID_FROM
    )
    successor = await _playthrough_location(
        db_connection, world, "the keep", SUPERSESSION_AT
    )
    await _supersede(
        db_connection,
        world.playthrough_id,
        predecessor.fact_id,
        SUPERSESSION_AT,
        successor.fact_id,
    )

    before = await _world_valid_ids_at(db_connection, world, SUPERSESSION_AT - 1)
    at_supersession = await _world_valid_ids_at(db_connection, world, SUPERSESSION_AT)
    assert before == {predecessor.fact_id}
    assert at_supersession == {successor.fact_id}


async def _seed_scope_edge(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> FactRow:
    subject_id = await insert_entity(connection, scope_kind, scope_id, "Mira")
    object_id = await insert_entity(connection, scope_kind, scope_id, "Red Guild")
    fact = make_fact(
        scope_kind, scope_id, subject_id, "member_of", object_entity_id=object_id
    )
    return await _create_one(connection, fact)


async def test_scope_isolation_across_templates_and_playthroughs(
    db_connection: AsyncConnection,
) -> None:
    first_template_id = await insert_template(db_connection)
    second_template_id = await insert_template(db_connection)
    first_playthrough_id = await insert_playthrough(db_connection, first_template_id)
    second_playthrough_id = await insert_playthrough(db_connection, second_template_id)
    template_fact = await _seed_scope_edge(
        db_connection, TEMPLATE_SCOPE, first_template_id
    )
    await _seed_scope_edge(db_connection, TEMPLATE_SCOPE, second_template_id)
    playthrough_fact = await _seed_scope_edge(
        db_connection, PLAYTHROUGH_SCOPE, first_playthrough_id
    )
    await _seed_scope_edge(db_connection, PLAYTHROUGH_SCOPE, second_playthrough_id)

    scoped = await _valid_ids_at(
        db_connection, first_playthrough_id, first_template_id, 0
    )
    template_missing = await _valid_ids_at(db_connection, first_playthrough_id, None, 0)

    assert scoped == {template_fact.fact_id, playthrough_fact.fact_id}
    assert template_missing == {playthrough_fact.fact_id}


async def test_scope_isolation_for_relations(db_connection: AsyncConnection) -> None:
    first_template_id = await insert_template(db_connection)
    second_template_id = await insert_template(db_connection)
    playthrough_id = await insert_playthrough(db_connection, first_template_id)
    own_fact = await _seed_scope_edge(db_connection, TEMPLATE_SCOPE, first_template_id)
    foreign_fact = await _seed_scope_edge(
        db_connection, TEMPLATE_SCOPE, second_template_id
    )
    entity_ids = [own_fact.subject_entity_id, foreign_fact.subject_entity_id]

    rows = await fact_repo.list_valid_relations_at(
        db_connection, playthrough_id, first_template_id, 0, entity_ids
    )

    assert _ids(rows) == {own_fact.fact_id}


async def test_list_valid_facts_filters_by_subject(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    mira_fact = await _template_attribute(db_connection, world, "smith")
    guild_fact = make_fact(
        TEMPLATE_SCOPE,
        world.template_id,
        world.guild_id,
        "is_a",
        object_literal="guild",
    )
    await _create_one(db_connection, guild_fact)

    rows = await fact_repo.list_valid_facts_at(
        db_connection,
        world.playthrough_id,
        world.template_id,
        0,
        subject_entity_ids=[world.mira_id],
    )

    assert _ids(rows) == {mira_fact.fact_id}
    assert rows[0].is_hidden is False
    assert rows[0].conditional is False


async def test_relations_are_entity_edges_in_both_directions(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    edge = await _template_edge(db_connection, world)
    await _template_attribute(db_connection, world, "Red Guild smith")

    by_subject = await fact_repo.list_valid_relations_at(
        db_connection, world.playthrough_id, world.template_id, 0, [world.mira_id]
    )
    by_object = await fact_repo.list_valid_relations_at(
        db_connection, world.playthrough_id, world.template_id, 0, [world.guild_id]
    )

    assert _ids(by_subject) == {edge.fact_id}
    assert _ids(by_object) == {edge.fact_id}


async def test_superseded_relation_disappears_from_supersession_onwards(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    edge = await _template_edge(db_connection, world)
    await _supersede(db_connection, world.playthrough_id, edge.fact_id, SUPERSESSION_AT)

    for at_seq, is_expected in RELATION_EXPECTATIONS:
        rows = await fact_repo.list_valid_relations_at(
            db_connection,
            world.playthrough_id,
            world.template_id,
            at_seq,
            [world.guild_id],
        )
        assert (edge.fact_id in _ids(rows)) == is_expected


async def test_add_supersessions_is_idempotent(db_connection: AsyncConnection) -> None:
    world = await _make_world(db_connection)
    fact = await _template_attribute(db_connection, world, "apprentice")
    supersession = make_supersession(
        world.playthrough_id, fact.fact_id, SUPERSESSION_AT
    )

    first = await fact_repo.add_supersessions(db_connection, [supersession])
    second = await fact_repo.add_supersessions(db_connection, [supersession])

    assert len(first) == 1
    assert second[0].supersession_id == first[0].supersession_id
    count = await count_rows(db_connection, COUNT_SUPERSESSIONS_FOR_FACT, fact.fact_id)
    assert count == 1
    assert await fact_repo.add_supersessions(db_connection, []) == []


async def test_add_fact_sources_is_idempotent(db_connection: AsyncConnection) -> None:
    world = await _make_world(db_connection)
    fact = await _template_edge(db_connection, world)
    span_id = await insert_span(db_connection, TEMPLATE_SCOPE, world.template_id)
    link = FactSourceCreate(fact_id=fact.fact_id, span_id=span_id)

    await fact_repo.add_fact_sources(db_connection, [link])
    await fact_repo.add_fact_sources(db_connection, [link])

    count = await count_rows(db_connection, COUNT_FACT_SOURCES_FOR_FACT, fact.fact_id)
    assert count == 1
    sources = await fact_repo.get_fact_sources(db_connection, [fact.fact_id])
    assert sources == {fact.fact_id: [span_id]}


async def test_list_valid_facts_filters_by_predicate(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    rank_fact = await _template_attribute(db_connection, world, "smith")
    edge_fact = await _template_edge(db_connection, world)

    rows = await fact_repo.list_valid_facts_at(
        db_connection, world.playthrough_id, world.template_id, 0, predicate="rank"
    )

    assert _ids(rows) == {rank_fact.fact_id}
    assert edge_fact.fact_id not in _ids(rows)


async def test_list_valid_facts_filters_by_subject_and_predicate(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    mira_rank = await _template_attribute(db_connection, world, "smith")
    guild_fact = make_fact(
        TEMPLATE_SCOPE,
        world.template_id,
        world.guild_id,
        "rank",
        object_literal="guild-rank",
    )
    await _create_one(db_connection, guild_fact)

    rows = await fact_repo.list_valid_facts_at(
        db_connection,
        world.playthrough_id,
        world.template_id,
        0,
        subject_entity_ids=[world.mira_id],
        predicate="rank",
    )

    assert _ids(rows) == {mira_rank.fact_id}


async def test_list_accepted_facts_after_filters_authority_subject_predicate_and_seq(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    accepted_after = make_fact(
        PLAYTHROUGH_SCOPE,
        world.playthrough_id,
        world.mira_id,
        "mood",
        object_literal="wary",
        valid_from_seq=15,
        authority="accepted",
    )
    accepted_before = make_fact(
        PLAYTHROUGH_SCOPE,
        world.playthrough_id,
        world.mira_id,
        "mood",
        object_literal="calm",
        valid_from_seq=5,
        authority="accepted",
    )
    extracted_after = make_fact(
        PLAYTHROUGH_SCOPE,
        world.playthrough_id,
        world.mira_id,
        "mood",
        object_literal="tense",
        valid_from_seq=20,
        authority="extracted",
    )
    other_predicate = make_fact(
        PLAYTHROUGH_SCOPE,
        world.playthrough_id,
        world.mira_id,
        "location",
        object_literal="the docks",
        valid_from_seq=25,
        authority="accepted",
    )
    for fact in (accepted_after, accepted_before, extracted_after, other_predicate):
        await _create_one(db_connection, fact)

    rows = await fact_repo.list_accepted_facts_after(
        db_connection, world.playthrough_id, world.mira_id, "mood", 10
    )

    assert [row.object_literal for row in rows] == ["wary"]


async def test_list_accepted_facts_after_orders_by_valid_from_seq_asc(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    later = make_fact(
        PLAYTHROUGH_SCOPE,
        world.playthrough_id,
        world.mira_id,
        "mood",
        object_literal="later",
        valid_from_seq=30,
        authority="accepted",
    )
    earlier = make_fact(
        PLAYTHROUGH_SCOPE,
        world.playthrough_id,
        world.mira_id,
        "mood",
        object_literal="earlier",
        valid_from_seq=11,
        authority="accepted",
    )
    await _create_one(db_connection, later)
    await _create_one(db_connection, earlier)

    rows = await fact_repo.list_accepted_facts_after(
        db_connection, world.playthrough_id, world.mira_id, "mood", 10
    )

    assert [row.object_literal for row in rows] == ["earlier", "later"]


async def test_deleting_playthrough_cascades_supersessions_only(
    db_connection: AsyncConnection,
) -> None:
    world = await _make_world(db_connection)
    fact = await _template_attribute(db_connection, world, "apprentice")
    await _supersede(db_connection, world.playthrough_id, fact.fact_id, SUPERSESSION_AT)

    await delete_playthrough(db_connection, world.playthrough_id)

    supersessions = await count_rows(
        db_connection, COUNT_SUPERSESSIONS_FOR_FACT, fact.fact_id
    )
    assert supersessions == 0
    assert await count_rows(db_connection, COUNT_FACTS_BY_ID, fact.fact_id) == 1
