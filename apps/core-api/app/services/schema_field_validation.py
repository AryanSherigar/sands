"""Validate and strip the optional per-field settings on a state_schema.

`hidden` is always on and must be a boolean. `initial_random` belongs to the
`rule_checks` tool: it is validated while the tool is on, refused when newly
added while the tool is off, and stripped from the pinned schema copy.
"""

import copy
from collections.abc import Iterator, Sequence

from app.exceptions.schema_field_exceptions import SchemaFieldValidationError
from app.exceptions.tool_exceptions import ToolNotEnabledError
from app.services.state_schema_paths import enum_option_values, field_at_path

HIDDEN_KEY = "hidden"
INITIAL_RANDOM_KEY = "initial_random"
RULE_CHECKS_TOOL_KEY = "rule_checks"


def validate_schema_fields(
    state_schema: dict[str, object],
    enabled_tools: Sequence[str],
    previous_schema: dict[str, object] | None = None,
) -> None:
    """With `rule_checks` off only an `initial_random` that is new or changed is
    refused: one left over from when the tool was on stays inert and must not
    block unrelated schema edits."""
    is_tool_on = RULE_CHECKS_TOOL_KEY in enabled_tools
    for path, field in _fields_with_paths(state_schema):
        _validate_hidden_flag(path, field)
        if INITIAL_RANDOM_KEY not in field:
            continue
        if is_tool_on:
            _validate_initial_random(path, field)
        else:
            _ensure_initial_random_is_unchanged(path, field, previous_schema or {})


def strip_initial_random(state_schema: dict[str, object]) -> dict[str, object]:
    return {
        name: _without_initial_random(field) for name, field in state_schema.items()
    }


def _without_initial_random(field: object) -> object:
    if not isinstance(field, dict):
        return copy.deepcopy(field)
    stripped = {
        k: copy.deepcopy(v) for k, v in field.items() if k != INITIAL_RANDOM_KEY
    }
    nested = field.get("fields")
    if isinstance(nested, dict):
        stripped["fields"] = strip_initial_random(nested)
    return stripped


def _fields_with_paths(
    fields: dict[str, object], prefix: str = ""
) -> Iterator[tuple[str, dict[str, object]]]:
    for name, field in fields.items():
        if not isinstance(field, dict):
            continue
        path = f"{prefix}{name}"
        yield path, field
        nested = field.get("fields")
        if isinstance(nested, dict):
            yield from _fields_with_paths(nested, f"{path}.")


def _fail(path: str, reason: str) -> SchemaFieldValidationError:
    return SchemaFieldValidationError(f"State field '{path}': {reason}")


def _validate_hidden_flag(path: str, field: dict[str, object]) -> None:
    if HIDDEN_KEY in field and not isinstance(field[HIDDEN_KEY], bool):
        raise _fail(path, "hidden must be true or false")


def _validate_initial_random(path: str, field: dict[str, object]) -> None:
    choices = field[INITIAL_RANDOM_KEY]
    if field.get("type") != "enum":
        raise _fail(path, "initial_random needs an enum field")
    if not isinstance(choices, list) or not choices:
        raise _fail(path, "initial_random must be a non-empty list")
    allowed = enum_option_values(field.get("options"))
    if not all(isinstance(choice, str) and choice in allowed for choice in choices):
        raise _fail(path, "initial_random values must be options of the field")
    if len(set(choices)) != len(choices):
        raise _fail(path, "initial_random values must be distinct")


def _ensure_initial_random_is_unchanged(
    path: str, field: dict[str, object], previous_schema: dict[str, object]
) -> None:
    previous = field_at_path(previous_schema, path)
    if (
        previous is None
        or previous.get(INITIAL_RANDOM_KEY) != field[INITIAL_RANDOM_KEY]
    ):
        raise ToolNotEnabledError(RULE_CHECKS_TOOL_KEY)
