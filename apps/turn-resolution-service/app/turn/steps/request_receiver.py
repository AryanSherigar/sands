"""Validates an incoming turn request before any state loading occurs."""

import time
import uuid

import structlog
from app.config import settings
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough as PlaythroughModel
from app.db.models.turn_log import TurnLog
from app.exceptions.combat_exceptions import (
    CombatActionError,
    CombatReplayConflictError,
)
from app.exceptions.fantasy_exceptions import FantasyReplayConflictError
from app.exceptions.turn_exceptions import (
    CheckNotArmedError,
    CheckOwnershipError,
    CheckResolutionMismatchError,
    CheckResolutionRequiredError,
    MinigameResultMismatchError,
    MinigameResultRequiredError,
    ParticipantAccessDeniedError,
    ParticipantNotFoundError,
    PlaythroughNotActiveError,
    StrategyTurnUnsupportedError,
    TurnOrderError,
)
from app.models.auth import CurrentUser
from app.models.turn import InputTruncation, TurnRequest, TurnRequestInput
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.turn.action_text_limit import truncate_action_text
from app.turn.rule_check_report import current_time_ms, describe_action, is_armed
from app.turn.turn_order import expected_participant

logger = structlog.get_logger()

EVENT_TURN_STEP_COMPLETED = "turn_step_completed"
EVENT_TURN_REJECTED_NOT_ACTIVE = "turn_rejected_not_active"
EVENT_TURN_REJECTED_ACCESS_DENIED = "turn_rejected_access_denied"
STEP_NAME = "request_receiver"
STATE_KEY_PENDING_MINIGAME = "_pending_minigame"
STATE_KEY_PENDING_CHECK = "_pending_check"
DICE_CHECK_KIND = "dice"
_OWNER_RESOLVED_KINDS = ("check_resolution",)


async def find_completed_turn(
    turn_input: TurnRequestInput,
    turn_log_repo: TurnLogRepo,
    participant_repo: ParticipantRepo,
    current_user: CurrentUser,
) -> TurnLog | None:
    """Return the stored turn a retry of `client_action_id` refers to, if any.

    Runs before receive_request's status, gating and turn-order checks: once the
    original turn committed, turn_count has moved on and a pending check or
    ending may block a legitimate retry. Ownership is validated before the
    stored turn is returned, so a replay never exposes another user's text.
    """
    turn_log = await turn_log_repo.get_by_client_action_id(
        turn_input.playthrough_id, turn_input.client_action_id
    )
    if turn_log is None:
        return None
    participants = await participant_repo.list_by_playthrough(turn_input.playthrough_id)
    acting_participant = _validate_acting_participant(
        participants, turn_input, current_user
    )
    if turn_log.participant_id != acting_participant.participant_id:
        raise ParticipantAccessDeniedError()
    if any(
        isinstance(entry, dict)
        and entry.get("tool_name")
        in {"_combat_action", "_combat_start", "_combat_outcome"}
        for entry in (getattr(turn_log, "tool_calls", None) or [])
    ):
        raise CombatReplayConflictError()
    audit = next(
        (
            entry
            for entry in (getattr(turn_log, "tool_calls", None) or [])
            if isinstance(entry, dict) and entry.get("tool_name") == "_fantasy_action"
        ),
        None,
    )
    requested = (
        turn_input.fantasy_action.action_id if turn_input.fantasy_action else None
    )
    recorded = (
        audit.get("arguments", {}).get("action_id")
        if audit and isinstance(audit.get("arguments"), dict)
        else None
    )
    if requested != recorded and (requested is not None or recorded is not None):
        raise FantasyReplayConflictError()
    return turn_log


async def receive_request(
    turn_input: TurnRequestInput,
    playthrough_repo: PlaythroughRepo,
    participant_repo: ParticipantRepo,
    current_user: CurrentUser,
) -> TurnRequest:
    """Validate playthrough status, participant membership, user ownership,
    pending-minigame gating, and turn order."""
    start = time.monotonic()
    playthrough = await playthrough_repo.get_by_id(turn_input.playthrough_id)
    _validate_playthrough_active(playthrough, turn_input.playthrough_id)
    _validate_turn_mode(playthrough)

    participants = await participant_repo.list_by_playthrough(turn_input.playthrough_id)
    acting_participant = _validate_acting_participant(
        participants, turn_input, current_user
    )

    state = getattr(playthrough, "state", None)
    combat = state.get("_combat") if isinstance(state, dict) else None
    if isinstance(combat, dict) and combat.get("status") == "active":
        raise CombatActionError("Finish the active combat before continuing the story.")
    if (
        isinstance(combat, dict)
        and combat.get("status") == "player_defeated"
        and not combat.get("outcome_id")
    ):
        raise CombatActionError(
            "The combat outcome must be resolved before continuing."
        )

    _validate_minigame_gating(turn_input, _pending_minigame(playthrough))
    _validate_check_gating(turn_input, _pending_check(playthrough), acting_participant)

    if len(participants) > 1 and turn_input.action_kind not in _OWNER_RESOLVED_KINDS:
        combat_events = 0
        if isinstance(combat, dict):
            combat_events = await TurnLogRepo(
                playthrough_repo.session
            ).count_combat_events(turn_input.playthrough_id, playthrough.turn_count)
        _validate_turn_order(
            participants, acting_participant, playthrough.turn_count - combat_events
        )

    _log_step_completed(start, turn_input.playthrough_id)
    return _build_turn_request(turn_input, playthrough)


