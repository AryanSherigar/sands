"""Unit tests for condition_evaluator.py."""

import time
import uuid

from app.models.turn import LoadedState
from app.turn.steps import condition_evaluator

_CAIRN_CONDITION = {
    "label": "The Cairn Presses In",
    "condition_expression": {"field": "flags.entered_cairn", "op": "==", "value": True},
    "narrator_instruction": "The cairn presses in on the player's mind.",
    "state_mutation": {"path": "player.sanity", "op": "decrement", "value": 2},
}


def test_authored_condition_updates_explicit_scene_characters() -> None:
    loaded = _loaded_state(
        {"flags": {"entered_cairn": True}, "scene_character_ids": ["asha"]},
        [
            {
                "condition_expression": {
                    "field": "flags.entered_cairn",
                    "op": "==",
                    "value": True,
                },
                "state_mutation": {
                    "path": "scene_character_ids",
                    "op": "set",
                    "value": ["bao"],
                },
            }
        ],
    )
    loaded.scenario_snapshot["state_schema"]["scene_character_ids"] = {
        "type": "list",
        "item_type": "entity_ref",
        "entity_type": "character",
    }
    loaded.scenario_snapshot["entities"] = [
        {"entity_id": "asha", "entity_type": "character"},
        {"entity_id": "bao", "entity_type": "character"},
    ]
    result = condition_evaluator.evaluate_conditions(loaded)
    assert result.state["scene_character_ids"] == ["bao"]


def _loaded_state(
    state: dict, scenario_conditions: list, turn_count: int = 0
) -> LoadedState:
    return LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "state_schema": {
                "player": {"type": "object", "fields": {"sanity": {"type": "number"}}},
                "flags": {
                    "type": "object",
                    "fields": {"entered_cairn": {"type": "boolean"}},
                },
            },
            "entities": [],
            "rule_invariants": [],
            "scenario_conditions": scenario_conditions,
        },
        state=state,
        turn_count=turn_count,
        checkpoint=None,
    )


def test_effect_c_fires_and_decrements_when_condition_true() -> None:
    loaded_state = _loaded_state(
        {"player": {"sanity": 100}, "flags": {"entered_cairn": True}},
        [_CAIRN_CONDITION],
    )
    result = condition_evaluator.evaluate_conditions(loaded_state)

    assert result.state["player"]["sanity"] == 98.0
    assert result.mutated_paths == {"player.sanity"}
    assert result.active_instructions == ["The cairn presses in on the player's mind."]


def test_effect_c_does_not_fire_when_condition_false() -> None:
    loaded_state = _loaded_state(
        {"player": {"sanity": 100}, "flags": {"entered_cairn": False}},
        [_CAIRN_CONDITION],
    )
    result = condition_evaluator.evaluate_conditions(loaded_state)

    assert result.state["player"]["sanity"] == 100
    assert result.mutated_paths == set()
    assert result.active_instructions == []


def test_condition_evaluator_never_imports_narration_client() -> None:
    """CLAUDE.md: only ai_orchestrator.py may call the narration client — this step
    must have no such coupling at all (call-order relative to the actual
    narration call is asserted at the pipeline level, see
    test_pipeline.py::test_run_turn_master_mode_effect_c_precedes_narration_call)."""
    assert not hasattr(condition_evaluator, "narration_router")


def test_field_relevance_skips_conditions_referencing_unchanged_fields() -> None:
    unrelated_condition = {
        "label": "Unrelated",
        "condition_expression": {"field": "player.sanity", "op": "<", "value": 1000},
        "narrator_instruction": "Should not fire — irrelevant field didn't change.",
    }
    loaded_state = _loaded_state(
        {
            "player": {"sanity": 100},
            "flags": {"entered_cairn": True},
            "_last_changed_fields": ["flags.entered_cairn"],
        },
        [unrelated_condition, _CAIRN_CONDITION],
        turn_count=5,
    )

    result = condition_evaluator.evaluate_conditions(loaded_state)

    # _CAIRN_CONDITION references flags.entered_cairn (changed) -> evaluated, fires.
    # unrelated_condition references player.sanity (not in _last_changed_fields) -> skipped.
    assert (
        "Should not fire — irrelevant field didn't change."
        not in result.active_instructions
    )
    assert result.mutated_paths == {"player.sanity"}


