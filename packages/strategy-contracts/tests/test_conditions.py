import pytest
from pydantic import TypeAdapter, ValidationError
from strategy_contracts.conditions import (
    AllOf,
    AnyOf,
    Comparison,
    Condition,
    ConditionMetric,
    ConditionOperator,
    Negation,
    condition_depth,
)

CONDITION_ADAPTER = TypeAdapter(Condition)


def _comparison() -> Comparison:
    return Comparison(
        metric=ConditionMetric.TREASURY, operator=ConditionOperator.GT, value=10
    )


def test_comparison_depth_is_one() -> None:
    assert condition_depth(_comparison()) == 1


def test_nested_condition_parses_from_json_and_measures_depth() -> None:
    nested = AllOf(
        conditions=[
            _comparison(),
            Negation(condition=AnyOf(conditions=[_comparison()])),
        ]
    )
    restored = CONDITION_ADAPTER.validate_json(nested.model_dump_json())
    assert restored == nested
    assert condition_depth(restored) == 4


def test_unknown_kind_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CONDITION_ADAPTER.validate_python({"kind": "maybe"})


def test_float_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Comparison(
            metric=ConditionMetric.TREASURY,
            operator=ConditionOperator.GT,
            value=1.5,
        )


def test_month_is_a_faction_scoped_metric() -> None:
    from strategy_contracts.conditions import ConditionScope, metric_scope

    assert ConditionMetric.MONTH.value == "month"
    assert metric_scope(ConditionMetric.MONTH) is ConditionScope.FACTION
