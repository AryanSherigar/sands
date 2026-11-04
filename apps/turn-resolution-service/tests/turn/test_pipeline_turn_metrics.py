"""turn_metrics rows written by the real pipeline against a real test Postgres."""

import json
import uuid

import pytest
import structlog
from app.db.models.turn_log import TurnLog
from app.db.models.turn_metrics import TurnMetrics
from app.integrations import memory_client
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.repositories.turn_metrics_repo import TurnMetricsRepo
from app.turn import pipeline
from app.turn.steps import ai_orchestrator, state_writer
from app.turn.turn_metrics_collector import TurnMetricsCollector
from session_factories import committed_factory
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from test_pipeline_memory_degraded import _retrieve_with
from test_pipeline_memory_outbox import _call, _fake_model, _seed
from test_pipeline_rule_checks import (
    _answer,
    _narrator,
    _open_check_id,
    _with_params,
    _with_recall,
)
from test_pipeline_rule_checks import _seed as _seed_rule_checks
from test_pipeline_rule_checks import _turn as _rule_check_turn

pytestmark = pytest.mark.asyncio(loop_scope="session")

HURT_CONDITION = {
    "condition_id": "hurt",
    "label": "Hurt",
    "condition_expression": {"field": "player.health", "op": "<", "value": 200},
    "narrator_instruction": "The player is hurt.",
}


async def _run(
    session: AsyncSession, playthrough, participant, client_action_id=None
) -> list:
    response = await pipeline.run_turn(
        TurnRequestInput(
            client_action_id=client_action_id or uuid.uuid4(),
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            action_text="I wait.",
        ),
        await committed_factory(session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    return [event async for event in response.body_iterator]


async def _metrics_rows(session: AsyncSession, playthrough) -> list[TurnMetrics]:
    result = await session.execute(
        select(TurnMetrics)
        .where(TurnMetrics.playthrough_id == playthrough.playthrough_id)
        .order_by(TurnMetrics.turn_number)
    )
    return list(result.scalars().all())


async def _turn_log_count(session: AsyncSession, playthrough) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(TurnLog)
        .where(TurnLog.playthrough_id == playthrough.playthrough_id)
    )
    return result.scalar_one()


@pytest.fixture
def narrator(monkeypatch):
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _fake_model([])
    )


async def test_each_turn_gets_exactly_one_row_with_timings(
    db_session: AsyncSession, narrator, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session)

    await _run(db_session, playthrough, participant)
    await _run(db_session, playthrough, participant)

    rows = await _metrics_rows(db_session, playthrough)
    assert [row.turn_number for row in rows] == [1, 2]
    assert all(row.total_ms >= 0 and row.first_token_ms is not None for row in rows)
    assert {
        "request_receiver",
        "state_loader",
        "context_retrieval",
        "condition_evaluator",
        "ai_orchestrator",
    } <= set(rows[0].step_durations)


async def test_stat_snapshot_matches_the_post_write_numeric_state(
    db_session: AsyncSession, narrator, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session)

    await _run(db_session, playthrough, participant)

    (row,) = await _metrics_rows(db_session, playthrough)
    assert row.stat_snapshot == {"player.health": 100.0}


async def test_fired_condition_ids_are_recorded(
    db_session: AsyncSession, narrator, monkeypatch
) -> None:
    playthrough, participant = await _seed(
        db_session, scenario_conditions=[HURT_CONDITION]
    )

    await _run(db_session, playthrough, participant)

    (row,) = await _metrics_rows(db_session, playthrough)
    assert row.fired_condition_ids == ["hurt"]


async def test_memory_degraded_reasons_and_retrieval_facts_are_recorded(
    db_session: AsyncSession, narrator, monkeypatch
) -> None:
    monkeypatch.setattr(
        memory_client, "retrieve", _retrieve_with(["embedding_unavailable"])
    )
    playthrough, participant = await _seed(db_session)

    await _run(db_session, playthrough, participant)

    (row,) = await _metrics_rows(db_session, playthrough)
    assert row.memory_degraded_reasons == ["embedding_unavailable"]
    assert row.memory_facts_returned == 0
    assert row.memory_retrieval_ms is not None


async def test_a_schema_breaking_mutation_is_counted_as_dropped(
    db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        _fake_model([_call("set_field", path="player.health", value=5000)]),
    )
    playthrough, participant = await _seed(db_session)

    await _run(db_session, playthrough, participant)

    (row,) = await _metrics_rows(db_session, playthrough)
    assert row.dropped_mutation_count == 1
    assert row.dropped_mutation_paths == ["player.health"]