def test_turn_zero_evaluates_all_conditions_regardless_of_last_changed() -> None:
    loaded_state = _loaded_state(
        {"player": {"sanity": 100}, "flags": {"entered_cairn": True}},
        [_CAIRN_CONDITION],
        turn_count=0,
    )
    result = condition_evaluator.evaluate_conditions(loaded_state)
    assert result.mutated_paths == {"player.sanity"}


def test_effect_c_mutation_violating_invariant_is_rejected_not_applied() -> None:
    snapshot_condition = {
        "label": "Runaway Buff",
        "condition_expression": {
            "field": "flags.entered_cairn",
            "op": "==",
            "value": True,
        },
        "narrator_instruction": "A surge of unnatural clarity.",
        "state_mutation": {"path": "player.sanity", "op": "set", "value": 500},
    }
    loaded_state = LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "state_schema": {
                "player": {
                    "type": "object",
                    "fields": {"sanity": {"type": "number", "min": 0, "max": 100}},
                },
                "flags": {
                    "type": "object",
                    "fields": {"entered_cairn": {"type": "boolean"}},
                },
            },
            "entities": [],
            "rule_invariants": [],
            "scenario_conditions": [snapshot_condition],
        },
        state={"player": {"sanity": 50}, "flags": {"entered_cairn": True}},
        turn_count=0,
        checkpoint=None,
    )
    result = condition_evaluator.evaluate_conditions(loaded_state)

    assert result.state["player"]["sanity"] == 50  # rejected, unchanged
    assert result.mutated_paths == set()


def test_condition_evaluator_stays_well_under_100ms_with_many_conditions() -> None:
    """Informational latency benchmark, not a hard CI gate."""
    many_conditions = [
        {
            "label": f"Condition {i}",
            "condition_expression": {
                "field": "flags.entered_cairn",
                "op": "==",
                "value": True,
            },
            "narrator_instruction": f"Instruction {i}",
        }
        for i in range(20)
    ]
    loaded_state = _loaded_state(
        {"player": {"sanity": 100}, "flags": {"entered_cairn": True}}, many_conditions
    )

    start = time.monotonic()
    condition_evaluator.evaluate_conditions(loaded_state)
    duration_ms = (time.monotonic() - start) * 1000

    assert duration_ms < 100


def test_list_active_condition_labels_returns_only_true_conditions() -> None:
    inactive = {
        "label": "Warden Is Wary",
        "condition_expression": {
            "field": "the_warden.awareness",
            "op": ">=",
            "value": 50,
        },
    }
    state = {"flags": {"entered_cairn": True}, "the_warden": {"awareness": 10}}

    labels = condition_evaluator.list_active_condition_labels(
        [_CAIRN_CONDITION, inactive], state
    )

    assert labels == ["The Cairn Presses In"]


def test_list_active_condition_labels_evaluates_every_condition_not_just_changed() -> (
    None
):
    """Unlike evaluate_conditions, this checks all conditions regardless of
    _last_changed_fields — a returning player's reload has no such scoping."""
    state = {"flags": {"entered_cairn": True}}

    labels = condition_evaluator.list_active_condition_labels([_CAIRN_CONDITION], state)

    assert labels == ["The Cairn Presses In"]


def test_list_active_condition_labels_skips_non_dict_entries() -> None:
    labels = condition_evaluator.list_active_condition_labels(
        ["not-a-condition", None], {"flags": {"entered_cairn": True}}
    )

    assert labels == []


def test_list_active_condition_labels_empty_for_no_conditions() -> None:
    assert condition_evaluator.list_active_condition_labels([], {}) == []


def test_previously_active_condition_fires_even_when_unrelated_field_changed() -> None:
    """[P1-LOGIC-3] Conditions active on previous turn must not disappear when
    unrelated fields change on the current turn."""
    poison_condition = {
        "label": "Poisoned",
        "condition_expression": {
            "field": "flags.is_poisoned",
            "op": "==",
            "value": True,
        },
        "narrator_instruction": "Venom pulses through the player's veins.",
    }
    loaded_state = _loaded_state(
        {
            "player": {"sanity": 100},
            "flags": {"is_poisoned": True},
            "_last_changed_fields": ["player.sanity"],
            "_active_conditions": ["Poisoned"],
        },
        [poison_condition],
        turn_count=2,
    )
    result = condition_evaluator.evaluate_conditions(loaded_state)

    assert result.active_instructions == ["Venom pulses through the player's veins."]
    assert result.state["_active_conditions"] == ["Poisoned"]


