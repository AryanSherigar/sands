"""automatic_effect and roll delta items become accepted facts; both are stored
as events either way."""

from uuid import UUID, uuid4

from app.models.ingest import AcceptedDeltaItem
from app.repositories import event_repo, fact_repo
from app.services.ingest_service import IngestService
from psycopg import AsyncConnection
from tests.services.ingest_helpers import (
    INITIAL_RANK,
    TemplateWorld,
    TurnSpec,
    build_request,
    count_rows,
    player_payload,
    register_item,
    seed_template_world,
    turn_item,
)

CHECK_PREDICATE = "check_result"
ROLL_TEXT = "lockpicking: rolled 14 against DC 12, success"


def _roll(check_id: str, roll: int = 14, **detail: object) -> AcceptedDeltaItem:
    base: dict[str, object] = {
        "check_type": "lockpicking",
        "difficulty_class": 12,
        "is_success": roll >= 12,
    }
    return AcceptedDeltaItem(
        kind="roll", key=check_id, after=roll, detail={**base, **detail}
    )


def _effect(key: str, after: object) -> AcceptedDeltaItem:
    return AcceptedDeltaItem(
        kind="automatic_effect",
        key=key,
        after=after,
        detail={"source": "condition"},
    )


async def _register(
    connection: AsyncConnection, world: TemplateWorld, playthrough_id: UUID
) -> None:
    player = player_payload(world.player_authored_id, "Kestrel")
    await IngestService(connection).ingest_items(
        build_request(playthrough_id, register_item(world.scenario_id, player=player))
    )


async def _ingest_turn(
    connection: AsyncConnection,
    playthrough_id: UUID,
    sequence: int,
    deltas: list[AcceptedDeltaItem],
) -> None:
    item = turn_item(TurnSpec(sequence, narration="x", deltas=deltas))
    await IngestService(connection).ingest_items(build_request(playthrough_id, item))


async def _check_facts(
    connection: AsyncConnection,
    world: TemplateWorld,
    playthrough_id: UUID,
    at_seq: int,
) -> list[object]:
    return await fact_repo.list_valid_facts_at(
        connection,
        playthrough_id,
        world.template_id,
        at_seq,
        predicate=CHECK_PREDICATE,
    )


async def test_automatic_effect_supersedes_the_previous_value(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    key = f"{world.mira_authored_id}.rank"

    await _ingest_turn(db_connection, playthrough_id, 1, [_effect(key, "major")])

    facts = await fact_repo.list_valid_facts_at(
        db_connection,
        playthrough_id,
        world.template_id,
        1,
        subject_entity_ids=[world.mira_entity_id],
        predicate="rank",
    )
    assert [fact.object_literal for fact in facts] == ['"major"']
    assert facts[0].authority == "accepted"
    earlier = await fact_repo.list_valid_facts_at(
        db_connection,
        playthrough_id,
        world.template_id,
        0,
        subject_entity_ids=[world.mira_entity_id],
        predicate="rank",
    )
    assert [fact.object_literal for fact in earlier] == [f'"{INITIAL_RANK}"']


async def test_roll_becomes_one_accepted_fact_about_the_player(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)

    await _ingest_turn(db_connection, playthrough_id, 1, [_roll("check-1")])

    [fact] = await _check_facts(db_connection, world, playthrough_id, 1)
    events = await event_repo.list_events(db_connection, playthrough_id, 1, 1)
    assert fact.subject_entity_id == world.player_entity_id
    assert (fact.authority, fact.assertion) == ("accepted", "occurred")
    assert fact.object_literal == ROLL_TEXT
    assert fact.valid_from_seq == 1
    assert fact.event_id == events[0].event_id


async def test_two_rolls_both_stay_valid(db_connection: AsyncConnection) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)

    await _ingest_turn(db_connection, playthrough_id, 1, [_roll("check-1")])
    await _ingest_turn(db_connection, playthrough_id, 2, [_roll("check-2", 3)])

    facts = await _check_facts(db_connection, world, playthrough_id, 2)
    assert sorted(fact.object_literal for fact in facts) == [
        "lockpicking: rolled 14 against DC 12, success",
        "lockpicking: rolled 3 against DC 12, failure",
    ]


async def test_redelivered_roll_creates_no_second_fact(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    spec = TurnSpec(1, narration="x", deltas=[_roll("check-1")])
    request = build_request(playthrough_id, turn_item(spec))
    await IngestService(db_connection).ingest_items(request)
    facts_after_first = (await count_rows(db_connection))["memory_fact"]

    await IngestService(db_connection).ingest_items(request)

    assert (await count_rows(db_connection))["memory_fact"] == facts_after_first


async def test_roll_without_a_player_entity_stays_an_event_only(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await IngestService(db_connection).ingest_items(
        build_request(playthrough_id, register_item(world.scenario_id))
    )

    await _ingest_turn(db_connection, playthrough_id, 1, [_roll("check-1")])

    assert await _check_facts(db_connection, world, playthrough_id, 1) == []
    events = await event_repo.list_events(db_connection, playthrough_id, 1, 1)
    assert [event.event_kind for event in events] == ["roll"]


async def test_roll_with_unusable_detail_stays_an_event_only(
    db_connection: AsyncConnection,
) -> None:
    world = await seed_template_world(db_connection)
    playthrough_id = uuid4()
    await _register(db_connection, world, playthrough_id)
    broken = AcceptedDeltaItem(kind="roll", key="check-1", after=14, detail={})

    await _ingest_turn(db_connection, playthrough_id, 1, [broken])

    assert await _check_facts(db_connection, world, playthrough_id, 1) == []
