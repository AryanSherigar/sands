import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.memory_outbox import MemoryOutbox
from app.db.models.turn_log import TurnLog
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import (
    add_playthrough,
    add_turn_log,
    make_scenario,
    make_user,
)


@pytest.mark.asyncio
async def test_add_register_row_defaults(db_session: AsyncSession) -> None:
    playthrough_id = uuid.uuid4()

    row = await MemoryOutboxRepo(db_session).add_register_row(
        playthrough_id, {"scenario_id": "x"}
    )

    assert row.outbox_id is not None
    assert row.item_kind == "register_playthrough"
    assert row.sequence == 0
    assert row.attempt_count == 0
    assert row.delivered_at is None
    assert row.last_error is None
    assert row.created_at is not None


@pytest.mark.asyncio
async def test_register_row_is_unique_per_playthrough(
    db_session: AsyncSession,
) -> None:
    playthrough_id = uuid.uuid4()
    repo = MemoryOutboxRepo(db_session)
    await repo.add_register_row(playthrough_id, {})

    with pytest.raises(IntegrityError):
        await repo.add_register_row(playthrough_id, {})


@pytest.mark.asyncio
async def test_item_kind_check_constraint_rejects_unknown_kind(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        MemoryOutbox(playthrough_id=uuid.uuid4(), item_kind="bogus", sequence=1)
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_same_sequence_allowed_for_turn_and_flush(
    db_session: AsyncSession,
) -> None:
    playthrough_id = uuid.uuid4()
    db_session.add_all(
        [
            MemoryOutbox(playthrough_id=playthrough_id, item_kind="turn", sequence=4),
            MemoryOutbox(playthrough_id=playthrough_id, item_kind="flush", sequence=4),
        ]
    )

    await db_session.flush()


@pytest.mark.asyncio
async def test_turn_log_accepted_delta_defaults_to_empty_object(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    playthrough = await add_playthrough(db_session, scenario, user)
    turn_log = await add_turn_log(db_session, playthrough, 1, datetime.now(UTC))

    await db_session.refresh(turn_log)

    assert turn_log.accepted_delta == {}
    assert turn_log.client_action_id is None


@pytest.mark.asyncio
async def test_turn_log_client_action_id_unique_per_playthrough_but_nulls_allowed(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user)
    playthrough = await add_playthrough(db_session, scenario, user)
    await add_turn_log(db_session, playthrough, 1, datetime.now(UTC))
    await add_turn_log(db_session, playthrough, 2, datetime.now(UTC))
    action_id = uuid.uuid4()
    for turn_number in (3, 4):
        db_session.add(
            TurnLog(
                playthrough_id=playthrough.playthrough_id,
                turn_number=turn_number,
                action_text="a",
                client_action_id=action_id,
            )
        )
        if turn_number == 3:
            await db_session.flush()

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_participants_kind_is_allowed_by_the_check_constraint(
    db_session: AsyncSession,
) -> None:
    playthrough_id = uuid.uuid4()

    await MemoryOutboxRepo(db_session).upsert_participants_row(
        playthrough_id, 2, {"participants": []}
    )

    rows = (
        (
            await db_session.execute(
                select(MemoryOutbox).where(
                    MemoryOutbox.playthrough_id == playthrough_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert [(row.item_kind, row.sequence) for row in rows] == [("participants", 2)]
