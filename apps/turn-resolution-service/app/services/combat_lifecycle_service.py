"""Start and resolve authored encounters in the existing turn transaction."""

import asyncio
import uuid

from app.combat.encounters import (
    EndingOutcome,
    RecoveryOutcome,
    choose_outcome,
    encounter_from_snapshot,
    prepare_encounter,
    with_player_health,
)
from app.combat.models import CombatState
from app.config import settings
from app.db.models.playthrough import Playthrough
from app.exceptions.combat_exceptions import (
    CombatActionError,
    CombatReplayConflictError,
)
from app.exceptions.turn_exceptions import ParticipantAccessDeniedError
from app.models.auth import CurrentUser
from app.models.combat import (
    AvailableEncounter,
    CombatOptions,
    CombatOutcomeRequest,
    CombatOutcomeResult,
    CombatStartRequest,
    CombatStateView,
    public_combat_state,
)
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.services.combat_service import _authorize, _authorize_combat_participant
from app.turn.state_paths import set_field_value
from app.turn.steps.map_state_sync import sync_discovered_locations
from app.turn.turn_order import expected_participant
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

START_RECEIPT = "_combat_start"
OUTCOME_RECEIPT = "_combat_outcome"
HISTORY_KEY = "_combat_history"


async def get_combat_options(
    session: AsyncSession,
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    current_user: CurrentUser,
) -> CombatOptions:
    """Return public, currently eligible encounters and any unresolved combat."""
    await _authorize(session, playthrough_id, participant_id, current_user)
    playthrough = await PlaythroughRepo(session).get_by_id(playthrough_id)
    if (
        playthrough is None
        or playthrough.status != "active"
        or playthrough.scenario_snapshot.get("mode") != "master"
    ):
        return CombatOptions(state=None, encounters=[])
    current = playthrough.state.get("_combat")
    if isinstance(current, dict) and (
        current.get("status") == "active"
        or (
            current.get("status") == "player_defeated" and not current.get("outcome_id")
        )
    ):
        try:
            return CombatOptions(
                state=public_combat_state(CombatState.model_validate(current)),
                encounters=[],
            )
        except ValidationError as exc:
            raise CombatActionError("Combat state is invalid.") from exc
    return CombatOptions(state=None, encounters=_available_encounters(playthrough))


def _available_encounters(playthrough: Playthrough) -> list[AvailableEncounter]:
    config = playthrough.scenario_snapshot.get("fantasy_combat")
    records = config.get("encounters") if isinstance(config, dict) else None
    if not isinstance(records, list):
        return []
    available = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(
            record.get("encounter_id"), str
        ):
            continue
        try:
            _start(playthrough, record["encounter_id"])
            encounter = encounter_from_snapshot(
                playthrough.scenario_snapshot, record["encounter_id"]
            )
            available.append(
                AvailableEncounter(
                    encounter_id=encounter.encounter_id, title=encounter.title
                )
            )
        except (ValueError, ValidationError, TypeError):
            continue
    return available


def _start(playthrough: Playthrough, encounter_id: str) -> tuple[dict, dict]:
    state = playthrough.state
    current = state.get("_combat")
    if isinstance(current, dict) and (
        current.get("status") == "active"
        or (
            current.get("status") == "player_defeated" and not current.get("outcome_id")
        )
    ):
        raise ValueError("combat is already pending")
    history = state.get(HISTORY_KEY, [])
    if not isinstance(history, list) or encounter_id in history:
        raise ValueError("encounter was already started")
    if state.get("_pending_check") or state.get("_pending_minigame"):
        raise ValueError("another encounter is pending")
    config = encounter_from_snapshot(playthrough.scenario_snapshot, encounter_id)
    combat = prepare_encounter(config, state)
    state = with_player_health(
        state,
        playthrough.scenario_snapshot,
        next(actor.health for actor in combat.combatants if actor.side == "player"),
    )
    state = {
        **state,
        "_combat": combat.model_dump(mode="json"),
        HISTORY_KEY: [*history, encounter_id],
    }
    return state, public_combat_state(combat).model_dump(mode="json")


