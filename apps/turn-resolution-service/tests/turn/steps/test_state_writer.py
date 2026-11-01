"""Unit tests for state_writer.py, with repositories mocked."""

import uuid
from unittest.mock import AsyncMock

import pytest
from app.config import settings
from app.exceptions.turn_exceptions import OptimisticLockError, StateWriteError
from app.models.accepted_delta import AcceptedDelta
from app.models.token_usage import TokenUsage
from app.models.turn import LoadedState, TurnRequest
from app.turn.steps.state_writer import MemoryCommit, write_turn
from sqlalchemy.exc import SQLAlchemyError


def _turn_request(action_mode: str = "do") -> TurnRequest:
    return TurnRequest(
        client_action_id=uuid.uuid4(),
        playthrough_id=uuid.uuid4(),
        participant_id=uuid.uuid4(),
        action_text="I look around.",
        action_mode=action_mode,
        turn_count=0,
    )


def _loaded_state(
    turn_count: int,
    scenario_id: uuid.UUID | None = None,
    is_playtest: bool = False,
) -> LoadedState:
    return LoadedState(
        scenario_id=scenario_id or uuid.uuid4(),
        scenario_snapshot={},
        state={"narrative": {}},
        turn_count=turn_count,
        checkpoint=None,
        is_playtest=is_playtest,
    )


def _memory_commit(outbox_repo: AsyncMock | None = None) -> MemoryCommit:
    return MemoryCommit(accepted_delta=AcceptedDelta(), outbox_repo=outbox_repo)


def _repos() -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    playthrough_repo = AsyncMock()
    playthrough_repo.session = AsyncMock()
    turn_log_repo = AsyncMock()
    scenario_repo = AsyncMock()
    return playthrough_repo, turn_log_repo, scenario_repo


async def test_write_turn_persists_turn_log_and_state() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    turn_request = _turn_request()

    updated_state = await write_turn(
        turn_request,
        _loaded_state(turn_count=0),
        "You see a corridor.",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
    )

    turn_log_repo.create.assert_awaited_once()
    playthrough_repo.update_state.assert_awaited_once()
    assert playthrough_repo.update_state.call_args.args[2] == 1
    assert playthrough_repo.update_state.call_args.args[3] == 0
    scenario_repo.increment_play_count.assert_not_awaited()
    assert "turns_so_far" not in updated_state["narrative"]
    assert (
        turn_log_repo.create.call_args.kwargs["client_action_id"]
        == turn_request.client_action_id
    )


async def test_write_turn_leaves_narrative_state_untouched() -> None:
    """The transcript lives in TurnLog; state no longer carries turns_so_far, and
    a corrupted narrative value must not crash the writer."""
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    loaded_state = LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={},
        state={"narrative": None},
        turn_count=0,
        checkpoint=None,
    )

    updated_state = await write_turn(
        _turn_request(),
        loaded_state,
        "You see a corridor.",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
    )

    assert updated_state["narrative"] is None


async def test_write_turn_increments_play_count_at_threshold() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    scenario_id = uuid.uuid4()
    turn_request = _turn_request()

    await write_turn(
        turn_request,
        _loaded_state(
            turn_count=settings.play_count_increment_turn_threshold - 1,
            scenario_id=scenario_id,
        ),
        "narration",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
    )

    scenario_repo.increment_play_count.assert_awaited_once_with(scenario_id)


async def test_combat_defers_play_count_until_tenth_narrative_turn() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    loaded = _loaded_state(turn_count=14)
    loaded.narrative_turn_count = settings.play_count_increment_turn_threshold - 1
    loaded.state["_combat_play_count_deferred"] = True
    await write_turn(
        _turn_request(),
        loaded,
        "narration",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
    )
    scenario_repo.increment_play_count.assert_awaited_once_with(loaded.scenario_id)


async def test_legacy_counted_play_is_not_counted_twice() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    loaded = _loaded_state(turn_count=14)
    loaded.narrative_turn_count = settings.play_count_increment_turn_threshold - 1
    await write_turn(
        _turn_request(),
        loaded,
        "narration",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
    )
    scenario_repo.increment_play_count.assert_not_awaited()


async def test_write_turn_does_not_increment_play_count_off_threshold() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    turn_request = _turn_request()

    await write_turn(
        turn_request,
        _loaded_state(turn_count=settings.play_count_increment_turn_threshold),
        "narration",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
    )

    scenario_repo.increment_play_count.assert_not_awaited()


