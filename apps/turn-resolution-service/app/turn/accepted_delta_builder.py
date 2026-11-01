"""Builds a turn's AcceptedDelta from its validated tool calls and state change.

Pure computation only, called exclusively from pipeline.py (CLAUDE.md: steps
in steps/ never call each other). Covers state_mutation, map_discovery,
automatic_effect (Effect C and minigame-result mutations, applied before
narration) and roll (a resolved check attempt); encounter outcomes are not
derived (docs/memory-specs/memory-eval-readiness.spec.md §2).
"""

from dataclasses import dataclass, field

from app.models.accepted_delta import AcceptedDelta, AcceptedDeltaItem
from app.models.check_event import CheckResolvedPayload
from app.models.tool_call import MUTATION_TOOL_NAMES
from app.turn import state_paths

STATE_KEY_DISCOVERED_LOCATIONS = "discovered_location_ids"
INTERNAL_KEY_PREFIX = "_"
EFFECT_SOURCE_CONDITION = "condition"
EFFECT_SOURCE_MINIGAME = "minigame"
EFFECT_SOURCE_RULE_CHECK = "rule_check"
EFFECT_SOURCE_MOVEMENT = "movement"


@dataclass(frozen=True)
class IntakeEffects:
    """What the pre-narration intake did to the turn's state.

    turn_start_state is the state as loaded, before the minigame/check/condition
    pass; effect_sources maps each path that pass wrote to its source.
    """

    turn_start_state: dict[str, object]
    effect_sources: dict[str, str] = field(default_factory=dict)
    check_resolved: CheckResolvedPayload | None = None


def build_accepted_delta(
    pre_state: dict[str, object],
    post_state: dict[str, object] | None,
    tool_calls: list[dict[str, object]] | None,
    intake: IntakeEffects | None = None,
) -> AcceptedDelta:
    """Return the accepted changes between pre_state and post_state.

    pre_state is the state after the intake pass. post_state is None for a turn
    that has no master-mode result (newbie).
    """
    if post_state is None:
        return AcceptedDelta()
    items = _automatic_effect_items(pre_state, intake)
    items.extend(_state_mutation_items(pre_state, post_state, tool_calls or []))
    items.extend(_roll_items(intake))
    items.extend(_map_discovery_items(pre_state, post_state))
    return AcceptedDelta(items=items)


def _automatic_effect_items(
    post_intake_state: dict[str, object], intake: IntakeEffects | None
) -> list[AcceptedDeltaItem]:
    if intake is None:
        return []
    items: list[AcceptedDeltaItem] = []
    for path, source in intake.effect_sources.items():
        if path.startswith(INTERNAL_KEY_PREFIX):
            continue
        before = state_paths.get_field_value(intake.turn_start_state, path)
        after = state_paths.get_field_value(post_intake_state, path)
        if before == after:
            continue
        items.append(
            AcceptedDeltaItem(
                kind="automatic_effect",
                key=path,
                before=before,
                after=after,
                detail={"source": source},
            )
        )
    return items


def _roll_items(intake: IntakeEffects | None) -> list[AcceptedDeltaItem]:
    checked = intake.check_resolved if intake is not None else None
    if checked is None or checked.resolved_roll is None:
        return []
    return [
        AcceptedDeltaItem(
            kind="roll",
            key=checked.check_id,
            after=checked.resolved_roll,
            detail={
                "check_type": checked.check_type,
                "difficulty_class": checked.difficulty_class,
                "is_success": checked.is_success,
            },
        )
    ]


def _state_mutation_items(
    pre_state: dict[str, object],
    post_state: dict[str, object],
    tool_calls: list[dict[str, object]],
) -> list[AcceptedDeltaItem]:
    tool_name_by_path: dict[str, object] = {}
    for call in tool_calls:
        path = _accepted_mutation_path(call)
        if path is not None:
            tool_name_by_path.setdefault(path, call.get("tool_name"))
    return [
        AcceptedDeltaItem(
            kind="state_mutation",
            key=path,
            before=state_paths.get_field_value(pre_state, path),
            after=state_paths.get_field_value(post_state, path),
            detail={"tool_name": tool_name},
        )
        for path, tool_name in tool_name_by_path.items()
    ]


def _accepted_mutation_path(call: dict[str, object]) -> str | None:
    if not call.get("is_valid") or call.get("tool_name") not in MUTATION_TOOL_NAMES:
        return None
    arguments = call.get("arguments")
    path = arguments.get("path") if isinstance(arguments, dict) else None
    return path if isinstance(path, str) and path else None


def _map_discovery_items(
    pre_state: dict[str, object], post_state: dict[str, object]
) -> list[AcceptedDeltaItem]:
    before = _discovered_location_ids(pre_state)
    return [
        AcceptedDeltaItem(kind="map_discovery", key=location_id, after=location_id)
        for location_id in _discovered_location_ids(post_state)
        if location_id not in before
    ]


def _discovered_location_ids(state: dict[str, object]) -> list[str]:
    raw = state.get(STATE_KEY_DISCOVERED_LOCATIONS)
    if not isinstance(raw, list):
        return []
    return [str(location_id) for location_id in raw]
