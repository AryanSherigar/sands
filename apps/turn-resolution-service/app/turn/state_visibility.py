"""What a playthrough's state may reveal to the browser (mirrors Core API's
app/services/state_visibility.py; the two case tables must stay identical)."""

import copy

HIDDEN_SYSTEM_KEYS = frozenset(
    {
        "_fired_conditions",
        "_check_queue",
        "_check_edges",
        "_check_reopens",
        "_combat",
        "_combat_history",
        "_combat_play_count_deferred",
        "_combat_participant_id",
        "_combat_last_turn",
    }
)


def visible_state(
    state: dict[str, object], state_schema: dict[str, object]
) -> dict[str, object]:
    visible = {
        key: copy.deepcopy(value)
        for key, value in state.items()
        if key not in HIDDEN_SYSTEM_KEYS
    }
    _remove_hidden_values(visible, state_schema)
    return visible


def _remove_hidden_values(values: dict[str, object], schema: dict[str, object]) -> None:
    for name, field_def in schema.items():
        if not isinstance(field_def, dict) or name not in values:
            continue
        if field_def.get("hidden") is True:
            del values[name]
            continue
        nested_values, nested_schema = values[name], field_def.get("fields")
        if isinstance(nested_values, dict) and isinstance(nested_schema, dict):
            _remove_hidden_values(nested_values, nested_schema)


def is_hidden_path(state_schema: dict[str, object], path: str) -> bool:
    """True when the field at `path`, or any group above it, is marked hidden."""
    if not path:
        return False
    fields: object = state_schema
    for segment in path.split("."):
        if not isinstance(fields, dict):
            return False
        field = fields.get(segment)
        if not isinstance(field, dict):
            return False
        if field.get("hidden") is True:
            return True
        fields = field.get("fields")
    return False
