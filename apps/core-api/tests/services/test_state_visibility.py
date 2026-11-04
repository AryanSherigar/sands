"""Visibility helper tests. The `VISIBLE_STATE_CASES` table is duplicated verbatim
in apps/turn-resolution-service/tests/turn/test_state_visibility.py; keep both
copies identical."""

import pytest
from app.services.state_visibility import client_snapshot, visible_state


def test_simple_portrait_schedule_changes_only_at_authored_turns():
    snapshot = {
        "mode": "newbie",
        "genre_tags": ["Slice of Life"],
        "state_schema": {
            "scene_character_ids": {"type": "list", "item_type": "entity_ref"}
        },
        "entities": [
            {"entity_id": "a", "entity_type": "character", "canonical_name": "Asha"},
            {"entity_id": "b", "entity_type": "character", "canonical_name": "Bao"},
        ],
        "character_avatar_assets": {"a": "avatar-a", "b": "avatar-b"},
        "portrait_schedule": [{"turn": 2, "character_ids": ["b"]}],
    }
    state = {"scene_character_ids": ["a"]}
    assert client_snapshot(snapshot, state, 1)["scene_portraits"][0]["entity_id"] == "a"
    assert client_snapshot(snapshot, state, 2)["scene_portraits"][0]["entity_id"] == "b"
    assert "portrait_schedule" not in client_snapshot(snapshot, state, 2)


def test_scene_portraits_require_explicit_visible_character_list():
    snapshot = {
        "genre_tags": ["Slice of Life"],
        "state_schema": {
            "scene_character_ids": {"type": "list", "item_type": "entity_ref"}
        },
        "entities": [
            {"entity_id": "a", "entity_type": "character", "canonical_name": "Asha"},
            {"entity_id": "b", "entity_type": "character", "canonical_name": "Bao"},
            {"entity_id": "c", "entity_type": "character", "canonical_name": "Cora"},
        ],
        "character_avatar_assets": {"a": "avatar-a", "b": "avatar-b", "c": "avatar-c"},
    }
    assert client_snapshot(snapshot, {"scene_character_ids": ["a", "a", "b", "c"]})[
        "scene_portraits"
    ] == [
        {"entity_id": "a", "name": "Asha", "avatar_url": "avatar-a"},
        {"entity_id": "b", "name": "Bao", "avatar_url": "avatar-b"},
    ]
    assert "scene_portraits" not in client_snapshot(snapshot, {})
    snapshot["state_schema"]["scene_character_ids"]["hidden"] = True
    assert "scene_portraits" not in client_snapshot(
        snapshot, {"scene_character_ids": ["a"]}
    )
    assert "character_avatar_assets" not in client_snapshot(
        snapshot, {"scene_character_ids": ["a"]}
    )


def test_combat_state_is_not_exposed_in_playthrough_state():
    assert visible_state({"_combat": {"secret": "weakness"}, "clock": 1}, {}) == {
        "clock": 1
    }


def test_client_snapshot_exposes_only_safe_fantasy_configuration():
    result = client_snapshot(
        {
            "genre_tags": ["High Fantasy"],
            "fantasy_mechanics": {
                "version": 1,
                "profile": "zegaris",
                "rest_cost": 5,
                "locations": {"inn": "inn-id", "secret": "hidden location"},
                "class_loadouts": {"disgraced_knight": ["sword"], "secret": ["hidden"]},
                "secret": "hidden lore",
            },
            "rule_invariants": [{"secret": "private"}],
        }
    )
    assert result["genre_tags"] == ["High Fantasy"]
    assert result["fantasy_mechanics"] == {
        "version": 1,
        "profile": "zegaris",
        "rest_cost": 5,
        "locations": {"inn": "inn-id"},
        "class_loadouts": {"disgraced_knight": ["sword"]},
    }
    assert "rule_invariants" not in result


def test_client_snapshot_omits_unrecognized_fantasy_profiles():
    assert "fantasy_mechanics" not in client_snapshot(
        {"fantasy_mechanics": {"version": 2, "profile": "zegaris"}}
    )


def test_fantasy_projection_does_not_copy_nested_objects_as_values():
    result = client_snapshot(
        {
            "fantasy_mechanics": {
                "version": 1,
                "profile": "zegaris",
                "bounty_reward": {"secret": "x"},
                "locations": {"inn": {"secret": "x"}},
                "class_loadouts": {"last_priest": ["mace", {"secret": "x"}]},
            }
        }
    )
    assert "secret" not in repr(result)