def _ending(snapshot: dict, outcome: EndingOutcome) -> dict:
    endings = snapshot.get("end_conditions", [])
    matches = [
        item
        for item in endings
        if isinstance(item, dict)
        and item.get("end_condition_id") == outcome.ending_id
        and item.get("outcome_tag") == "lose"
    ]
    if len(matches) != 1:
        raise ValueError("ending is not configured")
    uuid.UUID(outcome.ending_id)
    return matches[0]


def _recovery(state: dict, snapshot: dict, outcome: RecoveryOutcome) -> dict:
    if outcome.location_id is None:
        return with_player_health(state, snapshot, outcome.health)
    _validate_recovery_location(snapshot, outcome.location_id)
    previous = state
    state = set_field_value(state, "player.health", outcome.health)
    state = {**state, "current_location_id": outcome.location_id}
    changed = sync_discovered_locations(previous, state)
    result = with_player_health(state, snapshot, outcome.health)
    return {
        **result,
        "_last_changed_fields": sorted(
            set(result.get("_last_changed_fields", []))
            | {"current_location_id"}
            | changed
        ),
    }


def _validate_recovery_location(snapshot: dict, location_id: str) -> None:
    entities = snapshot.get("entities", [])
    schema = snapshot.get("state_schema", {})
    location_field = (
        schema.get("current_location_id") if isinstance(schema, dict) else None
    )
    if (
        not isinstance(location_field, dict)
        or location_field.get("type") != "entity_ref"
    ):
        raise ValueError("recovery location is not in the state schema")
    if not any(
        isinstance(item, dict)
        and item.get("entity_id") == location_id
        and item.get("entity_type") == "location"
        for item in entities
    ):
        raise ValueError("recovery location is not authored")


def _resolve(playthrough: Playthrough, revision: int) -> tuple[dict, dict, dict | None]:
    combat = CombatState.model_validate(playthrough.state.get("_combat"))
    if (
        combat.status != "player_defeated"
        or combat.outcome_id
        or combat.revision != revision
    ):
        raise ValueError("combat outcome is unavailable")
    snapshot = playthrough.scenario_snapshot
    config = encounter_from_snapshot(snapshot, combat.encounter_id)
    outcome = choose_outcome(config, playthrough.state, None)
    state, ending = playthrough.state, None
    if isinstance(outcome, RecoveryOutcome):
        state = _recovery(state, snapshot, outcome)
    else:
        ending = _ending(snapshot, outcome)
    combat = combat.model_copy(
        update={"outcome_id": outcome.id, "revision": combat.revision + 1}
    )
    state = {**state, "_combat": combat.model_dump(mode="json")}
    result = CombatOutcomeResult(
        state=public_combat_state(combat), outcome_id=outcome.id
    )
    return state, result.model_dump(mode="json"), ending


async def _save(
    session: AsyncSession,
    playthrough: Playthrough,
    request: CombatStartRequest | CombatOutcomeRequest,
    receipt_name: str,
    state: dict,
    result: dict,
    ending: dict | None,
) -> None:
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
    receipt = _receipt(request, receipt_name, result)
    log = await TurnLogRepo(session).create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=next_turn,
        participant_id=request.participant_id,
        action_text="Combat encounter",
        narration_text="",
        tool_calls=[receipt],
        client_action_id=request.client_action_id,
        accepted_delta=_accepted_delta(receipt_name, result),
    )
    await _complete_write(session, playthrough, next_turn, log.turn_id, ending)
    await session.commit()


def _accepted_delta(name: str, result: dict) -> dict:
    key = "combat.start" if name == START_RECEIPT else "combat.outcome"
    return {"items": [{"kind": "encounter_outcome", "key": key, "detail": result}]}


def _receipt(
    request: CombatStartRequest | CombatOutcomeRequest, name: str, result: dict
) -> dict:
    return {
        "tool_name": name,
        "arguments": request.model_dump(mode="json"),
        "result": result,
        "is_valid": True,
    }