def _build_turn_request(
    turn_input: TurnRequestInput, playthrough: PlaythroughModel
) -> TurnRequest:
    action_text, input_truncation = _capped_action_text(
        _trusted_action_text(turn_input, _pending_check(playthrough)),
        turn_input.action_kind,
    )
    return TurnRequest(
        playthrough_id=turn_input.playthrough_id,
        participant_id=turn_input.participant_id,
        client_action_id=turn_input.client_action_id,
        action_text=action_text,
        action_kind=turn_input.action_kind,
        action_mode=turn_input.action_mode,
        minigame_result=turn_input.minigame_result,
        check_resolution=turn_input.check_resolution,
        check_report=turn_input.check_report,
        fantasy_action=turn_input.fantasy_action,
        voice_output_requested=turn_input.voice_output_requested,
        turn_count=playthrough.turn_count,
        input_truncation=input_truncation,
    )


def _validate_playthrough_active(
    playthrough: PlaythroughModel | None, playthrough_id: uuid.UUID
) -> None:
    if playthrough is None or playthrough.status != "active":
        logger.warning(
            EVENT_TURN_REJECTED_NOT_ACTIVE,
            playthrough_id=str(playthrough_id),
            status=playthrough.status if playthrough is not None else "not_found",
        )
        raise PlaythroughNotActiveError(_not_active_message(playthrough))


def _validate_turn_mode(playthrough: PlaythroughModel) -> None:
    snapshot = getattr(playthrough, "scenario_snapshot", None) or {}
    if snapshot.get("mode") == "strategy":
        raise StrategyTurnUnsupportedError()


def _validate_acting_participant(
    participants: list[Participant],
    turn_input: TurnRequestInput,
    current_user: CurrentUser,
) -> Participant:
    acting_participant = _find_participant(participants, turn_input.participant_id)
    if acting_participant is None:
        raise ParticipantNotFoundError()

    if acting_participant.user_id != current_user.user_id:
        logger.warning(
            EVENT_TURN_REJECTED_ACCESS_DENIED,
            playthrough_id=str(turn_input.playthrough_id),
            participant_id=str(turn_input.participant_id),
            participant_user_id=str(acting_participant.user_id),
            current_user_id=str(current_user.user_id),
        )
        raise ParticipantAccessDeniedError()

    return acting_participant


def _log_step_completed(start: float, playthrough_id: uuid.UUID) -> None:
    logger.info(
        EVENT_TURN_STEP_COMPLETED,
        step_name=STEP_NAME,
        playthrough_id=str(playthrough_id),
        duration_ms=(time.monotonic() - start) * 1000,
    )


def _pending_minigame(playthrough: PlaythroughModel) -> dict[str, object] | None:
    """Read _pending_minigame off the already-fetched Playthrough row — no
    new query needed, per docs/specs/master-mode-minigames.spec.md §3.3."""
    state = getattr(playthrough, "state", None)
    if not isinstance(state, dict):
        return None
    pending = state.get(STATE_KEY_PENDING_MINIGAME)
    return pending if isinstance(pending, dict) else None


def _validate_minigame_gating(
    turn_input: TurnRequestInput, pending_minigame: dict[str, object] | None
) -> None:
    """A playthrough can never have two minigames pending, and a submitted
    result must match the minigame actually pending — see §2 sequence flow
    step 8 and §3.2's pending-minigame gating cases."""
    if turn_input.action_kind == "minigame_result":
        _validate_minigame_result_submission(turn_input, pending_minigame)
        return
    if pending_minigame is not None:
        raise MinigameResultRequiredError()


