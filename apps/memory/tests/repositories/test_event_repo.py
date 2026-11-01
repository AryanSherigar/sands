"""memory_event: batch idempotent create, sequence listing, FK cascade from
memory_playthrough."""

from app.repositories.event_repo import (
    create_events,
    create_events_with_status,
    list_events,
)
from psycopg import AsyncConnection
from tests.repositories.helpers_evidence import build_event, make_playthrough


async def test_create_events_empty_list_returns_empty(
    db_connection: AsyncConnection,
) -> None:
    assert await create_events(db_connection, []) == []


async def test_create_events_inserts_batch_in_input_order(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    events = [
        build_event(playthrough_id=playthrough.playthrough_id, event_key=f"key-{index}")
        for index in range(3)
    ]

    rows = await create_events(db_connection, events)

    assert [row.event_key for row in rows] == ["key-0", "key-1", "key-2"]
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_event WHERE playthrough_id = %s",
        (playthrough.playthrough_id,),
    )
    assert await cursor.fetchone() == (3,)


async def test_create_events_idempotent_reinsert_returns_existing_no_duplicate(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    event = build_event(playthrough_id=playthrough.playthrough_id)

    first = await create_events(db_connection, [event])
    second = await create_events(db_connection, [event])

    assert second[0].event_id == first[0].event_id
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_event WHERE playthrough_id = %s",
        (playthrough.playthrough_id,),
    )
    assert await cursor.fetchone() == (1,)


async def test_create_events_mixed_new_and_existing(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    existing = build_event(
        playthrough_id=playthrough.playthrough_id, event_key="existing"
    )
    await create_events(db_connection, [existing])
    new_event = build_event(playthrough_id=playthrough.playthrough_id, event_key="new")

    rows = await create_events(db_connection, [existing, new_event])

    assert [row.event_key for row in rows] == ["existing", "new"]
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_event WHERE playthrough_id = %s",
        (playthrough.playthrough_id,),
    )
    assert await cursor.fetchone() == (2,)


async def test_create_events_payload_round_trips_as_dict(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    event = build_event(playthrough_id=playthrough.playthrough_id)
    event = event.model_copy(update={"payload": {"hp_delta": -3, "target": "goblin"}})

    rows = await create_events(db_connection, [event])

    assert rows[0].payload == {"hp_delta": -3, "target": "goblin"}


async def test_list_events_filters_by_sequence_range(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    events = [
        build_event(
            playthrough_id=playthrough.playthrough_id,
            sequence=sequence,
            event_key=f"k{sequence}",
        )
        for sequence in (1, 5, 9)
    ]
    created = await create_events(db_connection, events)

    rows = await list_events(db_connection, playthrough.playthrough_id, 1, 5)

    assert {row.event_id for row in rows} == {created[0].event_id, created[1].event_id}


async def test_list_events_scope_isolation_between_playthroughs(
    db_connection: AsyncConnection,
) -> None:
    playthrough_a = await make_playthrough(db_connection)
    playthrough_b = await make_playthrough(db_connection)
    event_a = build_event(
        playthrough_id=playthrough_a.playthrough_id, event_key="shared"
    )
    event_b = build_event(
        playthrough_id=playthrough_b.playthrough_id, event_key="shared"
    )
    created_a = await create_events(db_connection, [event_a])
    created_b = await create_events(db_connection, [event_b])

    rows_a = await list_events(db_connection, playthrough_a.playthrough_id, 0, 100)
    rows_b = await list_events(db_connection, playthrough_b.playthrough_id, 0, 100)

    assert [row.event_id for row in rows_a] == [created_a[0].event_id]
    assert [row.event_id for row in rows_b] == [created_b[0].event_id]


async def test_create_events_with_status_empty_list_returns_empty(
    db_connection: AsyncConnection,
) -> None:
    assert await create_events_with_status(db_connection, []) == []


async def test_create_events_with_status_marks_new_rows_inserted(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    events = [
        build_event(playthrough_id=playthrough.playthrough_id, event_key=f"key-{index}")
        for index in range(2)
    ]

    rows_with_status = await create_events_with_status(db_connection, events)

    assert [is_inserted for _row, is_inserted in rows_with_status] == [True, True]


async def test_create_events_with_status_reinsert_marks_all_not_inserted(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    events = [
        build_event(playthrough_id=playthrough.playthrough_id, event_key=f"key-{index}")
        for index in range(2)
    ]
    await create_events_with_status(db_connection, events)

    rows_with_status = await create_events_with_status(db_connection, events)

    assert [is_inserted for _row, is_inserted in rows_with_status] == [False, False]


async def test_create_events_with_status_mixed_new_and_existing(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    existing = build_event(
        playthrough_id=playthrough.playthrough_id, event_key="existing"
    )
    await create_events_with_status(db_connection, [existing])
    new_event = build_event(playthrough_id=playthrough.playthrough_id, event_key="new")

    rows_with_status = await create_events_with_status(
        db_connection, [existing, new_event]
    )

    assert [is_inserted for _row, is_inserted in rows_with_status] == [False, True]


async def test_deleting_playthrough_cascades_to_its_events(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    await create_events(
        db_connection, [build_event(playthrough_id=playthrough.playthrough_id)]
    )

    await db_connection.execute(
        "DELETE FROM memory_playthrough WHERE playthrough_id = %s",
        (playthrough.playthrough_id,),
    )

    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_event WHERE playthrough_id = %s",
        (playthrough.playthrough_id,),
    )
    assert await cursor.fetchone() == (0,)
