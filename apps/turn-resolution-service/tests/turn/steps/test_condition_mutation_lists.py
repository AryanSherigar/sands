"""Multi-mutation and fire-once behaviour of condition_evaluator."""

import uuid

from app.models.turn import LoadedState
from app.turn.steps import condition_evaluator
from app.turn.steps.condition_evaluator import effective_mutations

_SCHEMA = {
    "sanity": {"type": "number", "min": 0, "max": 100},
    "alarm": {"type": "boolean"},
    "clock": {"type": "number"},
    "count": {"type": "number"},
}
_TRIGGER = {"field": "clock", "op": ">=", "value": 5}


def _set(path: str, value: object, op: str = "set") -> dict[str, object]:
    return {"path": path, "op": op, "value": value}


def _loaded(state: dict, conditions: list, turn_count: int = 0) -> LoadedState:
    return LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "state_schema": _SCHEMA,
            "entities": [],
            "rule_invariants": [],
            "scenario_conditions": conditions,
        },
        state=state,
        turn_count=turn_count,
        checkpoint=None,
    )


def _condition(**overrides) -> dict[str, object]:
    base = {
        "condition_id": "c1",
        "label": "Alarm",
        "condition_expression": _TRIGGER,
        "narrator_instruction": "The alarm sounds.",
    }
    base.update(overrides)
    return base


def test_effective_mutations_reads_list_then_legacy_single() -> None:
    listed = {"state_mutations": [_set("a", 1)], "state_mutation": _set("b", 2)}

    assert effective_mutations(listed) == [_set("a", 1)]
    assert effective_mutations({"state_mutation": _set("b", 2)}) == [_set("b", 2)]
    assert effective_mutations({"state_mutations": []}) == []
    assert effective_mutations({}) == []


def test_all_listed_mutations_apply_in_order() -> None:
    condition = _condition(
        state_mutations=[_set("sanity", 40), _set("alarm", True), _set("count", 3)]
    )

    result = condition_evaluator.evaluate_conditions(_loaded({"clock": 6}, [condition]))

    assert result.state["sanity"] == 40
    assert result.state["alarm"] is True
    assert result.state["count"] == 3
    assert {"sanity", "alarm", "count"} <= result.mutated_paths


def test_later_mutation_on_same_path_wins() -> None:
    condition = _condition(
        state_mutations=[_set("sanity", 40), _set("sanity", 10, "decrement")]
    )

    result = condition_evaluator.evaluate_conditions(_loaded({"clock": 6}, [condition]))

    assert result.state["sanity"] == 30


def test_one_invalid_mutation_does_not_stop_the_others() -> None:
    condition = _condition(state_mutations=[_set("sanity", 500), _set("alarm", True)])

    result = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 6, "sanity": 50}, [condition])
    )

    assert result.state["sanity"] == 50
    assert result.state["alarm"] is True
    assert "sanity" not in result.mutated_paths


def test_trigger_is_not_reevaluated_between_mutations() -> None:
    condition = _condition(state_mutations=[_set("clock", 0), _set("alarm", True)])

    result = condition_evaluator.evaluate_conditions(_loaded({"clock": 6}, [condition]))

    assert result.state["clock"] == 0
    assert result.state["alarm"] is True


def test_legacy_single_mutation_in_old_snapshot_still_applies() -> None:
    condition = _condition(state_mutation=_set("alarm", True))

    result = condition_evaluator.evaluate_conditions(_loaded({"clock": 6}, [condition]))

    assert result.state["alarm"] is True


def test_one_shot_condition_fires_once_and_records_itself() -> None:
    condition = _condition(is_one_shot=True, state_mutations=[_set("count", 1)])

    first = condition_evaluator.evaluate_conditions(_loaded({"clock": 6}, [condition]))
    second = condition_evaluator.evaluate_conditions(
        _loaded(first.state, [condition], turn_count=1)
    )

    assert first.active_instructions == ["The alarm sounds."]
    assert first.state["_fired_conditions"] == ["c1"]
    assert "_fired_conditions" in first.mutated_paths
    assert second.active_instructions == []
    assert second.state["count"] == 1


def test_one_shot_that_is_not_true_is_not_marked_fired() -> None:
    condition = _condition(is_one_shot=True)

    result = condition_evaluator.evaluate_conditions(_loaded({"clock": 1}, [condition]))

    assert "_fired_conditions" not in result.state


def test_retry_from_the_same_persisted_state_fires_again() -> None:
    condition = _condition(is_one_shot=True)
    persisted = {"clock": 6}

    first = condition_evaluator.evaluate_conditions(_loaded(persisted, [condition]))
    retry = condition_evaluator.evaluate_conditions(_loaded(persisted, [condition]))

    assert (
        first.active_instructions == retry.active_instructions == ["The alarm sounds."]
    )
    assert "_fired_conditions" not in persisted


def test_non_one_shot_condition_keeps_firing() -> None:
    condition = _condition(state_mutations=[_set("count", 1, "increment")])

    first = condition_evaluator.evaluate_conditions(_loaded({"clock": 6}, [condition]))
    second = condition_evaluator.evaluate_conditions(
        _loaded(first.state, [condition], turn_count=1)
    )

    assert second.state["count"] == 2


def test_status_badges_omit_a_one_shot_once_fired() -> None:
    condition = _condition(is_one_shot=True)

    before = condition_evaluator.list_active_condition_labels([condition], {"clock": 6})
    after = condition_evaluator.list_active_condition_labels(
        [condition], {"clock": 6, "_fired_conditions": ["c1"]}
    )

    assert before == ["Alarm"]
    assert after == []


def test_one_shot_whose_every_mutation_is_rejected_is_not_marked_fired() -> None:
    condition = _condition(is_one_shot=True, state_mutations=[_set("sanity", 500)])

    first = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 6, "sanity": 50}, [condition])
    )

    assert "_fired_conditions" not in first.state
    assert first.state["sanity"] == 50


def test_one_shot_with_a_rejected_mutation_is_still_fired_when_another_applies() -> (
    None
):
    condition = _condition(
        is_one_shot=True,
        state_mutations=[_set("sanity", 500), _set("alarm", True)],
    )

    result = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 6, "sanity": 50}, [condition])
    )

    assert result.state["_fired_conditions"] == ["c1"]


def test_a_condition_that_reads_a_hidden_field_is_not_listed_for_the_client() -> None:
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
    ]
    state = {"clock": 6, "regime": {"safe": False}}

    shown = condition_evaluator.list_active_condition_labels(conditions, state, schema)

    assert shown == ["Late"]
    assert condition_evaluator.list_active_condition_labels(conditions, state) == [
        "Late",
        "Regime tell",
    ]
