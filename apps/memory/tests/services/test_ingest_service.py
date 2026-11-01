"""ingest_service against a real Postgres: registration, turn evidence, accepted
facts and supersession, watermarks, idempotency and whole-batch rollback."""

from uuid import UUID, uuid4

import pytest
import structlog
from app.exceptions.ingest_exceptions import (
    IngestBatchTooLargeError,
    IngestContentConflictError,
    IngestOrderError,
    PlaythroughNotRegisteredError,
)
from app.logging import configure_logging
from app.models.ingest import (
    IngestRequest,
    IngestResponse,
    RejectedCall,
    SetupFactPayload,
    TurnItem,
)
from app.repositories import (
    entity_repo,
    event_repo,
    fact_repo,
    playthrough_repo,
    source_repo,
    span_repo,
)
from app.services.ingest_service import IngestService
from psycopg import AsyncConnection
from tests.services.ingest_helpers import (
    INITIAL_RANK,
    TemplateWorld,
    TurnSpec,
    add_template_alias,
    build_request,
    count_rows,
    create_template_entity,
    flush_item,
    mutation,
    player_payload,
    register_item,
    seed_template_world,
    turn_item,
)

CUSTOM_PLAYER_NAME = "Kestrel"
CANARY = "canary-prose-must-never-be-logged"
OVERSIZED_BATCH = 51
LATE_EARLY_SEQ = 2
LATE_LATER_SEQ = 3


async def _ingest(
    connection: AsyncConnection, request: IngestRequest
) -> IngestResponse:
    return await IngestService(connection).ingest_items(request)


async def _register(
    connection: AsyncConnection, world: TemplateWorld, playthrough_id: UUID
) -> IngestResponse:
    player = player_payload(world.player_authored_id, CUSTOM_PLAYER_NAME)
    item = register_item(world.scenario_id, player=player)
    return await _ingest(connection, build_request(playthrough_id, item))


async def _valid_literals(
    connection: AsyncConnection,
    world: TemplateWorld,
    playthrough_id: UUID,
    at_seq: int,
) -> list[str | None]:
    facts = await fact_repo.list_valid_facts_at(
        connection,
        playthrough_id,
        world.template_id,
        at_seq,
        subject_entity_ids=[world.mira_entity_id],
        predicate="rank",
    )
    return [fact.object_literal for fact in facts]


def _rank_turn(world: TemplateWorld, sequence: int, rank: str) -> TurnItem:
    key = f"{world.mira_authored_id}.rank"
    return turn_item(TurnSpec(sequence, narration="x", deltas=[mutation(key, rank)]))


