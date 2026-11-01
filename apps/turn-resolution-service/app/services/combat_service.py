"""Commit one deterministic combat action and its idempotency receipt."""

import asyncio
import uuid

from app.combat.encounters import encounter_from_snapshot, with_player_health
from app.combat.models import CombatAction, CombatState, CombatTransition
from app.combat.resolver import resolve_action
from app.config import settings
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.turn_log import TurnLog
from app.exceptions.combat_exceptions import (
    CombatActionError,
    CombatReplayConflictError,
)
from app.exceptions.turn_exceptions import (
    ParticipantAccessDeniedError,
    ParticipantNotFoundError,
)
from app.models.auth import CurrentUser
from app.models.combat import CombatActionResult, CombatStateView, public_combat_state
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.turn_log_repo import TurnLogRepo
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

COMBAT_STATE_KEY = "_combat"
COMBAT_RECEIPT_NAME = "_combat_action"


async def _authorize(
    session: AsyncSession,
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    current_user: CurrentUser,
) -> Participant:
    participant = await ParticipantRepo(session).get_by_id(participant_id)
    if participant is None or participant.playthrough_id != playthrough_id:
        raise ParticipantNotFoundError()
    if participant.user_id != current_user.user_id or participant.role not in {
        "owner",
        "joined",
    }:
        raise ParticipantAccessDeniedError()
    return participant


def _authorize_combat_participant(
    playthrough: Playthrough, participant: Participant
) -> None:
    participant_id = playthrough.state.get("_combat_participant_id")
    if participant_id is None and participant.role == "owner":
        return
    if participant_id != str(participant.participant_id):
        raise ParticipantAccessDeniedError()


def _replay(
    turn: TurnLog, participant_id: uuid.UUID, action: CombatAction
) -> CombatActionResult:
    if turn.participant_id != participant_id:
        raise ParticipantAccessDeniedError()
    receipt = next(
        (
            entry
            for entry in (turn.tool_calls or [])
            if isinstance(entry, dict) and entry.get("tool_name") == COMBAT_RECEIPT_NAME
        ),
        None,
    )
    if receipt is None or receipt.get("arguments") != action.model_dump(mode="json"):
        raise CombatReplayConflictError()
    return CombatActionResult.model_validate(receipt.get("result"))


def _transition(playthrough: Playthrough, action: CombatAction) -> CombatTransition:
    if (
        playthrough.status != "active"
        or playthrough.scenario_snapshot.get("mode") != "master"
    ):
        raise CombatActionError("Combat is unavailable in this playthrough.")
    if playthrough.state.get("_pending_check") or playthrough.state.get(
        "_pending_minigame"
    ):
        raise CombatActionError("Resolve the pending encounter first.")
    try:
        combat = CombatState.model_validate(playthrough.state.get(COMBAT_STATE_KEY))
        return resolve_action(combat, action)
    except (ValidationError, ValueError) as exc:
        raise CombatActionError(
            "Combat action is not valid for the current state."
        ) from exc


def _receipt(action: CombatAction, transition: CombatTransition) -> dict[str, object]:
    result = CombatActionResult(
        state=public_combat_state(transition.state), event=transition.event
    )
    return {
        "tool_name": COMBAT_RECEIPT_NAME,
        "arguments": action.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "is_valid": True,
    }


async def _write(
    session: AsyncSession,
    playthrough: Playthrough,
    participant_id: uuid.UUID,
    action: CombatAction,
    transition: CombatTransition,
) -> CombatActionResult:
    state = {
        **playthrough.state,
        COMBAT_STATE_KEY: transition.state.model_dump(mode="json"),
    }
    if "fantasy_combat" in playthrough.scenario_snapshot:
        try:
            encounter_from_snapshot(
                playthrough.scenario_snapshot, transition.state.encounter_id
            )
            player = next(
                actor for actor in transition.state.combatants if actor.side == "player"
            )
            state = with_player_health(
                state, playthrough.scenario_snapshot, player.health
            )
        except (ValidationError, ValueError) as exc:
            raise CombatActionError("Combat health violates scenario rules.") from exc
    next_turn = playthrough.turn_count + 1
    state["_combat_last_turn"] = next_turn
    if (
        next_turn == settings.play_count_increment_turn_threshold
        and not playthrough.is_playtest
    ):
        state["_combat_play_count_deferred"] = True
    await PlaythroughRepo(session).update_state(
        playthrough.playthrough_id, state, next_turn, playthrough.turn_count
    )
    receipt = _receipt(action, transition)
    event = transition.event.model_dump(mode="json")
    log = await TurnLogRepo(session).create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=next_turn,
        participant_id=participant_id,
        action_text="Combat attack",
        narration_text="",
        tool_calls=[receipt],
        client_action_id=action.client_action_id,
        accepted_delta={
            "items": [
                {"kind": "encounter_outcome", "key": "combat.attack", "detail": event}
            ]
        },
    )
    if playthrough.memory_publish_revision is not None:
        await MemoryOutboxRepo(session).add_turn_row(
            playthrough.playthrough_id, next_turn, log.turn_id
        )
    await session.commit()
    return CombatActionResult.model_validate(receipt["result"])


async def apply_combat_action(
    session: AsyncSession,
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    current_user: CurrentUser,
    action: CombatAction,
) -> CombatActionResult:
    """Authorize, replay or commit a single action using the playthrough lock."""
    try:
        participant = await _authorize(
            session, playthrough_id, participant_id, current_user
        )
        playthrough = await PlaythroughRepo(session).get_by_id_for_update(
            playthrough_id
        )
        if playthrough is None:
            raise CombatActionError("Playthrough not found.")
        turn = await TurnLogRepo(session).get_by_client_action_id(
            playthrough_id, action.client_action_id
        )
        if turn is not None:
            result = _replay(turn, participant_id, action)
            await session.rollback()
            return result
        _authorize_combat_participant(playthrough, participant)
        return await _write(
            session,
            playthrough,
            participant_id,
            action,
            _transition(playthrough, action),
        )
    except asyncio.CancelledError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise


async def get_combat_state(
    session: AsyncSession,
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    current_user: CurrentUser,
) -> CombatStateView:
    """Return only the public view of a participant's encounter."""
    await _authorize(session, playthrough_id, participant_id, current_user)
    playthrough = await PlaythroughRepo(session).get_by_id(playthrough_id)
    if playthrough is None or playthrough.scenario_snapshot.get("mode") != "master":
        raise CombatActionError("Combat is unavailable in this playthrough.")
    try:
        state = CombatState.model_validate(playthrough.state.get(COMBAT_STATE_KEY))
    except ValidationError as exc:
        raise CombatActionError("Combat is unavailable in this playthrough.") from exc
    return public_combat_state(state)
