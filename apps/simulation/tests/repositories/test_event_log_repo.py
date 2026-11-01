import pytest
from app.models.world_events import EventCause, EventLogEntry, PhaseName, StateChange
from app.repositories import event_log_repo
from psycopg.errors import UniqueViolation

from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough

BULK_EVENT_COUNT = 600


def _event(seq: int, turn: int = 0, changes: list[StateChange] | None = None):
    return EventLogEntry(
        seq=seq,
        turn=turn,
        phase=PhaseName.ECONOMY,
        kind="income",
        is_major=seq == 1,
        significance=seq,
        cause=EventCause(
            summary_key="tax", subject_ids=["ashford"], inputs={"gold": seq}
        ),
        changes=changes or [],
    )


async def test_events_round_trip_in_order(db_connection) -> None:
    await seed_playthrough(db_connection)
    entries = [
        _event(1, 0, [StateChange(path="a", before=None, after=1)]),
        _event(2, 1, [StateChange(path="b", before="x", after="y")]),
        _event(3, 1),
    ]
    assert (
        await event_log_repo.append_events(db_connection, PLAYTHROUGH_ID, entries) == 3
    )
    assert await event_log_repo.list_events(db_connection, PLAYTHROUGH_ID) == entries


async def test_duplicate_sequence_number_raises(db_connection) -> None:
    await seed_playthrough(db_connection)
    await event_log_repo.append_events(db_connection, PLAYTHROUGH_ID, [_event(1)])
    with pytest.raises(UniqueViolation):
        await event_log_repo.append_events(db_connection, PLAYTHROUGH_ID, [_event(1)])


async def test_filters_and_limit(db_connection) -> None:
    await seed_playthrough(db_connection)
    await event_log_repo.append_events(
        db_connection, PLAYTHROUGH_ID, [_event(1, 0), _event(2, 1), _event(3, 1)]
    )
    after = await event_log_repo.list_events(db_connection, PLAYTHROUGH_ID, after_seq=1)
    in_turn = await event_log_repo.list_events(db_connection, PLAYTHROUGH_ID, turn=1)
    limited = await event_log_repo.list_events(db_connection, PLAYTHROUGH_ID, limit=2)
    assert [event.seq for event in after] == [2, 3]
    assert [event.seq for event in in_turn] == [2, 3]
    assert [event.seq for event in limited] == [1, 2]


async def test_empty_append_is_a_no_op(db_connection) -> None:
    await seed_playthrough(db_connection)
    assert await event_log_repo.append_events(db_connection, PLAYTHROUGH_ID, []) == 0


async def test_default_page_is_capped_and_ascending(db_connection) -> None:
    await seed_playthrough(db_connection)
    entries = [_event(seq) for seq in range(1, BULK_EVENT_COUNT + 1)]
    await event_log_repo.append_events(db_connection, PLAYTHROUGH_ID, entries)
    page = await event_log_repo.list_events(db_connection, PLAYTHROUGH_ID)
    assert len(page) == event_log_repo.EVENT_PAGE_LIMIT
    assert [event.seq for event in page] == list(range(1, 501))
