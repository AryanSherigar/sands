"""Unit tests for accepted_delta_builder.py."""

from app.models.check_event import CheckResolvedPayload
from app.turn import accepted_delta_builder


def _call(tool_name: str, path: object, is_valid: bool = True) -> dict[str, object]:
    return {
        "tool_name": tool_name,
        "arguments": {"path": path},
        "result": {},
        "is_valid": is_valid,
    }


def test_no_post_state_gives_empty_delta() -> None:
    delta = accepted_delta_builder.build_accepted_delta({"a": 1}, None, [])

    assert delta.items == []


def test_valid_mutation_reads_before_and_after_from_state() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {"player": {"health": 100}},
        {"player": {"health": 90}},
        [_call("adjust_numeric_field", "player.health")],
    )

    [item] = delta.items
    assert (item.kind, item.key, item.before, item.after) == (
        "state_mutation",
        "player.health",
        100,
        90,
    )
    assert item.detail == {"tool_name": "adjust_numeric_field"}


def test_same_path_twice_is_one_item_with_first_before_and_final_after() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {"gold": 10},
        {"gold": 25},
        [_call("adjust_numeric_field", "gold"), _call("set_field", "gold")],
    )

    [item] = delta.items
    assert (item.before, item.after) == (10, 25)
    assert item.detail == {"tool_name": "adjust_numeric_field"}


def test_invalid_calls_and_non_mutation_tools_are_excluded() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {"gold": 1},
        {"gold": 1},
        [
            _call("set_field", "gold", is_valid=False),
            _call("propose_check", "gold"),
            _call("unknown_tool", "gold"),
        ],
    )

    assert delta.items == []


def test_calls_without_a_usable_path_are_skipped() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {},
        {},
        [
            _call("set_field", None),
            _call("set_field", ""),
            _call("set_field", 7),
            {"tool_name": "set_field", "arguments": "oops", "is_valid": True},
        ],
    )

    assert delta.items == []


def test_entity_path_resolves_under_entities() -> None:
    entity_id = "11111111-1111-1111-1111-111111111111"
    delta = accepted_delta_builder.build_accepted_delta(
        {"entities": {entity_id: {"hp": 5}}},
        {"entities": {entity_id: {"hp": 3}}},
        [_call("set_field", f"{entity_id}.hp")],
    )

    [item] = delta.items
    assert (item.key, item.before, item.after) == (f"{entity_id}.hp", 5, 3)


def test_new_discovered_locations_become_map_discovery_items() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {"discovered_location_ids": ["a"]},
        {"discovered_location_ids": ["a", "b"]},
        [],
    )

    [item] = delta.items
    assert (item.kind, item.key, item.before, item.after) == (
        "map_discovery",
        "b",
        None,
        "b",
    )


def test_delta_serialises_to_json_shape_memory_accepts() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {"gold": 1}, {"gold": 2}, [_call("set_field", "gold")]
    )

    assert delta.model_dump(mode="json") == {
        "items": [
            {
                "kind": "state_mutation",
                "key": "gold",
                "before": 1,
                "after": 2,
                "detail": {"tool_name": "set_field"},
            }
        ]
    }


def _effects(
    turn_start_state: dict[str, object],
    effect_sources: dict[str, str] | None = None,
    check_resolved: CheckResolvedPayload | None = None,
) -> accepted_delta_builder.IntakeEffects:
    return accepted_delta_builder.IntakeEffects(
        turn_start_state, effect_sources or {}, check_resolved
    )


def test_intake_effect_becomes_automatic_effect_with_turn_start_before() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {"player": {"health": 95}},
        {"player": {"health": 95}},
        [],
        _effects({"player": {"health": 100}}, {"player.health": "condition"}),
    )

    [item] = delta.items
    assert (item.kind, item.key, item.before, item.after) == (
        "automatic_effect",
        "player.health",
        100,
        95,
    )
    assert item.detail == {"source": "condition"}


def test_unchanged_and_internal_effect_paths_are_skipped() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {"gold": 5, "_pending_check": {}},
        {"gold": 5, "_pending_check": {}},
        [],
        _effects(
            {"gold": 5, "_pending_check": {"a": 1}},
            {"gold": "condition", "_pending_check": "minigame"},
        ),
    )

    assert delta.items == []


def test_automatic_effect_precedes_the_narrators_state_mutation() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {"gold": 9},
        {"gold": 12},
        [_call("set_field", "gold")],
        _effects({"gold": 10}, {"gold": "minigame"}),
    )

    assert [(item.kind, item.before, item.after) for item in delta.items] == [
        ("automatic_effect", 10, 9),
        ("state_mutation", 9, 12),
    ]


def _resolved(roll: int | None) -> CheckResolvedPayload:
    return CheckResolvedPayload(
        check_id="check-1",
        check_type="lockpicking",
        difficulty_class=12,
        resolved_roll=roll,
        is_success=None if roll is None else roll >= 12,
    )


def test_resolved_attempt_becomes_a_roll_item() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {}, {}, [], _effects({}, check_resolved=_resolved(14))
    )

    [item] = delta.items
    assert (item.kind, item.key, item.after) == ("roll", "check-1", 14)
    assert item.detail == {
        "check_type": "lockpicking",
        "difficulty_class": 12,
        "is_success": True,
    }


def test_declined_check_emits_no_roll() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {}, {}, [], _effects({}, check_resolved=_resolved(None))
    )

    assert delta.items == []


def test_newbie_turn_with_intake_effects_still_emits_nothing() -> None:
    delta = accepted_delta_builder.build_accepted_delta(
        {"gold": 1}, None, [], _effects({"gold": 2}, {"gold": "condition"})
    )

    assert delta.items == []
