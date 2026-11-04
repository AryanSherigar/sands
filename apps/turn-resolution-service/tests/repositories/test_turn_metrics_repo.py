"""Integration tests for TurnMetricsRepo."""

import pytest
from app.db.models.turn_log import TurnLog
from app.db.models.turn_metrics import TurnMetrics
from app.models.turn_metrics import CheckOutcome, TurnMetricsRecord
from app.repositories.turn_log_repo import TurnLogRepo
from app.repositories.turn_metrics_repo import TurnMetricsRepo
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.repositories.test_turn_log_repo import _seed_playthrough

pytestmark = pytest.mark.asyncio(loop_scope="session")

TOTAL_MS = 950


async def _seed_turn(session: AsyncSession) -> TurnLog:
    playthrough = await _seed_playthrough(session)
    return await TurnLogRepo(session).create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=1,
        participant_id=None,
        action_text="open the door",
        narration_text="It opens.",
    )


def _record() -> TurnMetricsRecord:
    return TurnMetricsRecord(
        total_ms=TOTAL_MS,
        first_token_ms=300,
        step_durations={"context_retrieval": 40},
        memory_degraded_reasons=["delivery_lag"],
        fired_condition_ids=["cond-1"],
        dropped_mutation_count=1,
        dropped_mutation_paths=["player.hp"],
        check_outcomes=[CheckOutcome(check_id="c1", kind="recall", result="passed")],
        stat_snapshot={"player.hp": 7.0},
    )


async def _count(session: AsyncSession, model: type) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_create_persists_every_field(db_session: AsyncSession) -> None:
    turn = await _seed_turn(db_session)

    await TurnMetricsRepo(db_session).create(
        turn.turn_id, turn.playthrough_id, turn.turn_number, _record()
    )

    row = (await db_session.execute(select(TurnMetrics))).scalar_one()
    assert row.total_ms == TOTAL_MS
    assert row.memory_degraded_reasons == ["delivery_lag"]
    assert row.check_outcomes[0]["result"] == "passed"
    assert row.stat_snapshot == {"player.hp": 7.0}
    assert row.replay_count == 0


async def test_deleting_the_turn_removes_its_metrics(db_session: AsyncSession) -> None:
    turn = await _seed_turn(db_session)
    await TurnMetricsRepo(db_session).create(
        turn.turn_id, turn.playthrough_id, 1, _record()
    )

    await db_session.execute(delete(TurnLog).where(TurnLog.turn_id == turn.turn_id))

    assert await _count(db_session, TurnMetrics) == 0
