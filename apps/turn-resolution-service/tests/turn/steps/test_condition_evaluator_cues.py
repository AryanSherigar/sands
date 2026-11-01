"""Sensory cues fired by conditions: rising edge only, atmosphere-gated, capped."""

import uuid

from app.models.turn import LoadedState
from app.turn.steps import condition_evaluator

SCHEMA = {"clock": {"type": "number"}, "alarm": {"type": "boolean"}}
TRIGGER = {"field": "clock", "op": ">=", "value": 5}


def _loaded(
    state: dict, conditions: list, tools: list[str] | None = None, turn_count: int = 0
) -> LoadedState:
    return LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "enabled_tools": ["atmosphere"] if tools is None else tools,
            "state_schema": SCHEMA,
            "entities": [],
            "rule_invariants": [],
            "scenario_conditions": conditions,
        },
        state=state,
        turn_count=turn_count,
        checkpoint=None,
    )


def _condition(condition_id: str = "c1", **overrides) -> dict:
    base = {
        "condition_id": condition_id,
        "label": f"Condition {condition_id}",
        "condition_expression": TRIGGER,
        "narrator_instruction": "The phone rings.",
        "sensory_cue": "phone_ring",
        "cut_ambient": True,
        "silence_duration_ms": 1500,
    }
    base.update(overrides)
    return base


def test_cue_fires_when_the_condition_becomes_active() -> None:
    result = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 6}, [_condition()])
    )

    assert [cue.model_dump() for cue in result.fired_cues] == [
        {"cue": "phone_ring", "cut_ambient": True, "silence_duration_ms": 1500}
    ]


def test_cue_is_not_resent_while_the_condition_stays_true() -> None:
    first = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 6}, [_condition()])
    )
    second = condition_evaluator.evaluate_conditions(
        _loaded(first.state, [_condition()], turn_count=1)
    )

    assert len(first.fired_cues) == 1
    assert second.fired_cues == []


def test_cue_fires_again_after_the_condition_goes_false_and_true_again() -> None:
    state = {"clock": 6}
    first = condition_evaluator.evaluate_conditions(_loaded(state, [_condition()]))
    gone = condition_evaluator.evaluate_conditions(
        _loaded({**first.state, "clock": 1}, [_condition()], turn_count=1)
    )
    back = condition_evaluator.evaluate_conditions(
        _loaded({**gone.state, "clock": 7}, [_condition()], turn_count=2)
    )

    assert len(back.fired_cues) == 1


def test_cues_are_ordered_by_firing_order_and_capped_at_three() -> None:
    conditions = [
        _condition(f"c{i}", sensory_cue=cue)
        for i, cue in enumerate(
            ["phone_ring", "heavy_knock", "light_buzz", "lamp_click", "paper_rustle"]
        )
    ]

    result = condition_evaluator.evaluate_conditions(_loaded({"clock": 6}, conditions))

    assert [cue.cue for cue in result.fired_cues] == [
        "phone_ring",
        "heavy_knock",
        "light_buzz",
    ]


def test_no_cue_when_atmosphere_is_off() -> None:
    result = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 6}, [_condition()], tools=[])
    )

    assert result.fired_cues == []
    assert result.active_instructions == ["The phone rings."]


def test_condition_without_a_cue_fires_none() -> None:
    result = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 6}, [_condition(sensory_cue=None)])
    )

    assert result.fired_cues == []


def test_one_shot_cue_fires_once_across_turns() -> None:
    condition = _condition(is_one_shot=True)
    first = condition_evaluator.evaluate_conditions(_loaded({"clock": 6}, [condition]))
    second = condition_evaluator.evaluate_conditions(
        _loaded({**first.state, "clock": 1}, [condition], turn_count=1)
    )
    third = condition_evaluator.evaluate_conditions(
        _loaded({**second.state, "clock": 9}, [condition], turn_count=2)
    )

    assert len(first.fired_cues) == 1
    assert third.fired_cues == []


def test_missing_cue_settings_fall_back_to_the_defaults() -> None:
    bare = _condition()
    del bare["cut_ambient"]
    del bare["silence_duration_ms"]

    result = condition_evaluator.evaluate_conditions(_loaded({"clock": 6}, [bare]))

    assert result.fired_cues[0].model_dump() == {
        "cue": "phone_ring",
        "cut_ambient": True,
        "silence_duration_ms": 800,
    }
