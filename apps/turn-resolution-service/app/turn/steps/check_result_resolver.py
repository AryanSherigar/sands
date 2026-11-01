"""Resolves a proposed check's roll/decline into a state mutation + narrator
instruction, mirroring minigame_result_resolver.py's shape.

Two distinct pieces:

- ensure_roll_persisted: the one deliberately-new piece of surgery for
  checks. Runs BEFORE ai_orchestrator's call, in run_turn/_run_turn_events,
  and commits directly (its own small write, not state_writer's end-of-turn
  commit) so a dropped connection mid-narration can't cause a reroll on
  retry — "the die is cast" as soon as this returns. Idempotent: a
  _pending_check that already has resolved_roll set is returned unchanged.
  Never advances turn_count (same expected_turn_count passed as both
  new/expected) — only the final state_writer.write_turn commit does that.

- resolve_decline: pure, in-memory only, exactly like minigame_result_
  resolver.resolve_result — no roll involved, so no early commit needed;
  the final state_writer commit persists it same as any other turn.

Runs after state_loader, before context_retrieval (master mode,
action_kind == "check_resolution" only), in the same pipeline slot as
minigame_result_resolver.py.
"""

import uuid

import structlog
from app.repositories.playthrough_repo import PlaythroughRepo
from app.turn.steps import tool_handler

logger = structlog.get_logger()

EVENT_CHECK_ROLL_PERSISTED = "check_roll_persisted"
EVENT_CHECK_DECLINED = "check_declined"
STATE_KEY_PENDING_CHECK = "_pending_check"
DEFAULT_CHECK_DIE_SIDES = 20


class CheckResolution:
    """Updated state plus the narrator instruction to inject into
    active_instructions — mirrors MinigameResolution's shape."""

    def __init__(self, state: dict[str, object], instruction: str) -> None:
        self.state = state
        self.instruction = instruction


async def ensure_roll_persisted(
    playthrough_id: uuid.UUID,
    state: dict[str, object],
    playthrough_repo: PlaythroughRepo,
    expected_turn_count: int,
) -> tuple[dict[str, object], int]:
    """Compute and durably stamp the roll into state["_pending_check"] if not
    already done; idempotent. Returns (updated_state, resolved_roll)."""
    pending_check = state.get(STATE_KEY_PENDING_CHECK)
    if not isinstance(pending_check, dict):
        pending_check = {}
    existing_roll = pending_check.get("resolved_roll")
    if isinstance(existing_roll, int):
        return state, existing_roll

    roll_result = tool_handler.compute_roll(DEFAULT_CHECK_DIE_SIDES, 0)
    resolved_roll = int(roll_result["roll"])

    patched_check = dict(pending_check)
    patched_check["resolved_roll"] = resolved_roll
    updated_state = dict(state)
    updated_state[STATE_KEY_PENDING_CHECK] = patched_check

    await playthrough_repo.update_state(
        playthrough_id,
        updated_state,
        new_turn_count=expected_turn_count,
        expected_turn_count=expected_turn_count,
    )
    await playthrough_repo.session.commit()
    logger.info(
        EVENT_CHECK_ROLL_PERSISTED,
        check_id=pending_check.get("check_id"),
        resolved_roll=resolved_roll,
    )
    return updated_state, resolved_roll


def resolve_attempt(
    state: dict[str, object],
    check_type: str,
    difficulty_class: int,
    resolved_roll: int,
) -> CheckResolution:
    """Clear _pending_check and inject a narrator instruction from the
    already-persisted roll — pure, no I/O (ensure_roll_persisted already did
    the roll and its own commit; this only builds the in-memory turn state
    that flows into ai_orchestrator as the base working_state, exactly like
    resolve_decline)."""
    state = dict(state)
    state.pop(STATE_KEY_PENDING_CHECK, None)
    is_success = resolved_roll >= difficulty_class
    outcome = "succeeded" if is_success else "failed"
    instruction = (
        f"The player attempted the {check_type} check (DC {difficulty_class}) "
        f"and rolled {resolved_roll} — they {outcome}. Narrate the real "
        "consequence of this outcome."
    )
    return CheckResolution(state, instruction)


def resolve_decline(state: dict[str, object], check_type: str) -> CheckResolution:
    """Clear _pending_check and inject a narrator instruction — no roll, no
    early commit; the final state_writer commit persists this like any
    other turn's mutations."""
    state = dict(state)
    state.pop(STATE_KEY_PENDING_CHECK, None)
    logger.info(EVENT_CHECK_DECLINED, check_type=check_type)
    instruction = (
        f"The player chose not to attempt the {check_type} check. Narrate the "
        "real consequence of stepping back from it — this is not a failure, "
        "just a different choice."
    )
    return CheckResolution(state, instruction)
