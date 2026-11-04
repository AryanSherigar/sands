"""Moves the player from what they typed, before conditions run.

Location-gated rules (R2 dwell, R4 approach) read current_location_id, so the
move has to happen in the same turn the player acts. The narrator's own
set_field on the location stays as a fallback for phrasing this cannot read.
"""

import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()

EVENT_MOVEMENT_RESOLVED = "movement_resolved"
EVENT_MOVEMENT_CONFLICT = "movement_conflict"
EVENT_LOCATION_DISCOVERED = "map_location_discovered"
STATE_KEY_CURRENT_LOCATION = "current_location_id"
STATE_KEY_DISCOVERED_LOCATIONS = "discovered_location_ids"
STATE_KEY_LAST_CHANGED_FIELDS = "_last_changed_fields"
ENTITY_TYPE_LOCATION = "location"
ACTION_MODE_DO = "do"
ATTRIBUTE_MOVEMENT_CLASS = "movement_class"
MOVEMENT_CLASS_APPROACH = "approach"
MOVEMENT_CLASS_INTERIOR = "interior"
SOURCE_CODE = "code"
SOURCE_MODEL = "model"
SOURCE_NONE = "none"

_DIRECTION_WORDS = r"(?: to| toward| towards)?"
_ROUTE_NOUNS = r"(?:road|path|trail|route|highway|stairs|stairway)"
APPROACH_VERB_PATTERN = re.compile(
    rf"\b(?:go(?:ing)?{_DIRECTION_WORDS}|walk{_DIRECTION_WORDS}|head{_DIRECTION_WORDS}"
    rf"|run{_DIRECTION_WORDS}|approach|move(?: to| toward| towards)"
    rf"|(?:travel|journey|ride|climb|descend){_DIRECTION_WORDS}|follow"
    rf"|set out(?: for| to| toward| towards)?|make (?:my|your|our) way"
    rf"|take (?:the |a )?(?:[\w'-]+ ){{0,2}}{_ROUTE_NOUNS})\b",
    re.IGNORECASE,
)
ENTER_VERB_PATTERN = re.compile(
    r"\b(?:enter|(?:go|walk|head|step|move) (?:in|inside|into))\b", re.IGNORECASE
)
NEGATION_PATTERN = re.compile(
    r"\b(?:not|never|no|refuse|refuses|don't|dont|won't|wont|can't|cant|cannot)\b",
    re.IGNORECASE,
)
CLAUSE_BOUNDARY_CHARS = ".!?;,\n"


@dataclass(frozen=True)
class _Verb:
    start: int
    is_enter: bool


@dataclass(frozen=True)
class _PlaceMatch:
    start: int
    length: int
    entity_id: str
    movement_class: str


@dataclass(frozen=True)
class MovementResolution:
    state: dict[str, object]
    mutated_paths: set[str] = field(default_factory=set)
    destination_id: str | None = None


def resolve_movement(
    action_text: str,
    action_mode: str,
    state: dict[str, object],
    scenario_snapshot: dict[str, object],
) -> MovementResolution:
    """Return the state after a move the action text asks for, or the
    unchanged state when it asks for none. Only Do actions move the player."""
    unchanged = MovementResolution(state)
    if action_mode != ACTION_MODE_DO or not scenario_snapshot.get("maps"):
        return unchanged
    places = _find_places(action_text, scenario_snapshot)
    destination_id = _pick_destination(action_text, places)
    if destination_id is None or destination_id == state.get(
        STATE_KEY_CURRENT_LOCATION
    ):
        return unchanged
    return _move_to(state, destination_id)


def log_movement_source(
    code_destination_id: str | None, mutated_paths: list[str]
) -> str:
    """Log where this turn's move came from: this resolver, the narrator's own
    set_field on the location, or nowhere."""
    if code_destination_id is not None:
        source = SOURCE_CODE
    elif STATE_KEY_CURRENT_LOCATION in mutated_paths:
        source = SOURCE_MODEL
    else:
        source = SOURCE_NONE
    logger.info(EVENT_MOVEMENT_RESOLVED, source=source)
    return source


def enforce_code_movement(
    working_state: dict[str, object], code_destination_id: str | None
) -> None:
    """The narrator may not undo or redirect a move code already made."""
    if code_destination_id is None:
        return
    if working_state.get(STATE_KEY_CURRENT_LOCATION) == code_destination_id:
        return
    logger.warning(EVENT_MOVEMENT_CONFLICT, location_entity_id=code_destination_id)
    working_state[STATE_KEY_CURRENT_LOCATION] = code_destination_id


