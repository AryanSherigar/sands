"""memory_playthrough: idempotent register, template_missing, monotonic watermarks/flush."""

from uuid import uuid4

from app.models.templates import ParticipantPayload, PlaythroughCreate
from app.repositories.playthrough_repo import (
    advance_watermarks,
    get_playthrough,
    list_playthroughs_behind_index,
    register_playthrough,
    set_flush_requested,
)
from psycopg import AsyncConnection
from tests.repositories.helpers_evidence import make_playthrough, make_template


async def test_register_playthrough_returns_row_with_default_watermarks(
    db_connection: AsyncConnection,
) -> None:
    template = await make_template(db_connection)
    playthrough_id = uuid4()

    row = await register_playthrough(
        db_connection,
        PlaythroughCreate(
            playthrough_id=playthrough_id, template_id=template.template_id
        ),
    )

    assert row.playthrough_id == playthrough_id
    assert row.template_id == template.template_id
    assert row.ingested_seq == 0
    assert row.indexed_seq == 0
    assert row.extracted_seq == 0
    assert row.latest_seq_seen == 0
    assert row.flush_requested_through_seq is None


async def test_register_playthrough_stores_participants_and_tracked_fields(
    db_connection: AsyncConnection,
) -> None:
    participant = ParticipantPayload(participant_id=uuid4(), display_name="Mira")

    row = await register_playthrough(
        db_connection,
        PlaythroughCreate(
            playthrough_id=uuid4(),
            template_id=None,
            participants=[participant],
            tracked_fields=["player.health", "player.gold"],
        ),
    )

    assert row.participants == [participant]
    assert row.tracked_fields == ["player.health", "player.gold"]


async def test_register_playthrough_defaults_to_empty_extraction_context(
    db_connection: AsyncConnection,
) -> None:
    row = await register_playthrough(
        db_connection, PlaythroughCreate(playthrough_id=uuid4(), template_id=None)
    )

    assert row.participants == []
    assert row.tracked_fields == []


async def test_register_playthrough_idempotent_reinsert_returns_existing_no_duplicate(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id = uuid4()
    first = await register_playthrough(
        db_connection,
        PlaythroughCreate(playthrough_id=playthrough_id, template_id=None),
    )

    second = await register_playthrough(
        db_connection,
        PlaythroughCreate(playthrough_id=playthrough_id, template_id=None),
    )

    assert second == first
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_playthrough WHERE playthrough_id = %s",
        (playthrough_id,),
    )
    assert await cursor.fetchone() == (1,)


async def test_register_playthrough_template_id_null_is_allowed(
    db_connection: AsyncConnection,
) -> None:
    row = await make_playthrough(db_connection, template_id=None)

    assert row.template_id is None


async def test_get_playthrough_returns_row(db_connection: AsyncConnection) -> None:
    created = await make_playthrough(db_connection)

    found = await get_playthrough(db_connection, created.playthrough_id)

    assert found == created


async def test_get_playthrough_returns_none_when_missing(
    db_connection: AsyncConnection,
) -> None:
    assert await get_playthrough(db_connection, uuid4()) is None


async def test_advance_watermarks_moves_forward(db_connection: AsyncConnection) -> None:
    created = await make_playthrough(db_connection)

    updated = await advance_watermarks(
        db_connection, created.playthrough_id, ingested_seq=10, indexed_seq=5
    )

    assert updated is not None
    assert updated.ingested_seq == 10
    assert updated.indexed_seq == 5
    assert updated.extracted_seq == 0


async def test_advance_watermarks_never_moves_backwards(
    db_connection: AsyncConnection,
) -> None:
    created = await make_playthrough(db_connection)
    await advance_watermarks(db_connection, created.playthrough_id, ingested_seq=10)

    regressed = await advance_watermarks(
        db_connection, created.playthrough_id, ingested_seq=3
    )

    assert regressed is not None
    assert regressed.ingested_seq == 10


async def test_advance_watermarks_partial_update_leaves_others_untouched(
    db_connection: AsyncConnection,
) -> None:
    created = await make_playthrough(db_connection)
    await advance_watermarks(
        db_connection,
        created.playthrough_id,
        ingested_seq=10,
        indexed_seq=8,
        extracted_seq=4,
        latest_seq_seen=10,
    )

    updated = await advance_watermarks(
        db_connection, created.playthrough_id, extracted_seq=6
    )

    assert updated is not None
    assert updated.ingested_seq == 10
    assert updated.indexed_seq == 8
    assert updated.extracted_seq == 6
    assert updated.latest_seq_seen == 10


async def test_set_flush_requested_first_call_from_null(
    db_connection: AsyncConnection,
) -> None:
    created = await make_playthrough(db_connection)

    updated = await set_flush_requested(db_connection, created.playthrough_id, 10)

    assert updated is not None
    assert updated.flush_requested_through_seq == 10


async def test_set_flush_requested_is_monotonic(db_connection: AsyncConnection) -> None:
    created = await make_playthrough(db_connection)
    await set_flush_requested(db_connection, created.playthrough_id, 10)

    regressed = await set_flush_requested(db_connection, created.playthrough_id, 3)
    advanced = await set_flush_requested(db_connection, created.playthrough_id, 20)

    assert regressed is not None
    assert regressed.flush_requested_through_seq == 10
    assert advanced is not None
    assert advanced.flush_requested_through_seq == 20


async def test_list_playthroughs_behind_index_returns_only_lagging_playthroughs(
    db_connection: AsyncConnection,
) -> None:
    behind = await make_playthrough(db_connection)
    caught_up = await make_playthrough(db_connection)
    idle = await make_playthrough(db_connection)
    await advance_watermarks(
        db_connection, behind.playthrough_id, ingested_seq=5, indexed_seq=2
    )
    await advance_watermarks(
        db_connection, caught_up.playthrough_id, ingested_seq=5, indexed_seq=5
    )

    rows = await list_playthroughs_behind_index(db_connection)

    assert [row.playthrough_id for row in rows] == [behind.playthrough_id]
    assert rows[0].ingested_seq == 5
    assert rows[0].indexed_seq == 2
    assert idle.playthrough_id not in [row.playthrough_id for row in rows]


async def test_list_playthroughs_behind_index_filters_by_playthrough_id(
    db_connection: AsyncConnection,
) -> None:
    first = await make_playthrough(db_connection)
    second = await make_playthrough(db_connection)
    caught_up = await make_playthrough(db_connection)
    for playthrough in (first, second):
        await advance_watermarks(
            db_connection, playthrough.playthrough_id, ingested_seq=3
        )

    scoped = await list_playthroughs_behind_index(
        db_connection, playthrough_id=second.playthrough_id
    )
    unscoped = await list_playthroughs_behind_index(db_connection)
    not_behind = await list_playthroughs_behind_index(
        db_connection, playthrough_id=caught_up.playthrough_id
    )

    assert [row.playthrough_id for row in scoped] == [second.playthrough_id]
    assert {row.playthrough_id for row in unscoped} == {
        first.playthrough_id,
        second.playthrough_id,
    }
    assert not_behind == []
