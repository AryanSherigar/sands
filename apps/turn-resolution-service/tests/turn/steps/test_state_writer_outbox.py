"""Atomicity tests for state_writer's outbox row, against a real test Postgres.

write_turn commits explicitly, so each test uses its own committed data with
fresh ids rather than relying on db_session's teardown rollback.
"""

import asyncio
import uuid

import pytest
from app.db.models.memory_outbox import MemoryOutbox
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from app.exceptions.turn_exceptions import OptimisticLockError, StateWriteError
from app.models.accepted_delta import AcceptedDelta
from app.models.turn import LoadedState, TurnRequest
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.turn.steps.state_writer import MemoryCommit, write_turn
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    session.add(
        User(user_id=user_id, display_name="T", auth_provider_id=str(uuid.uuid4()))
    )
    await session.flush()
    session.add(
        Scenario(
            scenario_id=scenario_id,
            creator_id=user_id,
            title="S",
            mode="newbie",
            complexity_tier="newbie",
            player_count_support="solo",
        )
    )
    await session.flush()
    playthrough = Playthrough(
        scenario_id=scenario_id,
        created_by=user_id,
        scenario_version=1,
        memory_publish_revision=0,
        state={"narrative": {}},
    )
    session.add(playthrough)
    await session.flush()
    participant = Participant(
        playthrough_id=playthrough.playthrough_id,
        user_id=user_id,
        role="owner",
        turn_order_position=1,
    )
    session.add(participant)
    await session.flush()
    await session.commit()
    return scenario_id, playthrough.playthrough_id, participant.participant_id


def _request(playthrough_id: uuid.UUID, participant_id: uuid.UUID) -> TurnRequest:
    return TurnRequest(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough_id,
        participant_id=participant_id,
        action_text="I act.",
        turn_count=0,
    )


def _loaded(scenario_id: uuid.UUID, turn_count: int = 0) -> LoadedState:
    return LoadedState(
        scenario_id=scenario_id,
        scenario_snapshot={},
        state={"narrative": {}},
        turn_count=turn_count,
        checkpoint=None,
        memory_publish_revision=0,
    )


async def _write(
    session: AsyncSession,
    scenario_id: uuid.UUID,
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    turn_count: int = 0,
) -> dict[str, object]:
    return await write_turn(
        _request(playthrough_id, participant_id),
        _loaded(scenario_id, turn_count),
        "narration",
        PlaythroughRepo(session),
        TurnLogRepo(session),
        ScenarioRepo(session),
        MemoryCommit(AcceptedDelta(), MemoryOutboxRepo(session)),
    )


async def _counts(
    session: AsyncSession, playthrough_id: uuid.UUID
) -> tuple[int, int, int]:
    session.expire_all()
    turn_logs = await session.scalar(
        select(func.count())
        .select_from(TurnLog)
        .where(TurnLog.playthrough_id == playthrough_id)
    )
    rows = await session.scalar(
        select(func.count())
        .select_from(MemoryOutbox)
        .where(MemoryOutbox.playthrough_id == playthrough_id)
    )
    turn_count = await session.scalar(
        select(Playthrough.turn_count).where(
            Playthrough.playthrough_id == playthrough_id
        )
    )
    return turn_logs, rows, turn_count


async def test_failure_after_turn_log_insert_leaves_no_turn_log_no_row_no_state(
    db_session: AsyncSession, monkeypatch
) -> None:
    scenario_id, playthrough_id, participant_id = await _seed(db_session)

    async def _boom(*args, **kwargs):
        raise SQLAlchemyError("simulated outbox insert failure")

    monkeypatch.setattr(MemoryOutboxRepo, "add_turn_row", _boom)

    with pytest.raises(StateWriteError):
        await _write(db_session, scenario_id, playthrough_id, participant_id)

    assert await _counts(db_session, playthrough_id) == (0, 0, 0)


async def test_transient_failure_after_insert_then_retry_writes_exactly_one_row(
    db_session: AsyncSession, monkeypatch
) -> None:
    scenario_id, playthrough_id, participant_id = await _seed(db_session)
    original = MemoryOutboxRepo.add_turn_row
    attempts: list[int] = []

    async def _fail_once(self, *args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            await original(self, *args, **kwargs)
            raise SQLAlchemyError("simulated transient failure after insert")
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(MemoryOutboxRepo, "add_turn_row", _fail_once)

    await _write(db_session, scenario_id, playthrough_id, participant_id)

    assert len(attempts) == 2
    assert await _counts(db_session, playthrough_id) == (1, 1, 1)


async def test_optimistic_lock_loss_writes_no_row(db_session: AsyncSession) -> None:
    scenario_id, playthrough_id, participant_id = await _seed(db_session)

    with pytest.raises(OptimisticLockError):
        await _write(
            db_session, scenario_id, playthrough_id, participant_id, turn_count=5
        )

    assert await _counts(db_session, playthrough_id) == (0, 0, 0)


async def test_two_concurrent_writers_for_one_turn_leave_exactly_one_row(
    db_session: AsyncSession, test_engine
) -> None:
    scenario_id, playthrough_id, participant_id = await _seed(db_session)
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def _writer() -> object:
        async with factory() as session:
            try:
                return await _write(
                    session, scenario_id, playthrough_id, participant_id
                )
            except OptimisticLockError as exc:
                return exc

    results = await asyncio.gather(_writer(), _writer())

    assert sum(isinstance(result, OptimisticLockError) for result in results) == 1
    assert await _counts(db_session, playthrough_id) == (1, 1, 1)


async def test_registered_turn_row_points_at_its_turn_log(
    db_session: AsyncSession,
) -> None:
    scenario_id, playthrough_id, participant_id = await _seed(db_session)

    await _write(db_session, scenario_id, playthrough_id, participant_id)

    turn_log = (
        await db_session.execute(
            select(TurnLog).where(TurnLog.playthrough_id == playthrough_id)
        )
    ).scalar_one()
    row = (
        await db_session.execute(
            select(MemoryOutbox).where(MemoryOutbox.playthrough_id == playthrough_id)
        )
    ).scalar_one()
    assert (row.item_kind, row.sequence, row.turn_id) == ("turn", 1, turn_log.turn_id)