def _find_places(
    action_text: str, scenario_snapshot: dict[str, object]
) -> list[_PlaceMatch]:
    places: list[_PlaceMatch] = []
    for entity in scenario_snapshot.get("entities", []) or []:
        if not isinstance(entity, dict):
            continue
        if entity.get("entity_type") != ENTITY_TYPE_LOCATION:
            continue
        places.extend(_match_entity_names(action_text, entity))
    return places


def _match_entity_names(
    action_text: str, entity: dict[str, object]
) -> list[_PlaceMatch]:
    names = [entity.get("canonical_name"), *(entity.get("aliases") or [])]
    matches: list[_PlaceMatch] = []
    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        pattern = re.compile(rf"\b{re.escape(name.strip())}\b", re.IGNORECASE)
        for found in pattern.finditer(action_text):
            matches.append(
                _PlaceMatch(
                    found.start(),
                    len(name.strip()),
                    str(entity.get("entity_id")),
                    _movement_class_of(entity),
                )
            )
    return matches


def _movement_class_of(entity: dict[str, object]) -> str:
    attributes = entity.get("attributes_schema")
    field_def = (
        attributes.get(ATTRIBUTE_MOVEMENT_CLASS)
        if isinstance(attributes, dict)
        else None
    )
    value = field_def.get("initial") if isinstance(field_def, dict) else None
    return str(value) if value else ""


def _pick_destination(action_text: str, places: list[_PlaceMatch]) -> str | None:
    if not places:
        return None
    last_start = max(place.start for place in places)
    final_places = [place for place in places if place.start == last_start]
    longest = max(place.length for place in final_places)
    candidates = [place for place in final_places if place.length == longest]
    verb = _nearest_verb_before(action_text, last_start)
    if verb is None or _is_negated(action_text, verb):
        return None
    return _choose_by_class(candidates, verb.is_enter)


def _nearest_verb_before(action_text: str, place_start: int) -> _Verb | None:
    verbs = [
        _Verb(found.start(), is_enter=False)
        for found in APPROACH_VERB_PATTERN.finditer(action_text)
    ] + [
        _Verb(found.start(), is_enter=True)
        for found in ENTER_VERB_PATTERN.finditer(action_text)
    ]
    preceding = [verb for verb in verbs if verb.start < place_start]
    if not preceding:
        return None
    return max(preceding, key=lambda verb: (verb.start, verb.is_enter))


def _is_negated(action_text: str, verb: _Verb) -> bool:
    clause_start = max(
        (action_text.rfind(char, 0, verb.start) for char in CLAUSE_BOUNDARY_CHARS),
        default=-1,
    )
    return (
        NEGATION_PATTERN.search(action_text[clause_start + 1 : verb.start]) is not None
    )


def _choose_by_class(candidates: list[_PlaceMatch], is_enter: bool) -> str:
    wanted = MOVEMENT_CLASS_INTERIOR if is_enter else MOVEMENT_CLASS_APPROACH
    for candidate in candidates:
        if candidate.movement_class == wanted:
            return candidate.entity_id
    return candidates[0].entity_id


def _move_to(state: dict[str, object], destination_id: str) -> MovementResolution:
    moved = {**state, STATE_KEY_CURRENT_LOCATION: destination_id}
    mutated_paths = {STATE_KEY_CURRENT_LOCATION}
    raw_discovered = state.get(STATE_KEY_DISCOVERED_LOCATIONS)
    discovered = list(raw_discovered) if isinstance(raw_discovered, list) else []
    if destination_id not in discovered:
        moved[STATE_KEY_DISCOVERED_LOCATIONS] = [*discovered, destination_id]
        mutated_paths.add(STATE_KEY_DISCOVERED_LOCATIONS)
        logger.info(EVENT_LOCATION_DISCOVERED, location_entity_id=destination_id)
    _mark_changed_for_conditions(moved, mutated_paths)
    return MovementResolution(moved, mutated_paths, destination_id)


def _mark_changed_for_conditions(
    state: dict[str, object], mutated_paths: set[str]
) -> None:
    """Conditions only re-run when a field they read changed since last turn.
    An empty list already means 'run them all', so it must stay empty."""
    last_changed = state.get(STATE_KEY_LAST_CHANGED_FIELDS)
    if isinstance(last_changed, list) and last_changed:
        state[STATE_KEY_LAST_CHANGED_FIELDS] = sorted({*last_changed, *mutated_paths})
