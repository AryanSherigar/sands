"""Unit tests for check_result_resolver.py."""

import uuid
from unittest.mock import AsyncMock

from app.turn.steps import check_result_resolver

_STATE = {
    "player": {"health": 100},
    "_pending_check": {
        "check_id": "check-1",
        "check_type": "stealth",
        "difficulty_class": 15,
        "reasoning": "risky",
        "proposing_participant_id": "p-1",
        "resolved_roll": None,
    },
}


def test_resolve_decline_clears_pending_check_and_builds_instruction() -> None:
    resolution = check_result_resolver.resolve_decline(_STATE, "stealth")

    assert "_pending_check" not in resolution.state
    assert "stealth" in resolution.instruction
    assert "chose not to attempt" in resolution.instruction


def test_resolve_decline_does_not_mutate_input_state() -> None:
    check_result_resolver.resolve_decline(_STATE, "stealth")

    assert "_pending_check" in _STATE


def test_resolve_attempt_clears_pending_check_and_reports_success() -> None:
    resolution = check_result_resolver.resolve_attempt(_STATE, "stealth", 15, 17)

    assert "_pending_check" not in resolution.state
    assert "rolled 17" in resolution.instruction
    assert "succeeded" in resolution.instruction


def test_resolve_attempt_reports_failure_when_roll_below_dc() -> None:
    resolution = check_result_resolver.resolve_attempt(_STATE, "stealth", 15, 9)

    assert "rolled 9" in resolution.instruction
    assert "failed" in resolution.instruction


def test_resolve_attempt_success_is_inclusive_of_exact_dc() -> None:
    """A roll exactly equal to the DC succeeds (>=), not just a strict beat."""
    resolution = check_result_resolver.resolve_attempt(_STATE, "stealth", 15, 15)

    assert "succeeded" in resolution.instruction


async def test_ensure_roll_persisted_computes_and_commits_once() -> None:
    playthrough_id = uuid.uuid4()
    playthrough_repo = AsyncMock()

    updated_state, resolved_roll = await check_result_resolver.ensure_roll_persisted(
        playthrough_id, _STATE, playthrough_repo, expected_turn_count=3
    )

    assert 1 <= resolved_roll <= 20
    assert updated_state["_pending_check"]["resolved_roll"] == resolved_roll
    playthrough_repo.update_state.assert_awaited_once()
    call_kwargs = playthrough_repo.update_state.await_args.kwargs
    assert call_kwargs["new_turn_count"] == 3
    assert call_kwargs["expected_turn_count"] == 3
    playthrough_repo.session.commit.assert_awaited_once()


async def test_ensure_roll_persisted_is_idempotent_on_existing_roll() -> None:
    """A retry after the roll was already persisted must never reroll —
    'the die is cast' as soon as it's first recorded."""
    playthrough_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    state_with_roll = {
        **_STATE,
        "_pending_check": {**_STATE["_pending_check"], "resolved_roll": 12},
    }

    updated_state, resolved_roll = await check_result_resolver.ensure_roll_persisted(
        playthrough_id, state_with_roll, playthrough_repo, expected_turn_count=3
    )

    assert resolved_roll == 12
    assert updated_state == state_with_roll
    playthrough_repo.update_state.assert_not_awaited()
    playthrough_repo.session.commit.assert_not_awaited()
