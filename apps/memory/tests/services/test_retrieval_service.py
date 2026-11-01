"""retrieve() end to end on a real database: eligibility, branches, fusion, packing
and the response shape. The query embedder is a deterministic fake."""

from uuid import uuid4

from app.models.facts import CommitmentStatusCreate
from app.repositories import commitment_repo
from app.services.packing import estimate_tokens
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.repositories import helpers_retrieval as helpers
from tests.repositories.helpers_retrieval import World
from tests.services.retrieval_service_helpers import (
    FakeQueryEmbedder,
    add_entity,
    add_fact,
    add_scene,
    add_span,
    build_service,
    make_request,
    texts_of,
)

CHARS_PER_TOKEN = 3


async def retrieve(pool: AsyncConnectionPool, request, **overrides):
    service = build_service(pool, FakeQueryEmbedder(), **overrides)
    return await service.retrieve(request)


# --- eligibility, end to end ---------------------------------------------------


async def test_hidden_fact_and_span_named_by_the_action_text_wait_for_the_reveal(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.template_scope
    secret = uuid4()
    moon = await add_entity(db_connection, scope, "Moonstone", authored_id=uuid4())
    await add_fact(
        db_connection,
        scope,
        moon,
        "is",
        object_literal="cursed",
        is_hidden=True,
        authored_fact_id=secret,
        is_embedded=True,
    )
    await add_span(
        db_connection,
        scope,
        "Moonstone",
        sequence=0,
        entity_ids=[moon.entity_id],
        source_kind="authored_fact_text",
        is_hidden=True,
        authored_fact_id=secret,
    )
    await db_connection.commit()

    before = await retrieve(retrieval_pool, make_request(retrieval_world, "Moonstone"))
    after = await retrieve(
        retrieval_pool,
        make_request(retrieval_world, "Moonstone", revealed_fact_ids=[secret]),
    )

    assert before.items == []
    assert sorted(texts_of(after.items)) == ["Moonstone", "Moonstone is cursed"]
    assert {item.kind for item in after.items} == {"span", "fact"}


async def test_conditional_items_appear_only_when_listed_active(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.template_scope
    condition = uuid4()
    lamp = await add_entity(db_connection, scope, "Lamp", authored_id=uuid4())
    await add_fact(
        db_connection,
        scope,
        lamp,
        "glows",
        object_literal="blue",
        conditional=True,
        authored_fact_id=condition,
    )
    await add_span(
        db_connection,
        scope,
        "Lamp glows",
        sequence=0,
        entity_ids=[lamp.entity_id],
        conditional=True,
        authored_fact_id=condition,
    )
    await db_connection.commit()

    inactive = await retrieve(retrieval_pool, make_request(retrieval_world, "Lamp"))
    active = await retrieve(
        retrieval_pool,
        make_request(retrieval_world, "Lamp", active_conditional_fact_ids=[condition]),
    )

    assert inactive.items == []
    assert len(active.items) == 2


async def test_fact_superseded_at_20_is_absent_at_25_and_present_at_15(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    mara = await add_entity(db_connection, world.playthrough_scope, "Mara")
    fact = await add_fact(
        db_connection, world.playthrough_scope, mara, "lives_in", object_literal="Vale"
    )
    await helpers.supersede_fact(db_connection, world.playthrough_id, fact.fact_id, 20)
    await db_connection.commit()

    at_25 = await retrieve(retrieval_pool, make_request(world, "Mara", sequence=25))
    at_15 = await retrieve(retrieval_pool, make_request(world, "Mara", sequence=15))

    assert at_25.items == []
    assert texts_of(at_15.items) == ["Mara lives in Vale"]


async def test_spans_inside_the_recent_window_are_excluded_and_the_boundary_kept(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    mara = await add_entity(db_connection, world.playthrough_scope, "Mara")
    for sequence in (23, 24, 25, 30):
        await add_span(
            db_connection,
            world.playthrough_scope,
            f"Mara at turn {sequence}",
            sequence=sequence,
            entity_ids=[mara.entity_id],
        )
    await db_connection.commit()

    default_window = await retrieve(retrieval_pool, make_request(world, "Mara"))
    no_window = await retrieve(
        retrieval_pool, make_request(world, "Mara", recent_window_turns=0)
    )
    settings_window = await retrieve(
        retrieval_pool, make_request(world, "Mara"), recent_window_turns=3
    )

    assert sorted(item.sequence for item in default_window.items) == [23, 24]
    assert sorted(item.sequence for item in no_window.items) == [23, 24, 25, 30]
    assert sorted(item.sequence for item in settings_window.items) == [23, 24, 25]


async def test_same_named_entities_of_other_playthroughs_and_templates_never_leak(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    leaked: set = set()
    allowed: set = set()
    for scope, bucket in (
        (world.playthrough_scope, allowed),
        (world.sibling_scope, leaked),
        (world.foreign_scope, leaked),
    ):
        mara = await add_entity(db_connection, scope, "Mara")
        span = await add_span(
            db_connection,
            scope,
            "Mara waits by the well",
            sequence=2,
            entity_ids=[mara.entity_id],
        )
        fact = await add_fact(
            db_connection,
            scope,
            mara,
            "waits_at",
            object_literal="the well",
            is_embedded=True,
        )
        commitment = await helpers.add_commitment(
            db_connection, scope[1], mara.entity_id, opened_seq=3
        )
        bucket.update({span.span_id, fact.fact_id, commitment.commitment_id})
    await db_connection.commit()

    response = await retrieve(
        retrieval_pool, make_request(world, "Mara waits by the well")
    )

    returned = {item.item_id for item in response.items}
    assert returned & allowed == allowed
    assert not returned & leaked
    assert len(response.items) == 3


async def test_a_playthrough_without_a_template_gets_playthrough_scope_only(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    orphan = await helpers.make_playthrough(db_connection, template_id=None)
    template_mara = await add_entity(db_connection, world.template_scope, "Mara")
    await add_fact(
        db_connection, world.template_scope, template_mara, "is", object_literal="lore"
    )
    orphan_scope = ("playthrough", orphan.playthrough_id)
    own_mara = await add_entity(db_connection, orphan_scope, "Mara")
    await add_fact(db_connection, orphan_scope, own_mara, "is", object_literal="mine")
    await db_connection.commit()
    request = make_request(world, "Mara", playthrough_id=orphan.playthrough_id)

    response = await retrieve(retrieval_pool, request)

    assert texts_of(response.items) == ["Mara is mine"]
    assert response.degraded_reasons == ["template_missing"]


# --- branches and fusion -------------------------------------------------------


async def test_graph_only_candidates_are_returned_when_hop_one_is_sparse(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.playthrough_scope
    alpha, bravo, charlie = [
        await add_entity(db_connection, scope, name)
        for name in ("Alpha", "Bravo", "Charlie")
    ]
    await add_fact(
        db_connection, scope, alpha, "knows", object_entity=bravo, valid_from_seq=1
    )
    await add_fact(
        db_connection, scope, bravo, "trusts", object_entity=charlie, valid_from_seq=2
    )
    await add_fact(
        db_connection,
        scope,
        charlie,
        "carries",
        object_literal="a lantern",
        valid_from_seq=3,
    )
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(retrieval_world, "Alpha"))

    branches = {item.text: item.branches for item in response.items}
    assert branches["Alpha knows Bravo"] == ["exact", "graph"]
    assert branches["Bravo trusts Charlie"] == ["graph"]
    assert branches["Charlie carries a lantern"] == ["graph"]


async def test_no_second_hop_when_hop_one_is_dense(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.playthrough_scope
    alpha = await add_entity(db_connection, scope, "Alpha")
    neighbours = [await add_entity(db_connection, scope, f"Near{n}") for n in range(5)]
    for neighbour in neighbours:
        await add_fact(db_connection, scope, alpha, "knows", object_entity=neighbour)
    far = await add_entity(db_connection, scope, "Far")
    await add_fact(db_connection, scope, neighbours[0], "trusts", object_entity=far)
    await add_fact(
        db_connection, scope, neighbours[0], "wears", object_literal="a cloak"
    )
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(retrieval_world, "Alpha"))

    texts = texts_of(response.items)
    assert "Near0 trusts Far" not in texts
    assert "Near0 wears a cloak" in texts


async def test_the_player_entity_never_expands_as_a_neighbour(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    scope = world.playthrough_scope
    alpha = await add_entity(db_connection, scope, "Alpha")
    player = await add_entity(db_connection, scope, "Hero", is_player=True)
    friend = await add_entity(db_connection, scope, "Friend")
    await add_fact(db_connection, scope, alpha, "serves", object_entity=player)
    await add_fact(db_connection, scope, player, "befriends", object_entity=friend)
    await add_fact(db_connection, scope, player, "wears", object_literal="armor")
    await db_connection.execute(
        "UPDATE memory_playthrough SET player_entity_id = %s WHERE playthrough_id = %s",
        (player.entity_id, world.playthrough_id),
    )
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(world, "Alpha"))

    assert texts_of(response.items) == ["Alpha serves Hero"]


async def test_a_crowded_neighbour_never_expands(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.playthrough_scope
    alpha = await add_entity(db_connection, scope, "Alpha")
    crowd = await add_entity(db_connection, scope, "Crowd")
    await add_fact(db_connection, scope, alpha, "sees", object_entity=crowd)
    for number in range(25):
        member = await add_entity(db_connection, scope, f"Member{number}")
        await add_fact(db_connection, scope, crowd, "hosts", object_entity=member)
    await add_fact(db_connection, scope, crowd, "smells", object_literal="of smoke")
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(retrieval_world, "Alpha"))

    assert texts_of(response.items) == ["Alpha sees Crowd"]


async def test_bm25_and_vector_return_spans_by_content_and_carry_their_branches(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.playthrough_scope
    await add_span(
        db_connection, scope, "the lantern flickers in the cellar", sequence=2
    )
    await add_span(db_connection, scope, "birds sing over the meadow", sequence=3)
    await db_connection.commit()

    response = await retrieve(
        retrieval_pool,
        make_request(retrieval_world, "the lantern flickers in the cellar"),
    )

    top = next(i for i in response.items if "lantern" in i.text)
    assert top.branches == ["bm25", "vector"]
    assert top.authority == "accepted"
    assert top.source_kind == "turn_narration"


async def test_vector_only_candidates_beyond_rank_20_are_dropped(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.playthrough_scope
    for number in range(30):
        await add_span(db_connection, scope, f"filler{number} words", sequence=1)
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(retrieval_world, "zzqq"))

    assert len(response.items) == 20
    assert all(item.branches == ["vector"] for item in response.items)


async def test_identical_text_from_two_sources_stays_as_two_items(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    first = await add_span(
        db_connection, scope, "Mara smiles", sequence=2, entity_ids=[mara.entity_id]
    )
    second = await add_span(
        db_connection, scope, "Mara smiles", sequence=3, entity_ids=[mara.entity_id]
    )
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(retrieval_world, "Mara"))

    assert [item.item_id for item in response.items] == [first.span_id, second.span_id]


async def test_the_exact_branch_is_capped_at_forty_candidates(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
    captured_logs: list[dict[str, object]],
) -> None:
    scope = retrieval_world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    for number in range(50):
        await add_span(
            db_connection,
            scope,
            f"note {number}",
            sequence=1 + number % 20,
            entity_ids=[mara.entity_id],
            is_embedded=False,
        )
    await db_connection.commit()

    response = await retrieve(
        retrieval_pool, make_request(retrieval_world, "Mara"), recall_budget_tokens=4000
    )

    logged = next(e for e in captured_logs if e["event"] == "retrieve_completed")
    assert logged["branch_counts"]["exact"] == 40
    assert len(response.items) == 40


# --- budget ----------------------------------------------------------------------


async def test_output_never_exceeds_the_budget_and_refills_after_eligibility(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    scope = world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    for number in range(40):
        await add_span(
            db_connection,
            scope,
            f"Mara story part {number} " + "words " * 25,
            sequence=1 + number % 10,
            entity_ids=[mara.entity_id],
            is_embedded=False,
        )
    await db_connection.commit()
    request = make_request(world, "Mara story", recall_budget_tokens=200)
    baseline = await retrieve(retrieval_pool, request)

    for number in range(30):
        await add_span(
            db_connection,
            world.template_scope,
            f"Mara story secret {number} " + "words " * 25,
            sequence=0,
            entity_ids=[mara.entity_id],
            is_hidden=True,
            authored_fact_id=uuid4(),
            source_kind="authored_lore",
            is_embedded=False,
        )
    await db_connection.commit()
    with_decoys = await retrieve(retrieval_pool, request)

    used = sum(estimate_tokens(i.text, CHARS_PER_TOKEN) for i in baseline.items)
    assert 0 < used <= 200
    assert {i.item_id for i in with_decoys.items} == {i.item_id for i in baseline.items}


async def test_the_request_budget_overrides_the_setting_and_none_falls_back(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    scope = world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    for number in range(20):
        await add_span(
            db_connection,
            scope,
            f"Mara line {number} " + "x" * 90,
            sequence=1,
            entity_ids=[mara.entity_id],
            is_embedded=False,
        )
    await db_connection.commit()

    setting_default = await retrieve(
        retrieval_pool, make_request(world, "Mara"), recall_budget_tokens=250
    )
    explicit = await retrieve(
        retrieval_pool,
        make_request(world, "Mara", recall_budget_tokens=500),
        recall_budget_tokens=250,
    )

    def used(response) -> int:
        return sum(estimate_tokens(i.text, CHARS_PER_TOKEN) for i in response.items)

    assert used(setting_default) <= 250
    assert 250 < used(explicit) <= 500


# --- commitments, grouping and response ------------------------------------------


async def add_resolved_commitment(
    connection: AsyncConnection,
    world: World,
    evidence_span_id,
    status: str = "fulfilled",
):
    scope = world.playthrough_scope
    mara = await add_entity(connection, scope, "Mara")
    orin = await add_entity(connection, scope, "Orin")
    commitment = await helpers.add_commitment(
        connection,
        world.playthrough_id,
        mara.entity_id,
        counterparty_entity_id=orin.entity_id,
        opened_seq=5,
        summary="to bring the key",
    )
    await commitment_repo.append_commitment_status(
        connection,
        CommitmentStatusCreate(
            commitment_id=commitment.commitment_id,
            at_seq=12,
            status=status,
            evidence_span_id=evidence_span_id,
        ),
    )
    return commitment


async def test_a_commitment_is_returned_with_its_fulfilled_status_and_eligible_label(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    evidence = await add_span(
        db_connection, world.playthrough_scope, "Mara hands over the key", sequence=12
    )
    await add_resolved_commitment(db_connection, world, evidence.span_id)
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(world, "Mara"))

    commitment = next(i for i in response.items if i.kind == "commitment")
    assert commitment.text == (
        f"Mara promised Orin: to bring the key — fulfilled (turn 12) [{evidence.label}]"
    )
    assert commitment.authority == "extracted"
    assert commitment.sequence == 12


async def test_an_in_window_or_hidden_evidence_label_is_never_shown(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    in_window = await add_span(
        db_connection, world.playthrough_scope, "recent proof", sequence=29
    )
    hidden = await add_span(
        db_connection,
        world.template_scope,
        "secret proof",
        sequence=0,
        source_kind="authored_lore",
        is_hidden=True,
        authored_fact_id=uuid4(),
    )
    await add_resolved_commitment(db_connection, world, in_window.span_id)
    await add_resolved_commitment(db_connection, world, hidden.span_id, status="broken")
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(world, "Mara and Orin"))

    lines = [i.text for i in response.items if i.kind == "commitment"]
    assert len(lines) == 2
    assert all("[" not in line for line in lines)
    assert any("fulfilled (turn 12)" in line for line in lines)
    assert any("broken (turn 12)" in line for line in lines)


async def test_items_are_grouped_by_seed_entity_and_chronological_within_a_group(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    scope = retrieval_world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    orin = await add_entity(db_connection, scope, "Orin")
    for sequence, entity in ((9, mara), (3, orin), (5, mara), (1, orin)):
        await add_span(
            db_connection,
            scope,
            f"{entity.canonical_name} at {sequence}",
            sequence=sequence,
            entity_ids=[entity.entity_id],
            is_embedded=False,
        )
    await db_connection.commit()

    response = await retrieve(
        retrieval_pool, make_request(retrieval_world, "Mara Orin")
    )

    assert texts_of(response.items) == [
        "Mara at 5",
        "Mara at 9",
        "Orin at 1",
        "Orin at 3",
    ]


async def test_response_carries_seeds_scene_watermarks_and_model(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    authored = uuid4()
    mara = await add_entity(
        db_connection, world.template_scope, "Mara", authored_id=authored
    )
    tavern = await add_entity(db_connection, world.playthrough_scope, "Tavern")
    await add_scene(
        db_connection,
        world.playthrough_id,
        4,
        location=tavern.entity_id,
        present=[mara.entity_id],
    )
    await db_connection.execute(
        "UPDATE memory_playthrough SET ingested_seq = 28, indexed_seq = 27, "
        "extracted_seq = 20, latest_seq_seen = 30 WHERE playthrough_id = %s",
        (world.playthrough_id,),
    )
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(world, "Mara"))

    seeds = {seed.name: seed for seed in response.active_entities}
    assert list(seeds) == ["Mara", "Tavern"]
    assert seeds["Mara"].authored_entity_id == authored
    assert seeds["Mara"].entity_id == mara.entity_id
    assert seeds["Mara"].provenance == "authored"
    assert all(seed.brief is None for seed in response.active_entities)
    assert seeds["Tavern"].authored_entity_id is None
    assert response.scene is not None
    assert response.scene.location_entity_id == tavern.entity_id
    assert response.scene.present_entity_ids == [mara.entity_id]
    assert response.watermarks.model_dump() == {
        "ingested_seq": 28,
        "indexed_seq": 27,
        "extracted_seq": 20,
        "latest_seq_seen": 30,
    }
    assert response.embedding_model == "model-a"
    assert response.skipped_branches == []


async def test_speaker_comes_from_participant_names(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    from tests.services.retrieval_service_helpers import add_actor_span

    world = retrieval_world
    known, unknown = uuid4(), uuid4()
    scope = world.playthrough_scope
    mara = await add_entity(db_connection, scope, "Mara")
    await add_actor_span(
        db_connection, scope, "Mara says hi", 2, known, [mara.entity_id]
    )
    await add_actor_span(
        db_connection, scope, "Mara waves", 3, unknown, [mara.entity_id]
    )
    await db_connection.commit()

    response = await retrieve(
        retrieval_pool, make_request(world, "Mara", participant_names={known: "Aria"})
    )

    speakers = {i.text: i.speaker for i in response.items}
    assert speakers == {"Mara says hi": "Aria", "Mara waves": None}


async def test_authored_spans_report_authored_authority(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    world = retrieval_world
    await add_span(
        db_connection,
        world.template_scope,
        "The keep stands on a cliff",
        sequence=0,
        source_kind="authored_lore",
    )
    await db_connection.commit()

    response = await retrieve(
        retrieval_pool, make_request(world, "The keep stands on a cliff")
    )

    assert [(i.authority, i.source_kind) for i in response.items] == [
        ("authored", "authored_lore")
    ]


async def test_degraded_reasons_are_reported_in_the_response(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    retrieval_world: World,
) -> None:
    from tests.services.retrieval_service_helpers import add_batch

    world = retrieval_world
    await add_batch(db_connection, world.playthrough_id, "failed")
    await db_connection.execute(
        "UPDATE memory_playthrough SET indexed_seq = 0, latest_seq_seen = 30 "
        "WHERE playthrough_id = %s",
        (world.playthrough_id,),
    )
    await db_connection.commit()

    response = await retrieve(retrieval_pool, make_request(world, "anything"))

    assert response.degraded_reasons == ["extraction_failed", "indexing_lag"]
