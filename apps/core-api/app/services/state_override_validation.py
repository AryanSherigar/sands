"""Validation and merge of the tracked values a playtest may preset."""

import copy

from app.exceptions.playthrough_exceptions import (
    InvalidSchemaInitialError,
    InvalidStateOverrideError,
)
from app.services.initial_state import ensure_initial_fits
from app.services.state_schema_paths import field_at_path

PATH_SEPARATOR = "."
SETTABLE_FIELD_TYPES = frozenset({"number", "string", "boolean", "enum"})
REASON_UNKNOWN = "no such value"
REASON_CARD_VALUE = "card values cannot be preset"
REASON_NOT_SETTABLE = "this kind of value cannot be preset"


def validate_state_overrides(
    state_schema: dict[str, object],
    entities: list[dict[str, object]],
    overrides: dict[str, object],
) -> dict[str, object]:
    """Check every preset against the pinned state_schema before anything is
    created; a single bad entry rejects the whole set."""
    card_ids = {
        str(entity["entity_id"]) for entity in entities if "entity_id" in entity
    }
    validated: dict[str, object] = {}
    for key, value in overrides.items():
        field_def = _settable_field(state_schema, card_ids, key)
        _ensure_value_fits(field_def, key, value)
        validated[key] = copy.deepcopy(value)
    return validated


def merge_state_overrides(
    state: dict[str, object], overrides: dict[str, object]
) -> dict[str, object]:
    merged = copy.deepcopy(state)
    for key, value in overrides.items():
        _set_at_path(merged, key.split(PATH_SEPARATOR), value)
    return merged


def _settable_field(
    state_schema: dict[str, object], card_ids: set[str], key: str
) -> dict[str, object]:
    field_def = field_at_path(state_schema, key)
    if field_def is None:
        is_card_value = key.split(PATH_SEPARATOR)[0] in card_ids
        raise InvalidStateOverrideError(
            key, REASON_CARD_VALUE if is_card_value else REASON_UNKNOWN
        )
    if field_def.get("type") not in SETTABLE_FIELD_TYPES:
        raise InvalidStateOverrideError(key, REASON_NOT_SETTABLE)
    return field_def


def _ensure_value_fits(field_def: dict[str, object], key: str, value: object) -> None:
    try:
        ensure_initial_fits(field_def, key, value)
    except InvalidSchemaInitialError as error:
        raise InvalidStateOverrideError(key, error.reason) from error


def _set_at_path(target: dict[str, object], segments: list[str], value: object) -> None:
    for segment in segments[:-1]:
        child = target.get(segment)
        if not isinstance(child, dict):
            child = {}
            target[segment] = child
        target = child
    target[segments[-1]] = value