async def test_register_with_template_adds_playthrough_alias_to_template_player(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    response = await _register(db_connection, world, playthrough_id)
    row = await playthrough_repo.get_playthrough(db_connection, playthrough_id)
    assert row is not None
    assert row.template_id == world.template_id
    assert row.player_entity_id == world.player_entity_id
    assert response.items[0].outcome == "applied"
    aliases = await entity_repo.list_aliases_in_scopes(
        db_connection, [("playthrough", playthrough_id)]
    )
    assert aliases == [("kestrel", world.player_entity_id)]


async def test_two_playthroughs_with_same_custom_name_both_get_alias(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    first, second = uuid4(), uuid4()
    await _register(db_connection, world, first)
    await _register(db_connection, world, second)
    for playthrough_id in (first, second):
        aliases = await entity_repo.list_aliases_in_scopes(
            db_connection, [("playthrough", playthrough_id)]
        )
        assert aliases == [("kestrel", world.player_entity_id)]


async def test_register_without_template_creates_playthrough_player(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id, player_authored_id = uuid4(), uuid4()
    player = player_payload(player_authored_id, CUSTOM_PLAYER_NAME, ["Kes"])
    item = register_item(uuid4(), player=player)
    await _ingest(db_connection, build_request(playthrough_id, item))
    row = await playthrough_repo.get_playthrough(db_connection, playthrough_id)
    assert row is not None and row.template_id is None
    scope = [("playthrough", playthrough_id)]
    entities = await entity_repo.get_entities(db_connection, scope)
    assert [entity.entity_id for entity in entities] == [row.player_entity_id]
    assert entities[0].is_player and entities[0].provenance == "authored"
    assert entities[0].authored_entity_id == player_authored_id
    aliases = await entity_repo.list_aliases_in_scopes(db_connection, scope)
    assert sorted(alias for alias, _ in aliases) == ["kes", "kestrel"]


async def test_setup_facts_are_accepted_at_zero_with_setup_spans(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    facts = [
        SetupFactPayload(
            fact_id=uuid4(),
            subject_entity_id=world.mira_authored_id,
            predicate="trusts",
            object_entity_id=world.player_authored_id,
        ),
        SetupFactPayload(
            fact_id=uuid4(),
            subject_entity_id=world.mira_authored_id,
            predicate="mood",
            object_literal="wary",
        ),
    ]
    player = player_payload(world.player_authored_id, CUSTOM_PLAYER_NAME)
    item = register_item(world.scenario_id, player=player, setup_facts=facts)
    await _ingest(db_connection, build_request(playthrough_id, item))
    await _assert_setup_facts(db_connection, world, playthrough_id)


async def _assert_setup_facts(
    connection: AsyncConnection, world: TemplateWorld, playthrough_id: UUID
) -> None:
    valid = await fact_repo.list_valid_facts_at(
        connection, playthrough_id, world.template_id, 0
    )
    setup = [fact for fact in valid if fact.scope_kind == "playthrough"]
    assert len(setup) == 2
    assert all(fact.authority == "accepted" for fact in setup)
    assert all(
        fact.assertion == "occurred" and fact.valid_from_seq == 0 for fact in setup
    )
    trusts = next(fact for fact in setup if fact.predicate == "trusts")
    assert trusts.object_entity_id == world.player_entity_id
    spans = await span_repo.list_spans_by_labels(
        connection, "playthrough", playthrough_id, ["S0.1", "S0.2"]
    )
    assert {span.label: span.text for span in spans} == {
        "S0.1": f"Mira trusts {CUSTOM_PLAYER_NAME}",
        "S0.2": "Mira mood wary",
    }
    links = await fact_repo.get_fact_sources(connection, [f.fact_id for f in setup])
    linked = {span_id for span_ids in links.values() for span_id in span_ids}
    assert linked == {span.span_id for span in spans}


async def test_unresolvable_setup_fact_is_dropped(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    orphan = SetupFactPayload(
        fact_id=uuid4(),
        subject_entity_id=uuid4(),
        predicate="mood",
        object_literal="calm",
    )
    item = register_item(world.scenario_id, setup_facts=[orphan])
    response = await _ingest(db_connection, build_request(playthrough_id, item))
    assert response.items[0].outcome == "applied"
    valid = await fact_repo.list_valid_facts_at(
        db_connection, playthrough_id, world.template_id, 0
    )
    assert all(fact.scope_kind == "template" for fact in valid)


async def test_redelivery_is_a_noop(db_connection: AsyncConnection) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    player = player_payload(world.player_authored_id, CUSTOM_PLAYER_NAME)
    spec = TurnSpec(
        1,
        narration="Mira salutes.",
        action="I wave.",
        deltas=[mutation(f"{world.mira_authored_id}.rank", "major")],
        rejected=[RejectedCall(tool_name="set_state")],
    )
    request = build_request(
        playthrough_id,
        register_item(world.scenario_id, player=player),
        turn_item(spec),
        flush_item(1),
    )
    first = await _ingest(db_connection, request)
    counts = await count_rows(db_connection)
    second = await _ingest(db_connection, request)
    assert [item.outcome for item in first.items] == ["applied"] * 3
    assert [item.outcome for item in second.items] == ["duplicate"] * 3
    assert await count_rows(db_connection) == counts
    assert second.ingested_seq == first.ingested_seq == 1


async def test_out_of_order_turns_advance_ingested_seq_contiguously(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    observed: list[tuple[int, int]] = []
    for sequence in (1, 3, 2):
        item = turn_item(TurnSpec(sequence, narration=f"turn {sequence}"))
        response = await _ingest(db_connection, build_request(playthrough_id, item))
        observed.append((response.ingested_seq, response.latest_seq_seen))
    assert observed == [(1, 1), (1, 3), (3, 3)]


async def test_rejected_calls_become_rejected_mutation_events(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    rejected = [
        RejectedCall(tool_name="set_state", arguments={"hp": 99}),
        RejectedCall(tool_name="give_item", result={"error": "unknown item"}),
    ]
    item = turn_item(TurnSpec(1, narration="No.", rejected=rejected))
    await _ingest(db_connection, build_request(playthrough_id, item))
    events = await event_repo.list_events(db_connection, playthrough_id, 1, 1)
    by_key = {event.event_key: event for event in events}
    assert set(by_key) == {"rejected:0", "rejected:1"}
    assert all(event.event_kind == "rejected_mutation" for event in events)
    assert not any(event.is_accepted for event in events)
    assert by_key["rejected:1"].payload["tool_name"] == "give_item"
    assert by_key["rejected:0"].payload["arguments"] == {"hp": 99}


async def test_entity_attribute_mutation_supersedes_authored_fact(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    await _ingest(
        db_connection, build_request(playthrough_id, _rank_turn(world, 1, "major"))
    )
    before = await _valid_literals(db_connection, world, playthrough_id, 0)
    after = await _valid_literals(db_connection, world, playthrough_id, 1)
    assert before == [f'"{INITIAL_RANK}"']
    assert after == ['"major"']
    facts = await fact_repo.list_valid_facts_at(
        db_connection, playthrough_id, world.template_id, 1, predicate="rank"
    )
    events = await event_repo.list_events(db_connection, playthrough_id, 1, 1)
    assert facts[0].authority == "accepted" and facts[0].scope_kind == "playthrough"
    assert facts[0].event_id == events[0].event_id


async def test_player_path_and_unknown_entity_are_events_only(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    facts_before = (await count_rows(db_connection))["memory_fact"]
    deltas = [
        mutation("player.hp", 7),
        mutation(f"{uuid4()}.rank", "ghost"),
        mutation("flags.door_open", True),
    ]
    item = turn_item(TurnSpec(1, narration="x", deltas=deltas))
    await _ingest(db_connection, build_request(playthrough_id, item))
    events = await event_repo.list_events(db_connection, playthrough_id, 1, 1)
    assert len(events) == len(deltas)
    assert all(event.is_accepted for event in events)
    assert (await count_rows(db_connection))["memory_fact"] == facts_before


async def test_noop_value_creates_no_fact(db_connection: AsyncConnection) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    counts_before = await count_rows(db_connection)
    item = _rank_turn(world, 1, INITIAL_RANK)
    await _ingest(db_connection, build_request(playthrough_id, item))
    counts_after = await count_rows(db_connection)
    assert counts_after["memory_event"] == counts_before["memory_event"] + 1
    assert counts_after["memory_fact"] == counts_before["memory_fact"]
    assert counts_after["memory_supersession"] == 0


async def test_late_arrival_keeps_validity_correct(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    later = _rank_turn(world, LATE_LATER_SEQ, "admiral")
    earlier = _rank_turn(world, LATE_EARLY_SEQ, "commodore")
    await _ingest(db_connection, build_request(playthrough_id, later))
    await _ingest(db_connection, build_request(playthrough_id, earlier))
    expected = {
        LATE_EARLY_SEQ - 1: [f'"{INITIAL_RANK}"'],
        LATE_EARLY_SEQ: ['"commodore"'],
        LATE_LATER_SEQ: ['"admiral"'],
    }
    for at_seq, literals in expected.items():
        assert (
            await _valid_literals(db_connection, world, playthrough_id, at_seq)
            == literals
        )


async def test_overlay_supersession_is_isolated_per_playthrough(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    first, second = uuid4(), uuid4()
    await _register(db_connection, world, first)
    await _register(db_connection, world, second)
    await _ingest(db_connection, build_request(first, _rank_turn(world, 1, "major")))
    assert await _valid_literals(db_connection, world, first, 1) == ['"major"']
    assert await _valid_literals(db_connection, world, second, 1) == [
        f'"{INITIAL_RANK}"'
    ]


async def test_turn_before_register_raises_and_writes_nothing(
    db_connection: AsyncConnection,
) -> None:
    counts = await count_rows(db_connection)
    request = build_request(uuid4(), turn_item(TurnSpec(1, narration="x")))
    with pytest.raises(PlaythroughNotRegisteredError):
        await _ingest(db_connection, request)
    with pytest.raises(PlaythroughNotRegisteredError):
        await _ingest(db_connection, build_request(uuid4(), flush_item(1)))
    assert await count_rows(db_connection) == counts


async def test_content_conflict_rolls_back_whole_batch(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    original = TurnSpec(2, narration="The gate holds.")
    await _ingest(db_connection, build_request(playthrough_id, turn_item(original)))
    counts = await count_rows(db_connection)
    conflicting = TurnSpec(2, narration="The gate falls.", turn_id=original.turn_id)
    request = build_request(
        playthrough_id,
        turn_item(TurnSpec(1, narration="An earlier turn.")),
        turn_item(conflicting),
    )
    with pytest.raises(IngestContentConflictError):
        await _ingest(db_connection, request)
    assert await count_rows(db_connection) == counts


async def test_replay_dropping_stored_action_is_content_conflict(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    original = TurnSpec(1, narration="The gate holds.", action="Open the gate.")
    await _ingest(db_connection, build_request(playthrough_id, turn_item(original)))
    replay = TurnSpec(1, narration="The gate holds.", turn_id=original.turn_id)
    with pytest.raises(IngestContentConflictError):
        await _ingest(db_connection, build_request(playthrough_id, turn_item(replay)))


async def test_flush_sets_watermark_and_redelivery_is_duplicate(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    first = await _ingest(db_connection, build_request(playthrough_id, flush_item(4)))
    second = await _ingest(db_connection, build_request(playthrough_id, flush_item(4)))
    row = await playthrough_repo.get_playthrough(db_connection, playthrough_id)
    assert row is not None and row.flush_requested_through_seq == 4
    assert first.items[0].outcome == "applied"
    assert second.items[0].outcome == "duplicate"


async def test_unique_alias_is_tagged_and_ambiguous_alias_is_not(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    _, jon_a = await create_template_entity(db_connection, world.template_id, "Jon")
    _, jon_b = await create_template_entity(db_connection, world.template_id, "Jonas")
    await add_template_alias(db_connection, world.template_id, jon_b, "Jon")
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    item = turn_item(
        TurnSpec(1, narration="Mira and Jon greet Kestrel. Miranda waits.")
    )
    await _ingest(db_connection, build_request(playthrough_id, item))
    spans = await span_repo.list_spans_by_sequence(
        db_connection, "playthrough", playthrough_id, 1, 1
    )
    tagged = set(spans[0].entity_ids)
    assert tagged == {world.mira_entity_id, world.player_entity_id}
    assert jon_a not in tagged and jon_b not in tagged


async def test_action_actor_is_participant_and_narration_actor_is_null(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    spec = TurnSpec(1, narration="The door opens.", action="I push the door.")
    await _ingest(db_connection, build_request(playthrough_id, turn_item(spec)))
    sources = await source_repo.list_sources(
        db_connection, "playthrough", playthrough_id, 1, 1
    )
    actors = {source.source_kind: source.actor_participant_id for source in sources}
    assert actors == {"turn_action": spec.participant_id, "turn_narration": None}
    assert all(source.source_ref == str(spec.turn_id) for source in sources)


async def test_empty_action_creates_only_narration_source(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    await _ingest(db_connection, build_request(playthrough_id, turn_item(TurnSpec(1))))
    sources = await source_repo.list_sources(
        db_connection, "playthrough", playthrough_id, 1, 1
    )
    assert [source.source_kind for source in sources] == ["turn_narration"]
    assert sources[0].content == ""


async def test_span_labels_are_unique_within_a_turn(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    spec = TurnSpec(5, narration="One.\n\nTwo.\n\nThree.", action="Go.\n\nNow.")
    await _ingest(db_connection, build_request(playthrough_id, turn_item(spec)))
    spans = await span_repo.list_spans_by_sequence(
        db_connection, "playthrough", playthrough_id, 5, 5
    )
    by_label = {span.label: span.text for span in spans}
    assert by_label == {
        "S5.1": "Go.",
        "S5.2": "Now.",
        "S5.3": "One.",
        "S5.4": "Two.",
        "S5.5": "Three.",
    }


async def test_register_and_turns_in_one_request_share_the_transaction(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    player = player_payload(world.player_authored_id, CUSTOM_PLAYER_NAME)
    request = build_request(
        playthrough_id,
        register_item(world.scenario_id, player=player),
        turn_item(TurnSpec(1, narration="Kestrel arrives.")),
    )
    response = await _ingest(db_connection, request)
    spans = await span_repo.list_spans_by_sequence(
        db_connection, "playthrough", playthrough_id, 1, 1
    )
    assert response.ingested_seq == 1
    assert spans[0].entity_ids == [world.player_entity_id]


async def test_oversized_batch_raises_before_touching_the_database(
    db_connection: AsyncConnection,
) -> None:
    await db_connection.close()
    items = [flush_item(sequence) for sequence in range(1, OVERSIZED_BATCH + 1)]
    with pytest.raises(IngestBatchTooLargeError):
        await _ingest(db_connection, build_request(uuid4(), *items))


@pytest.mark.parametrize("sequences", [(2, 1), (1, 1)])
async def test_unordered_items_raise_before_touching_the_database(
    db_connection: AsyncConnection, sequences: tuple[int, int]
) -> None:
    await db_connection.close()
    items = [turn_item(TurnSpec(sequence)) for sequence in sequences]
    with pytest.raises(IngestOrderError):
        await _ingest(db_connection, build_request(uuid4(), *items))


async def test_flush_before_turn_of_same_sequence_is_out_of_order(
    db_connection: AsyncConnection,
) -> None:
    await db_connection.close()
    request = build_request(uuid4(), flush_item(1), turn_item(TurnSpec(1)))
    with pytest.raises(IngestOrderError):
        await _ingest(db_connection, request)


async def test_logs_never_contain_prose(
    db_connection: AsyncConnection, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("INFO")
    structlog.configure(cache_logger_on_first_use=False)
    try:
        await _ingest_canary_turns(db_connection)
    finally:
        structlog.reset_defaults()
    captured = capsys.readouterr()
    assert "ingest_items_applied" in captured.out
    assert CANARY not in captured.out + captured.err


async def _ingest_canary_turns(connection: AsyncConnection) -> None:
    world = await seed_template_world(connection)
    playthrough_id = uuid4()
    orphan = SetupFactPayload(
        fact_id=uuid4(), subject_entity_id=uuid4(), predicate="p", object_literal=CANARY
    )
    player = player_payload(world.player_authored_id, CANARY)
    register = register_item(world.scenario_id, player=player, setup_facts=[orphan])
    spec = TurnSpec(1, narration=CANARY, action=CANARY)
    await _ingest(connection, build_request(playthrough_id, register, turn_item(spec)))
    conflict = TurnSpec(1, narration="different", turn_id=spec.turn_id)
    with pytest.raises(IngestContentConflictError):
        await _ingest(connection, build_request(playthrough_id, turn_item(conflict)))


async def test_registration_stores_participants_and_tracked_fields(
    db_connection: AsyncConnection,
) -> None:
    from app.models.templates import ParticipantPayload

    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    participant = ParticipantPayload(participant_id=uuid4(), display_name="Mira")
    item = register_item(world.scenario_id)
    item.payload.participants = [participant]
    item.payload.tracked_fields = ["health", "gold"]

    await IngestService(db_connection).ingest_items(build_request(playthrough_id, item))

    row = await playthrough_repo.get_playthrough(db_connection, playthrough_id)
    assert row is not None
    assert row.participants == [participant]
    assert row.tracked_fields == ["health", "gold"]
