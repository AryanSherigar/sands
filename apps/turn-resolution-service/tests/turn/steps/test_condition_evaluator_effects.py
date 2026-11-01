"""Client effects and authored images fired by conditions: rising edge only,
not gated on the atmosphere tool."""

import uuid

from app.models.turn import LoadedState
from app.turn.steps import condition_evaluator

SCHEMA = {"clock": {"type": "number"}}
TRIGGER = {"field": "clock", "op": ">=", "value": 5}
EFFECT = {
    "kind": "input_takeover",
    "params": {"text": "I feel too much", "lock_ms": 5000, "type_ms_per_char": 60},
}
IMAGE_URL = "https://media.example/poster.png"


def _loaded(state: dict, conditions: list, turn_count: int = 0) -> LoadedState:
    return LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "enabled_tools": [],
            "state_schema": SCHEMA,
            "entities": [],
            "rule_invariants": [],
            "scenario_conditions": conditions,
        },
        state=state,
        turn_count=turn_count,
        checkpoint=None,
    )


def _condition(**metadata: object) -> dict:
    return {
        "condition_id": "c1",
        "label": "c1",
        "narrator_instruction": "",
        "condition_expression": TRIGGER,
        "metadata": dict(metadata),
    }


def test_effect_fires_when_condition_turns_true() -> None:
    result = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 5}, [_condition(client_effect=EFFECT)])
    )
    assert [effect.kind for effect in result.fired_effects] == ["input_takeover"]
    assert result.fired_effects[0].params["text"] == "I feel too much"


def test_effect_fires_on_rising_edge_only() -> None:
    first = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 5}, [_condition(client_effect=EFFECT)])
    )
    second = condition_evaluator.evaluate_conditions(
        _loaded(first.state, [_condition(client_effect=EFFECT)], turn_count=1)
    )
    assert second.fired_effects == []


def test_authored_image_url_is_reported() -> None:
    result = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 5}, [_condition(authored_image_url=IMAGE_URL)])
    )
    assert result.authored_image_url == IMAGE_URL


def test_nothing_fires_without_metadata() -> None:
    result = condition_evaluator.evaluate_conditions(
        _loaded({"clock": 5}, [_condition()])
    )
    assert result.fired_effects == []
    assert result.authored_image_url is None
