"""Unit tests for Core API's condition_state.py evaluator mirror."""

import pytest
from app.services.condition_state import list_active_condition_labels


def test_list_active_condition_labels_matches_true_condition() -> None:
    conditions = [
        {
            "label": "Low Health",
            "condition_expression": {
                "field": "player.health",
                "op": "<=",
                "value": 10,
            },
        },
        {
            "label": "High Health",
            "condition_expression": {
                "field": "player.health",
                "op": ">=",
                "value": 50,
            },
        },
    ]
    state = {"player": {"health": 5}}
    labels = list_active_condition_labels(conditions, state)
    assert labels == ["Low Health"]


def test_list_active_condition_labels_cross_field_ref() -> None:
    conditions = [
        {
            "label": "At or Below Max",
            "condition_expression": {
                "field": "player.health",
                "op": "<=",
                "ref": "player.max_health",
            },
        }
    ]
    state = {"player": {"health": 80, "max_health": 100}}
    assert list_active_condition_labels(conditions, state) == ["At or Below Max"]

    over_cap_state = {"player": {"health": 120, "max_health": 100}}
    assert list_active_condition_labels(conditions, over_cap_state) == []


def test_list_active_condition_labels_dotted_string_literal_not_resolved_as_ref() -> (
    None
):
    conditions = [
        {
            "label": "Has Scroll",
            "condition_expression": {
                "field": "player.item",
                "op": "==",
                "value": "scroll.txt",
            },
        }
    ]
    # State has a matching 'scroll.txt' path with an unrelated value
    state = {"player": {"item": "scroll.txt"}, "scroll": {"txt": "other"}}
    assert list_active_condition_labels(conditions, state) == ["Has Scroll"]


def test_list_active_condition_labels_multiple_connectives_raises_error() -> None:
    conditions = [
        {
            "label": "Ambiguous",
            "condition_expression": {
                "field": "player.health",
                "op": "<=",
                "value": 10,
                "AND": {"field": "player.health", "op": ">=", "value": 0},
                "OR": {"field": "flags.escaped", "op": "==", "value": True},
            },
        }
    ]
    with pytest.raises(ValueError, match="at most one connective"):
        list_active_condition_labels(conditions, {"player": {"health": 5}})


def test_one_shot_condition_is_omitted_once_fired() -> None:
    conditions = [
        {
            "condition_id": "c1",
            "label": "Alarm",
            "is_one_shot": True,
            "condition_expression": {"field": "clock", "op": ">=", "value": 5},
        }
    ]

    assert list_active_condition_labels(conditions, {"clock": 6}) == ["Alarm"]
    assert (
        list_active_condition_labels(
            conditions, {"clock": 6, "_fired_conditions": ["c1"]}
        )
        == []
    )


def test_a_condition_that_reads_a_hidden_field_is_not_listed_for_the_client() -> None:
    from app.services.condition_state import list_active_condition_labels

    schema = {
        "clock": {"type": "number"},
        "regime": {
            "type": "object",
            "hidden": True,
            "fields": {"safe": {"type": "boolean"}},
        },
    }
    conditions = [
        {
            "label": "Late",
            "condition_expression": {"field": "clock", "op": ">=", "value": 5},
        },
        {
            "label": "Regime tell",
            "condition_expression": {
                "field": "clock",
                "op": ">=",
                "value": 5,
                "AND": {"field": "regime.safe", "op": "==", "value": False},
            },
        },
        {
            "label": "Ref to hidden",
            "condition_expression": {
                "field": "clock",
                "op": ">=",
                "ref": "regime.safe",
            },
        },
    ]
    state = {"clock": 6, "regime": {"safe": False}}

    assert list_active_condition_labels(conditions, state, schema) == ["Late"]
    assert list_active_condition_labels(conditions[:2], state) == [
        "Late",
        "Regime tell",
    ]
