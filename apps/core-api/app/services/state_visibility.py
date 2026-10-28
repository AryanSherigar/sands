"""What a playthrough's state and snapshot may reveal to the browser."""

import copy

HIDDEN_SYSTEM_KEYS = frozenset(
    {"_fired_conditions", "_check_queue", "_check_edges", "_check_reopens"}
)

CLIENT_SNAPSHOT_KEYS = (
    "mode",
    "world_data",
    "setup_schema",
    "entities",
    "facts",
    "maps",
    "map_pins",
    "map_connections",
    "narration_font",
    "narrator_voice_name",
    "music_tracks",
    "tier_tracks",
    "action_chips",
    "enabled_tools",
)
CLIENT_ENDING_KEYS = ("outcome_title", "outcome_tag", "outcome_text")


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


def visible_schema(state_schema: dict[str, object]) -> dict[str, object]:
    visible: dict[str, object] = {}
    for name, field_def in state_schema.items():
        if isinstance(field_def, dict) and field_def.get("hidden") is True:
            continue
        visible[name] = _with_visible_children(field_def)
    return visible


def _with_visible_children(field_def: object) -> object:
    if not isinstance(field_def, dict):
        return copy.deepcopy(field_def)
    nested = field_def.get("fields")
    if not isinstance(nested, dict):
        return copy.deepcopy(field_def)
    return {**copy.deepcopy(field_def), "fields": visible_schema(nested)}


def client_snapshot(snapshot: dict[str, object]) -> dict[str, object]:
    """Allowlist: a snapshot key not named here is private by default."""
    shared: dict[str, object] = {
        key: copy.deepcopy(snapshot[key])
        for key in CLIENT_SNAPSHOT_KEYS
        if key in snapshot
    }
    state_schema = snapshot.get("state_schema")
    if isinstance(state_schema, dict):
        shared["state_schema"] = visible_schema(state_schema)
    end_conditions = snapshot.get("end_conditions")
    if isinstance(end_conditions, list):
        shared["end_conditions"] = _public_endings(end_conditions)
    return shared


def _public_endings(end_conditions: list[object]) -> list[dict[str, object]]:
    return [
        {key: ending.get(key) for key in CLIENT_ENDING_KEYS}
        for ending in end_conditions
        if isinstance(ending, dict) and not ending.get("is_secret")
    ]


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


def redact_hidden_tool_calls(
    tool_calls: list[dict[str, object]], state_schema: dict[str, object]
) -> list[dict[str, object]]:
    """Drops tool calls aimed at hidden fields from what scrollback returns."""
    return [
        call for call in tool_calls if not _targets_hidden_field(call, state_schema)
    ]


def _targets_hidden_field(
    call: dict[str, object], state_schema: dict[str, object]
) -> bool:
    arguments = call.get("arguments")
    path = arguments.get("path") if isinstance(arguments, dict) else None
    return isinstance(path, str) and is_hidden_path(state_schema, path)