def _validate_minigame_result_submission(
    turn_input: TurnRequestInput, pending_minigame: dict[str, object] | None
) -> None:
    if pending_minigame is None:
        raise MinigameResultMismatchError()
    submitted_id = (
        turn_input.minigame_result.minigame_id if turn_input.minigame_result else None
    )
    if submitted_id != pending_minigame.get("minigame_id"):
        raise MinigameResultMismatchError()
    # NOTE: Old pending records predate attempt ids and remain compatible. New
    # records require the server-issued id, preventing a stale overlay from
    # resolving a later encounter with the same minigame definition.
    pending_attempt_id = pending_minigame.get("attempt_id")
    submitted_attempt_id = (
        turn_input.minigame_result.attempt_id if turn_input.minigame_result else None
    )
    if pending_attempt_id is not None and submitted_attempt_id != pending_attempt_id:
        raise MinigameResultMismatchError()


def _pending_check(playthrough: PlaythroughModel) -> dict[str, object] | None:
    """Read _pending_check off the already-fetched Playthrough row, same
    pattern as _pending_minigame above."""
    state = getattr(playthrough, "state", None)
    if not isinstance(state, dict):
        return None
    pending = state.get(STATE_KEY_PENDING_CHECK)
    return pending if isinstance(pending, dict) else None


def _validate_check_gating(
    turn_input: TurnRequestInput,
    pending_check: dict[str, object] | None,
    acting_participant: Participant,
) -> None:
    """A playthrough can never have two checks pending. A dice resolution must
    match the pending dice check and come from the participant who proposed it
    (resolution bypasses normal turn-order rotation precisely because
    ownership is enforced here instead); a rule-check report must match the
    pending rule check, whatever its kind."""
    if turn_input.action_kind == "check_resolution":
        _validate_check_resolution_submission(
            turn_input, pending_check, acting_participant
        )
        return
    if turn_input.action_kind == "check_report":
        _validate_check_report_submission(turn_input, pending_check)
        return
    if pending_check is not None:
        raise CheckResolutionRequiredError()


def _is_dice_check(pending_check: dict[str, object]) -> bool:
    return pending_check.get("kind", DICE_CHECK_KIND) == DICE_CHECK_KIND


def _validate_check_resolution_submission(
    turn_input: TurnRequestInput,
    pending_check: dict[str, object] | None,
    acting_participant: Participant,
) -> None:
    if pending_check is None or not _is_dice_check(pending_check):
        raise CheckResolutionMismatchError()
    submitted_id = (
        turn_input.check_resolution.check_id if turn_input.check_resolution else None
    )
    if submitted_id != pending_check.get("check_id"):
        raise CheckResolutionMismatchError()
    if not is_armed(pending_check):
        raise CheckNotArmedError()
    if str(acting_participant.participant_id) != pending_check.get(
        "proposing_participant_id"
    ):
        raise CheckOwnershipError()


def _trusted_action_text(
    turn_input: TurnRequestInput, pending_check: dict[str, object] | None
) -> str:
    """A rule-check answer is described from the pinned pending check; the
    client's own action_text never reaches the narrator or the turn log."""
    if turn_input.fantasy_action is not None:
        return {
            "rest": "I pay for a full rest.",
            "claim_retrieval_reward": "I claim the retrieval reward.",
        }[turn_input.fantasy_action.action_id]
    if turn_input.action_kind != "check_report" or turn_input.check_report is None:
        return turn_input.action_text
    return describe_action(
        pending_check or {}, turn_input.check_report, current_time_ms()
    )


def _capped_action_text(
    action_text: str, action_kind: str
) -> tuple[str, InputTruncation | None]:
    """Only a free-typed narrative action is player-authored text worth capping;
    the other kinds carry structured payloads or server-derived text."""
    if action_kind != "narrative":
        return action_text, None
    result = truncate_action_text(action_text, settings.turn_action_max_chars)
    if not result.is_truncated:
        return result.text, None
    return result.text, InputTruncation(
        original_length=result.original_length,
        max_length=settings.turn_action_max_chars,
    )


def _validate_check_report_submission(
    turn_input: TurnRequestInput, pending_check: dict[str, object] | None
) -> None:
    if pending_check is None or _is_dice_check(pending_check):
        raise CheckResolutionMismatchError()
    submitted_id = turn_input.check_report.check_id if turn_input.check_report else None
    if submitted_id != pending_check.get("check_id"):
        raise CheckResolutionMismatchError()


def _not_active_message(playthrough: PlaythroughModel | None) -> str:
    """Distinguish a completed story from an abandoned or missing one."""
    if playthrough is not None and playthrough.status == "completed":
        return "This playthrough has already ended"
    return "Playthrough is not active"


def _find_participant(
    participants: list[Participant], participant_id: uuid.UUID
) -> Participant | None:
    for participant in participants:
        if participant.participant_id == participant_id:
            return participant
    return None


def _validate_turn_order(
    participants: list[Participant],
    acting_participant: Participant,
    turn_count: int,
) -> None:
    expected = expected_participant(participants, turn_count)
    if acting_participant.participant_id != expected.participant_id:
        raise TurnOrderError()