async def _complete_write(
    session: AsyncSession,
    playthrough: Playthrough,
    next_turn: int,
    turn_id: uuid.UUID,
    ending: dict | None,
) -> None:
    if ending is not None:
        await PlaythroughRepo(session).mark_ended(
            playthrough.playthrough_id,
            ending["outcome_tag"],
            ending["outcome_title"],
            ending["outcome_text"],
            uuid.UUID(ending["end_condition_id"]),
            should_commit=False,
        )
    if playthrough.memory_publish_revision is not None:
        outbox = MemoryOutboxRepo(session)
        await outbox.add_turn_row(playthrough.playthrough_id, next_turn, turn_id)
        if ending is not None:
            await outbox.add_flush_row(playthrough.playthrough_id, next_turn)


async def execute_lifecycle(
    session: AsyncSession,
    request: CombatStartRequest | CombatOutcomeRequest,
    current_user: CurrentUser,
) -> CombatStateView | CombatOutcomeResult:
    """Authorize before replay; serialize each transition with the playthrough lock."""
    try:
        return await _execute(session, request, current_user)
    except (ValidationError, ValueError, TypeError, KeyError) as exc:
        await session.rollback()
        raise CombatActionError("Combat lifecycle action is not available.") from exc
    except asyncio.CancelledError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise


async def _execute(
    session: AsyncSession,
    request: CombatStartRequest | CombatOutcomeRequest,
    current_user: CurrentUser,
) -> CombatStateView | CombatOutcomeResult:
    participant = await _authorize(
        session, request.playthrough_id, request.participant_id, current_user
    )
    playthrough = await PlaythroughRepo(session).get_by_id_for_update(
        request.playthrough_id
    )
    if playthrough is None:
        raise CombatActionError("Playthrough not found.")
    name = START_RECEIPT if isinstance(request, CombatStartRequest) else OUTCOME_RECEIPT
    previous = await TurnLogRepo(session).get_by_client_action_id(
        request.playthrough_id, request.client_action_id
    )
    if previous is not None:
        result = _replay(previous, request, name)
        await session.rollback()
        return result
    if (
        playthrough.status != "active"
        or playthrough.scenario_snapshot.get("mode") != "master"
    ):
        raise CombatActionError("Combat is unavailable in this playthrough.")
    if isinstance(request, CombatStartRequest):
        participants = await ParticipantRepo(session).list_by_playthrough(
            request.playthrough_id
        )
        combat_count = await TurnLogRepo(session).count_combat_events(
            request.playthrough_id, playthrough.turn_count
        )
        if (
            expected_participant(
                participants, playthrough.turn_count - combat_count
            ).participant_id
            != request.participant_id
        ):
            raise ParticipantAccessDeniedError()
    else:
        _authorize_combat_participant(playthrough, participant)
    state, result, ending = _transition_lifecycle(playthrough, request)
    if isinstance(request, CombatStartRequest):
        state["_combat_participant_id"] = str(request.participant_id)
    await _save(session, playthrough, request, name, state, result, ending)
    return (
        CombatStateView.model_validate(result)
        if name == START_RECEIPT
        else CombatOutcomeResult.model_validate(result)
    )


def _transition_lifecycle(
    playthrough: Playthrough, request: CombatStartRequest | CombatOutcomeRequest
) -> tuple[dict, dict, dict | None]:
    if isinstance(request, CombatStartRequest):
        state, result = _start(playthrough, request.encounter_id)
        return state, result, None
    return _resolve(playthrough, request.expected_revision)


def _replay(
    turn, request: CombatStartRequest | CombatOutcomeRequest, name: str
) -> CombatStateView | CombatOutcomeResult:
    receipt = next(
        (
            entry
            for entry in (turn.tool_calls or [])
            if isinstance(entry, dict) and entry.get("tool_name") == name
        ),
        None,
    )
    if (
        turn.participant_id != request.participant_id
        or receipt is None
        or receipt.get("arguments") != request.model_dump(mode="json")
    ):
        raise CombatReplayConflictError()
    result = receipt.get("result")
    return (
        CombatStateView.model_validate(result)
        if name == START_RECEIPT
        else CombatOutcomeResult.model_validate(result)
    )
