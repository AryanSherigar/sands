"""Builds the eligibility inputs and the retrieve request for one turn.

Pure. Memory never evaluates `when_active` expressions and never sees the
player's state; everything it needs to stay leak-free arrives here as ids.
"""

import uuid

import structlog
from app.config import settings
from app.models.memory import (
    MAX_ID_LIST_LENGTH,
    MAX_LAST_UTTERANCE_CHARS,
    MAX_PARTICIPANT_NAME_CHARS,
    MAX_PARTICIPANT_NAMES,
    MAX_RECENT_TEXT_CHARS,
    MAX_SCENE_ENTITY_IDS,
    RetrieveRequest,
)
from app.models.turn import LoadedState, RecentTurn, TurnRequest
from app.turn import expression_evaluator
from app.turn.on_scene import get_on_scene_entity_ids
from app.turn.recent_turns import fit_recent_text, last_say_utterance

logger = structlog.get_logger()

EVENT_WHEN_ACTIVE_INVALID = "when_active_evaluation_failed"
MODE_MASTER = "master"
STATE_KEY_REVEALED_FACTS = "revealed_facts"


def build_retrieve_request(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    recent_turns: list[RecentTurn],
    participant_names: dict[uuid.UUID, str],
) -> RetrieveRequest:
    snapshot = loaded_state.scenario_snapshot
    return RetrieveRequest(
        playthrough_id=turn_request.playthrough_id,
        sequence=loaded_state.turn_count,
        action_text=turn_request.action_text,
        action_mode=turn_request.action_mode,
        actor_participant_id=turn_request.participant_id,
        recent_text=fit_recent_text(
            recent_turns, participant_names, MAX_RECENT_TEXT_CHARS
        ),
        last_actor_utterance=last_say_utterance(recent_turns, MAX_LAST_UTTERANCE_CHARS),
        scene_authored_entity_ids=build_scene_entity_ids(loaded_state.state, snapshot),
        revealed_fact_ids=build_revealed_fact_ids(loaded_state.state),
        active_conditional_fact_ids=build_active_conditional_fact_ids(
            snapshot, loaded_state.state
        ),
        participant_names=cap_participant_names(participant_names),
        recent_window_turns=settings.recent_window_turns,
    )


def build_scene_entity_ids(
    state: dict[str, object], snapshot: dict[str, object]
) -> list[uuid.UUID]:
    if snapshot.get("mode") != MODE_MASTER:
        return []
    ids = (_to_uuid(raw) for raw in get_on_scene_entity_ids(state, snapshot))
    return sorted({entity_id for entity_id in ids if entity_id is not None})[
        :MAX_SCENE_ENTITY_IDS
    ]


def build_revealed_fact_ids(state: dict[str, object]) -> list[uuid.UUID]:
    raw_ids = state.get(STATE_KEY_REVEALED_FACTS)
    if not isinstance(raw_ids, list):
        return []
    ids = (_to_uuid(raw) for raw in raw_ids)
    return [fact_id for fact_id in ids if fact_id is not None][:MAX_ID_LIST_LENGTH]


def build_active_conditional_fact_ids(
    snapshot: dict[str, object], state: dict[str, object]
) -> list[uuid.UUID]:
    """Conditional facts whose expression holds now. Failing closed: an
    expression that cannot be evaluated leaves its fact inactive."""
    facts = snapshot.get("facts") or []
    active: list[uuid.UUID] = []
    for fact in facts:
        fact_id = _active_fact_id(fact, state)
        if fact_id is not None:
            active.append(fact_id)
    return active[:MAX_ID_LIST_LENGTH]


def _active_fact_id(fact: object, state: dict[str, object]) -> uuid.UUID | None:
    if not isinstance(fact, dict):
        return None
    expression = fact.get("when_active")
    fact_id = _to_uuid(fact.get("fact_id"))
    if fact_id is None or not isinstance(expression, dict):
        return None
    return fact_id if _is_expression_true(expression, state, fact_id) else None


def _is_expression_true(
    expression: dict[str, object], state: dict[str, object], fact_id: uuid.UUID
) -> bool:
    # NOTE: Intentionally broad. The expression is creator-authored data and the
    # evaluator can raise ValueError, TypeError or re.error; none may fail a turn.
    try:
        return expression_evaluator.evaluate(expression, state)
    except Exception as exc:  # noqa: BLE001 - logged, fact stays inactive
        logger.warning(
            EVENT_WHEN_ACTIVE_INVALID,
            fact_id=str(fact_id),
            error_type=type(exc).__name__,
        )
        return False


def cap_participant_names(names: dict[uuid.UUID, str]) -> dict[uuid.UUID, str]:
    items = list(names.items())[:MAX_PARTICIPANT_NAMES]
    return {key: value[:MAX_PARTICIPANT_NAME_CHARS] for key, value in items}


def _to_uuid(value: object) -> uuid.UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None