async def test_write_turn_skips_play_count_increment_for_playtest() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    scenario_id = uuid.uuid4()
    turn_request = _turn_request()

    await write_turn(
        turn_request,
        _loaded_state(
            turn_count=settings.play_count_increment_turn_threshold - 1,
            scenario_id=scenario_id,
            is_playtest=True,
        ),
        "narration",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
    )

    scenario_repo.increment_play_count.assert_not_awaited()


async def test_write_turn_raises_after_retries_exhausted() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    turn_log_repo.create.side_effect = SQLAlchemyError("simulated write failure")

    with pytest.raises(StateWriteError):
        await write_turn(
            _turn_request(),
            _loaded_state(turn_count=0),
            "narration",
            playthrough_repo,
            turn_log_repo,
            scenario_repo,
            _memory_commit(),
        )

    assert turn_log_repo.create.await_count == settings.state_write_max_retries + 1


async def test_write_turn_persists_working_state_and_mutated_paths() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    turn_request = _turn_request()
    working_state = {"player": {"health": 90}, "narrative": {}}

    await write_turn(
        turn_request,
        _loaded_state(turn_count=0),
        "You take a hit.",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
        working_state=working_state,
        tool_calls=[{"tool_name": "adjust_numeric_field", "is_valid": True}],
        mutated_paths={"player.health"},
    )

    persisted_state = playthrough_repo.update_state.call_args.args[1]
    assert persisted_state["player"]["health"] == 90
    assert persisted_state["_last_changed_fields"] == ["player.health"]
    turn_log_repo.create.assert_awaited_once()
    assert turn_log_repo.create.call_args.kwargs["tool_calls"] == [
        {"tool_name": "adjust_numeric_field", "is_valid": True}
    ]


async def test_write_turn_aborts_immediately_on_optimistic_lock_error() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    playthrough_repo.update_state.side_effect = OptimisticLockError()

    with pytest.raises(OptimisticLockError):
        await write_turn(
            _turn_request(),
            _loaded_state(turn_count=0),
            "narration",
            playthrough_repo,
            turn_log_repo,
            scenario_repo,
            _memory_commit(),
        )

    assert playthrough_repo.update_state.await_count == 1
    turn_log_repo.create.assert_not_awaited()
    playthrough_repo.session.rollback.assert_awaited_once()


async def test_write_turn_persists_the_submitted_action_mode() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    turn_request = _turn_request(action_mode="say")

    await write_turn(
        turn_request,
        _loaded_state(turn_count=0),
        "The Warden stirs.",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
    )

    assert turn_log_repo.create.call_args.kwargs["action_mode"] == "say"


async def test_write_turn_calls_update_state_before_turn_log_create() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    call_order: list[str] = []
    playthrough_repo.update_state.side_effect = lambda *_, **__: call_order.append(
        "update_state"
    )
    turn_log_repo.create.side_effect = lambda *_, **__: call_order.append(
        "turn_log_create"
    )

    await write_turn(
        _turn_request(),
        _loaded_state(turn_count=0),
        "narration",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
    )

    assert call_order == ["update_state", "turn_log_create"]


async def test_write_turn_persists_token_usage() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    turn_request = _turn_request()
    usage = TokenUsage(
        prompt_tokens=350, completion_tokens=75, model_name="gemini-2.5-flash"
    )

    await write_turn(
        turn_request,
        _loaded_state(turn_count=0),
        "You enter the chamber.",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
        token_usage=usage,
    )

    turn_log_repo.create.assert_awaited_once()
    create_kwargs = turn_log_repo.create.call_args.kwargs
    assert create_kwargs["prompt_tokens"] == 350
    assert create_kwargs["completion_tokens"] == 75
    assert create_kwargs["model_name"] == "gemini-2.5-flash"


async def test_write_turn_stores_the_turn_under_the_given_id() -> None:
    playthrough_repo, turn_log_repo, scenario_repo = _repos()
    turn_id = uuid.uuid4()

    await write_turn(
        _turn_request(),
        _loaded_state(turn_count=0),
        "You see a corridor.",
        playthrough_repo,
        turn_log_repo,
        scenario_repo,
        _memory_commit(),
        turn_id=turn_id,
    )

    assert turn_log_repo.create.call_args.kwargs["turn_id"] == turn_id