VISIBLE_STATE_CASES = [
    pytest.param(
        {"sanity": {"type": "number", "hidden": True}, "clock": {"type": "number"}},
        {"sanity": 40, "clock": 12},
        {"clock": 12},
        id="hidden-leaf-removed",
    ),
    pytest.param(
        {
            "secrets": {
                "type": "object",
                "hidden": True,
                "fields": {"code": {"type": "string"}},
            }
        },
        {"secrets": {"code": "1234"}, "other": 1},
        {"other": 1},
        id="hidden-group-removes-subtree",
    ),
    pytest.param(
        {"sanity": {"type": "number"}},
        {"sanity": 40},
        {"sanity": 40},
        id="absent-flag-is-visible",
    ),
    pytest.param(
        {"sanity": {"type": "number", "hidden": False}},
        {"sanity": 40},
        {"sanity": 40},
        id="false-flag-is-visible",
    ),
    pytest.param(
        {
            "player": {
                "type": "object",
                "fields": {
                    "health": {"type": "number"},
                    "dread": {"type": "number", "hidden": True},
                },
            }
        },
        {"player": {"health": 9, "dread": 3}},
        {"player": {"health": 9}},
        id="nested-hidden-leaf-removed",
    ),
    pytest.param(
        {},
        {
            "a": 1,
            "_fired_conditions": ["c1"],
            "_check_queue": ["k"],
            "_check_edges": ["k"],
            "_check_reopens": {"k": 1},
        },
        {"a": 1},
        id="new-system-keys-stripped",
    ),
    pytest.param(
        {},
        {
            "_pending_check": {"check_id": "x"},
            "_pending_minigame": {"minigame_id": "m"},
            "_last_changed_fields": ["a"],
            "_active_conditions": ["c"],
        },
        {
            "_pending_check": {"check_id": "x"},
            "_pending_minigame": {"minigame_id": "m"},
            "_last_changed_fields": ["a"],
            "_active_conditions": ["c"],
        },
        id="existing-system-keys-kept",
    ),
    pytest.param(
        {"sanity": {"type": "number", "hidden": True}},
        {"entities": {"e1": {"sanity": 5}}},
        {"entities": {"e1": {"sanity": 5}}},
        id="entity-attributes-not-filtered-by-root-schema",
    ),
    pytest.param(
        {"sanity": {"type": "number", "hidden": True}},
        {"clock": 3},
        {"clock": 3},
        id="hidden-field-absent-from-state-is-fine",
    ),
]


@pytest.mark.parametrize(("schema", "state", "expected"), VISIBLE_STATE_CASES)
def test_visible_state(schema, state, expected):
    assert visible_state(state, schema) == expected


def test_visible_state_does_not_mutate_its_inputs():
    schema = {"sanity": {"type": "number", "hidden": True}}
    state = {"sanity": 1, "_check_queue": ["k"]}

    visible_state(state, schema)

    assert state == {"sanity": 1, "_check_queue": ["k"]}
    assert schema == {"sanity": {"type": "number", "hidden": True}}


def _full_snapshot():
    return {
        "mode": "master",
        "narrator_persona": "secret persona",
        "world_data": {"lore": "x"},
        "setup_schema": [],
        "state_schema": {
            "clock": {"type": "number"},
            "sanity": {"type": "number", "hidden": True},
        },
        "checkpoints": [{"c": 1}],
        "narration_font": "serif",
        "narrator_voice_name": "Kore",
        "music_tracks": {"mystery": None},
        "action_chips": ["Look"],
        "entities": [{"entity_id": "e1"}],
        "facts": [{"fact_id": "f1"}],
        "scenario_conditions": [{"label": "secret"}],
        "rule_invariants": [{"label": "secret"}],
        "scenario_minigames": [{"label": "secret"}],
        "end_conditions": [
            {
                "outcome_tag": "win",
                "outcome_title": "Dawn",
                "outcome_text": "You leave.",
                "is_secret": False,
                "condition_expression": {"field": "x"},
                "priority": 1,
            },
            {
                "outcome_tag": "lose",
                "outcome_title": "Hidden",
                "outcome_text": "Secret text",
                "is_secret": True,
            },
        ],
        "enabled_tools": ["rule_checks"],
        "maps": [{"map_id": "m"}],
        "map_pins": [],
        "map_connections": [],
        "rule_checks": [{"correct_index": 1}],
        "brand_new_key": "private by default",
    }