async def test_a_replayed_action_adds_no_row(
    db_session: AsyncSession, narrator, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session)
    action_id = uuid.uuid4()

    await _run(db_session, playthrough, participant, action_id)
    await _run(db_session, playthrough, participant, action_id)
    await _run(db_session, playthrough, participant, action_id)

    (row,) = await _metrics_rows(db_session, playthrough)
    assert row.replay_count == 0
    assert await _turn_log_count(db_session, playthrough) == 1


async def test_a_collector_failure_still_commits_the_turn_and_logs_it(
    db_session: AsyncSession, narrator, monkeypatch
) -> None:
    def explode(self, final_state):
        raise RuntimeError("collector bug")

    monkeypatch.setattr(TurnMetricsCollector, "build_record", explode)
    playthrough, participant = await _seed(db_session)

    with structlog.testing.capture_logs() as logs:
        events = await _run(db_session, playthrough, participant)

    assert events[-1].event == "done"
    assert await _turn_log_count(db_session, playthrough) == 1
    assert await _metrics_rows(db_session, playthrough) == []
    failures = [
        log for log in logs if log["event"] == state_writer.EVENT_TURN_METRICS_FAILED
    ]
    assert failures and failures[0]["log_level"] == "error"


async def test_a_database_failure_in_the_metrics_insert_does_not_fail_the_turn(
    db_session: AsyncSession, narrator, monkeypatch
) -> None:
    async def failing_insert(self, turn_id, playthrough_id, turn_number, record):
        await self.session.execute(
            text("INSERT INTO turn_metrics (turn_id) VALUES (:turn_id)"),
            {"turn_id": turn_id},
        )

    monkeypatch.setattr(TurnMetricsRepo, "create", failing_insert)
    playthrough, participant = await _seed(db_session)

    events = await _run(db_session, playthrough, participant)

    assert events[-1].event == "done"
    assert await _turn_log_count(db_session, playthrough) == 1
    assert await _metrics_rows(db_session, playthrough) == []


async def _check_outcome_after(
    db_session, monkeypatch, report: dict, configure=None
) -> dict:
    playthrough, participant = await _seed_rule_checks(db_session)
    if configure is not None:
        configure(playthrough)
    check_id = await _open_check_id(db_session, playthrough, participant, monkeypatch)
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", _narrator("It rings.")
    )
    await _rule_check_turn(
        db_session, playthrough, participant, **_answer(check_id, **report)
    )
    rows = await _metrics_rows(db_session, playthrough)
    assert rows[0].check_outcomes == []
    (outcome,) = rows[1].check_outcomes
    return outcome


async def test_a_timed_out_report_is_recorded_as_a_timeout(
    db_session: AsyncSession, monkeypatch
) -> None:
    outcome = await _check_outcome_after(db_session, monkeypatch, {"timed_out": True})

    assert outcome["result"] == "timeout"
    assert outcome["kind"] == "timed_choice"


async def test_a_hidden_tab_report_is_recorded_as_hidden(
    db_session: AsyncSession, monkeypatch
) -> None:
    outcome = await _check_outcome_after(
        db_session,
        monkeypatch,
        {"choice_id": "answer", "was_hidden": True},
        configure=lambda playthrough: _with_params(playthrough, hidden_result="unseen"),
    )

    assert outcome["result"] == "hidden"


async def test_an_answered_prompt_records_when_the_player_answered(
    db_session: AsyncSession, monkeypatch
) -> None:
    outcome = await _check_outcome_after(
        db_session, monkeypatch, {"choice_id": "answer"}
    )

    assert outcome["result"] == "passed"
    assert outcome["answer_ms"] >= 0


async def test_a_recall_check_distinguishes_right_from_wrong(
    db_session: AsyncSession, monkeypatch
) -> None:
    right = await _check_outcome_after(
        db_session, monkeypatch, {"choice_id": "v1"}, configure=_with_recall
    )
    wrong = await _check_outcome_after(
        db_session, monkeypatch, {"choice_id": "v0"}, configure=_with_recall
    )

    assert (right["result"], wrong["result"]) == ("passed", "failed")


async def test_metrics_payload_is_json_serialisable() -> None:
    collector = TurnMetricsCollector(is_enabled=True)
    collector.record_step_ms("context_retrieval", 12)

    record = collector.build_record({"player": {"health": 3}, "flag": True})

    assert json.loads(record.model_dump_json())["stat_snapshot"] == {
        "player.health": 3.0
    }
