"""Seed values for a new playthrough's state, from state_schema and entities."""

import copy
import random
from collections.abc import Sequence

from app.exceptions.playthrough_exceptions import InvalidSchemaInitialError
from app.services.schema_field_validation import (
    INITIAL_RANDOM_KEY,
    RULE_CHECKS_TOOL_KEY,
)
from app.services.state_schema_paths import enum_option_values

RESERVED_LOCATION_KEYS = frozenset({"current_location_id", "discovered_location_ids"})
ENTITIES_BUCKET = "entities"


def materialise_initial_state(
    state_schema: dict[str, object],
    entities: list[dict[str, object]],
    rng: random.Random,
    enabled_tools: Sequence[str],
) -> dict[str, object]:
    """state_schema initials plus entity attribute initials; `initial_random` is
    drawn only when `rule_checks` is enabled."""
    state = _initials_for_fields(state_schema, "", skipped_keys=RESERVED_LOCATION_KEYS)
    if RULE_CHECKS_TOOL_KEY in enabled_tools:
        _merge_into(state, _drawn_initials(state_schema, "", rng))
    entity_bucket = _entity_attribute_initials(entities)
    if entity_bucket:
        state[ENTITIES_BUCKET] = entity_bucket
    return state


def _drawn_initials(
    fields: dict[str, object], path_prefix: str, rng: random.Random
) -> dict[str, object]:
    drawn: dict[str, object] = {}
    for name, field_def in fields.items():
        if not isinstance(field_def, dict):
            continue
        field_path = f"{path_prefix}{name}"
        if field_def.get("type") == "object":
            nested = field_def.get("fields")
            nested_drawn = (
                _drawn_initials(nested, f"{field_path}.", rng)
                if isinstance(nested, dict)
                else {}
            )
            if nested_drawn:
                drawn[name] = nested_drawn
            continue
        choices = field_def.get(INITIAL_RANDOM_KEY)
        if isinstance(choices, list) and choices:
            value = rng.choice(choices)
            ensure_initial_fits(field_def, field_path, value)
            drawn[name] = value
    return drawn


def _merge_into(target: dict[str, object], source: dict[str, object]) -> None:
    for key, value in source.items():
        existing = target.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            _merge_into(existing, value)
        else:
            target[key] = value


def _entity_attribute_initials(
    entities: list[dict[str, object]],
) -> dict[str, object]:
    bucket: dict[str, object] = {}
    for entity in entities:
        attributes_schema = entity.get("attributes_schema")
        if not isinstance(attributes_schema, dict):
            continue
        entity_id = str(entity["entity_id"])
        initials = _initials_for_fields(attributes_schema, f"{entity_id}.")
        if initials:
            bucket[entity_id] = initials
    return bucket


def _initials_for_fields(
    fields: dict[str, object],
    path_prefix: str,
    skipped_keys: frozenset[str] = frozenset(),
) -> dict[str, object]:
    initials: dict[str, object] = {}
    for name, field_def in fields.items():
        if name in skipped_keys or not isinstance(field_def, dict):
            continue
        value = _initial_for_field(field_def, f"{path_prefix}{name}")
        if value is not None:
            initials[name] = value
    return initials


def _initial_for_field(field_def: dict[str, object], field_path: str) -> object:
    if field_def.get("type") == "object":
        nested = field_def.get("fields")
        if not isinstance(nested, dict):
            return None
        return _initials_for_fields(nested, f"{field_path}.") or None
    value = field_def.get("initial")
    if value is None:
        return None
    ensure_initial_fits(field_def, field_path, value)
    return copy.deepcopy(value)


def ensure_initial_fits(
    field_def: dict[str, object], field_path: str, value: object
) -> None:
    field_type = field_def.get("type")
    if field_type == "number":
        _ensure_number_fits(field_def, field_path, value)
    elif field_type == "string" and not isinstance(value, str):
        raise InvalidSchemaInitialError(field_path, "expected a string")
    elif field_type == "boolean" and not isinstance(value, bool):
        raise InvalidSchemaInitialError(field_path, "expected a boolean")
    elif field_type == "enum":
        _ensure_enum_fits(field_def, field_path, value)


def _ensure_number_fits(
    field_def: dict[str, object], field_path: str, value: object
) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidSchemaInitialError(field_path, "expected a number")
    minimum, maximum = field_def.get("min"), field_def.get("max")
    if isinstance(minimum, int | float) and value < minimum:
        raise InvalidSchemaInitialError(field_path, f"below minimum {minimum}")
    if isinstance(maximum, int | float) and value > maximum:
        raise InvalidSchemaInitialError(field_path, f"above maximum {maximum}")


def _ensure_enum_fits(
    field_def: dict[str, object], field_path: str, value: object
) -> None:
    options = enum_option_values(field_def.get("options"))
    if options and value not in options:
        raise InvalidSchemaInitialError(field_path, "not one of the enum options")