def test_client_snapshot_keeps_exactly_the_allowlisted_keys():
    result = client_snapshot(_full_snapshot())

    assert set(result) == {
        "mode",
        "world_data",
        "setup_schema",
        "state_schema",
        "narration_font",
        "narrator_voice_name",
        "music_tracks",
        "action_chips",
        "entities",
        "facts",
        "end_conditions",
        "enabled_tools",
        "maps",
        "map_pins",
        "map_connections",
    }


def test_client_snapshot_drops_server_only_and_unknown_keys():
    result = client_snapshot(_full_snapshot())

    for private_key in (
        "scenario_conditions",
        "rule_invariants",
        "scenario_minigames",
        "narrator_persona",
        "checkpoints",
        "rule_checks",
        "brand_new_key",
    ):
        assert private_key not in result


def test_client_snapshot_removes_hidden_fields_from_schema_copy():
    result = client_snapshot(_full_snapshot())

    assert result["state_schema"] == {"clock": {"type": "number"}}


def test_client_snapshot_reduces_endings_to_non_secret_three_fields():
    result = client_snapshot(_full_snapshot())

    assert result["end_conditions"] == [
        {"outcome_tag": "win", "outcome_title": "Dawn", "outcome_text": "You leave."}
    ]


def test_client_snapshot_does_not_invent_absent_keys():
    assert client_snapshot({"mode": "newbie"}) == {"mode": "newbie"}


def test_client_snapshot_does_not_mutate_the_source():
    source = _full_snapshot()

    client_snapshot(source)

    assert source == _full_snapshot()


from app.services.state_visibility import (  # noqa: E402
    is_hidden_path,
    redact_hidden_tool_calls,
)

HIDDEN_SCHEMA = {
    "dread": {"type": "number", "hidden": True},
    "clock": {"type": "number"},
    "secrets": {
        "type": "object",
        "hidden": True,
        "fields": {"code": {"type": "string"}},
    },
    "player": {
        "type": "object",
        "fields": {
            "fear": {"type": "number", "hidden": True},
            "hp": {"type": "number"},
        },
    },
}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("dread", True),
        ("clock", False),
        ("secrets", True),
        ("secrets.code", True),
        ("player.fear", True),
        ("player.hp", False),
        ("player", False),
        ("unknown.path", False),
        ("", False),
    ],
)
def test_is_hidden_path(path, expected):
    assert is_hidden_path(HIDDEN_SCHEMA, path) is expected


def _call(path: str) -> dict:
    return {
        "tool_name": "set_field",
        "arguments": {"path": path, "value": 1},
        "result": {"path": path, "new_value": 1},
        "is_valid": True,
    }


def test_tool_calls_on_hidden_fields_are_dropped_from_scrollback():
    calls = [_call("dread"), _call("clock"), _call("player.fear"), _call("player.hp")]

    kept = redact_hidden_tool_calls(calls, HIDDEN_SCHEMA)

    assert [c["arguments"]["path"] for c in kept] == ["clock", "player.hp"]


def test_tool_calls_without_a_path_are_kept():
    call = {
        "tool_name": "propose_check",
        "arguments": {"check_type": "x"},
        "result": {},
    }

    assert redact_hidden_tool_calls([call], HIDDEN_SCHEMA) == [call]


def test_redaction_does_not_mutate_its_input():
    calls = [_call("dread")]

    redact_hidden_tool_calls(calls, HIDDEN_SCHEMA)

    assert len(calls) == 1


def test_a_logged_rule_violation_is_dropped_from_scrollback():
    schema = {
        "rule_flags": {
            "type": "object",
            "hidden": True,
            "fields": {"r2": {"type": "boolean"}},
        }
    }
    calls = [
        {
            "tool_name": "flag_rule_violation",
            "arguments": {
                "rule_id": "r2",
                "evidence": "He opened the cage.",
                "path": "rule_flags.r2",
            },
        },
        {"tool_name": "set_field", "arguments": {"path": "sanity", "value": "50"}},
    ]

    kept = redact_hidden_tool_calls(calls, schema)

    assert [call["tool_name"] for call in kept] == ["set_field"]
