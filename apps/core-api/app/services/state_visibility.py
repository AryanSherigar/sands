"""What a playthrough's state and snapshot may reveal to the browser."""

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

CLIENT_SNAPSHOT_KEYS = (
    "mode",
    "genre_tags",
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
FANTASY_CONFIG_KEYS = (
    "version",
    "profile",
    "energy_max",
    "initial_energy",
    "rest_cost",
    "bounty_reward",
    "corpse_item_id",
)
FANTASY_LOCATION_KEYS = ("inn", "quest_giver", "recovery", "cremation")
FANTASY_CLASS_KEYS = (
    "disgraced_knight",
    "rogue_apprentice",
    "fugitive_smuggler",
    "last_priest",
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


def client_snapshot(
    snapshot: dict[str, object],
    state: dict[str, object] | None = None,
    narrative_turn_count: int = 0,
) -> dict[str, object]:
    """Allowlist: a snapshot key not named here is private by default."""
    shared: dict[str, object] = {
        key: copy.deepcopy(snapshot[key])
        for key in CLIENT_SNAPSHOT_KEYS
        if key in snapshot
    }
    portraits = _scene_portraits(snapshot, state or {}, narrative_turn_count)
    if portraits:
        shared["scene_portraits"] = portraits
    fantasy = _public_fantasy_mechanics(snapshot.get("fantasy_mechanics"))
    if fantasy is not None:
        shared["fantasy_mechanics"] = fantasy
    combat = snapshot.get("fantasy_combat")
    if (
        isinstance(combat, dict)
        and isinstance(combat.get("encounters"), list)
        and combat["encounters"]
    ):
        shared["combat_enabled"] = True
    state_schema = snapshot.get("state_schema")
    if isinstance(state_schema, dict):
        shared["state_schema"] = visible_schema(state_schema)
    end_conditions = snapshot.get("end_conditions")
    if isinstance(end_conditions, list):
        shared["end_conditions"] = _public_endings(end_conditions)
    return shared


def _scene_portraits(
    snapshot: dict[str, object], state: dict[str, object], narrative_turn_count: int
) -> list[dict[str, str]]:
    genres = snapshot.get("genre_tags")
    if not isinstance(genres, list) or genres[:1] != ["Slice of Life"]:
        return []
    schema = snapshot.get("state_schema")
    field = schema.get("scene_character_ids") if isinstance(schema, dict) else None
    if (
        not isinstance(field, dict)
        or field.get("hidden") is True
        or field.get("type") != "list"
        or field.get("item_type") != "entity_ref"
    ):
        return []
    ids = state.get("scene_character_ids")
    if snapshot.get("mode") == "newbie":
        ids = _scheduled_portrait_ids(snapshot, ids, narrative_turn_count)
    assets = snapshot.get("character_avatar_assets")
    entities = snapshot.get("entities")
    if (
        not isinstance(ids, list)
        or not isinstance(assets, dict)
        or not isinstance(entities, list)
    ):
        return []
    characters = {
        e.get("entity_id"): e.get("canonical_name")
        for e in entities
        if isinstance(e, dict)
        and e.get("entity_type") == "character"
        and isinstance(e.get("entity_id"), str)
    }
    result: list[dict[str, str]] = []
    for entity_id in ids:
        if not isinstance(entity_id, str) or any(
            item["entity_id"] == entity_id for item in result
        ):
            continue
        name, avatar = characters.get(entity_id), assets.get(entity_id)
        if isinstance(name, str) and isinstance(avatar, str) and avatar:
            result.append({"entity_id": entity_id, "name": name, "avatar_url": avatar})
        if len(result) == 2:
            break
    return result


def _scheduled_portrait_ids(
    snapshot: dict[str, object], initial: object, turn: int
) -> object:
    schedule = snapshot.get("portrait_schedule")
    if not isinstance(schedule, list):
        return initial
    eligible = [
        item
        for item in schedule
        if isinstance(item, dict)
        and type(item.get("turn")) is int
        and 0 < item["turn"] <= turn
        and isinstance(item.get("character_ids"), list)
    ]
    return (
        max(eligible, key=lambda item: item["turn"])["character_ids"]
        if eligible
        else initial
    )


def _public_fantasy_mechanics(value: object) -> dict[str, object] | None:
    if (
        not isinstance(value, dict)
        or type(value.get("version")) is not int
        or value.get("version") != 1
        or value.get("profile") != "zegaris"
    ):
        return None
    result = {
        key: value[key]
        for key in FANTASY_CONFIG_KEYS
        if key in value
        and (value[key] is None or type(value[key]) in (str, int, float))
    }
    for field, keys in (
        ("locations", FANTASY_LOCATION_KEYS),
        ("class_loadouts", FANTASY_CLASS_KEYS),
    ):
        data = value.get(field)
        if isinstance(data, dict):
            result[field] = _public_fantasy_values(data, keys, field)
    return result


def _public_fantasy_values(
    data: dict[str, object], keys: tuple[str, ...], field: str
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key in keys:
        item = data.get(key)
        if field == "locations" and isinstance(item, str):
            result[key] = item
        if (
            field == "class_loadouts"
            and isinstance(item, list)
            and all(isinstance(entry, str) for entry in item)
        ):
            result[key] = list(item)
    return result


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