def test_same_turn_mutation_triggers_later_dependent_condition() -> None:
    """[P2-LOGIC-2] Condition A's Effect C mutation to player.sanity must make
    Condition B (which references player.sanity, listed after A) fire in the
    same turn, even though player.sanity is not itself in _last_changed_fields."""
    lowers_sanity = {
        "label": "Cairn Whispers",
        "condition_expression": {
            "field": "flags.entered_cairn",
            "op": "==",
            "value": True,
        },
        "narrator_instruction": "The cairn whispers.",
        "state_mutation": {"path": "player.sanity", "op": "set", "value": 10},
    }
    reacts_to_low_sanity = {
        "label": "Sanity Critical",
        "condition_expression": {"field": "player.sanity", "op": "<=", "value": 20},
        "narrator_instruction": "The player's mind frays.",
    }
    loaded_state = _loaded_state(
        {
            "player": {"sanity": 100},
            "flags": {"entered_cairn": True},
            "_last_changed_fields": ["flags.entered_cairn"],
        },
        [lowers_sanity, reacts_to_low_sanity],
        turn_count=5,
    )

    result = condition_evaluator.evaluate_conditions(loaded_state)

    assert "The player's mind frays." in result.active_instructions


def test_dependent_condition_listed_before_its_trigger_still_waits_a_turn() -> None:
    """[P2-LOGIC-2] Known, accepted limitation of the single-pass union fix:
    a dependent condition earlier in scenario_conditions than the condition
    that mutates its field can't see that mutation until the next turn."""
    reacts_to_low_sanity = {
        "label": "Sanity Critical",
        "condition_expression": {"field": "player.sanity", "op": "<=", "value": 20},
        "narrator_instruction": "The player's mind frays.",
    }
    lowers_sanity = {
        "label": "Cairn Whispers",
        "condition_expression": {
            "field": "flags.entered_cairn",
            "op": "==",
            "value": True,
        },
        "narrator_instruction": "The cairn whispers.",
        "state_mutation": {"path": "player.sanity", "op": "set", "value": 10},
    }
    loaded_state = _loaded_state(
        {
            "player": {"sanity": 100},
            "flags": {"entered_cairn": True},
            "_last_changed_fields": ["flags.entered_cairn"],
        },
        [reacts_to_low_sanity, lowers_sanity],
        turn_count=5,
    )

    result = condition_evaluator.evaluate_conditions(loaded_state)

    assert "The player's mind frays." not in result.active_instructions


def test_previously_active_condition_stops_firing_when_condition_becomes_false() -> (
    None
):
    """When a condition becomes false, it ceases to be active and is removed
    from _active_conditions."""
    poison_condition = {
        "label": "Poisoned",
        "condition_expression": {
            "field": "flags.is_poisoned",
            "op": "==",
            "value": True,
        },
        "narrator_instruction": "Venom pulses through the player's veins.",
    }
    loaded_state = _loaded_state(
        {
            "player": {"sanity": 100},
            "flags": {"is_poisoned": False},
            "_last_changed_fields": ["flags.is_poisoned"],
            "_active_conditions": ["Poisoned"],
        },
        [poison_condition],
        turn_count=3,
    )
    result = condition_evaluator.evaluate_conditions(loaded_state)

    assert result.active_instructions == []
    assert result.state["_active_conditions"] == []


def test_fact_placed_condition_is_active_but_not_delivered_as_a_directive() -> None:
    fact_condition = {
        **_CAIRN_CONDITION,
        "condition_id": "never-describe",
        "metadata": {"placement": "facts"},
    }
    loaded_state = _loaded_state(
        {"player": {"sanity": 100}, "flags": {"entered_cairn": True}},
        [fact_condition],
    )

    result = condition_evaluator.evaluate_conditions(loaded_state)

    assert result.active_instructions == []
    assert result.fired_condition_ids == ["never-describe"]
