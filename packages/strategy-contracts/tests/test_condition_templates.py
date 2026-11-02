import pytest
from pydantic import ValidationError
from strategy_contracts.condition_templates import (
    ConditionClause,
    ConditionTemplate,
    compile_clause,
)
from strategy_contracts.conditions import Comparison, ConditionMetric, ConditionOperator

TEMPLATE_CASES = [
    (ConditionTemplate.TREASURY_BELOW, ConditionMetric.TREASURY, ConditionOperator.LT),
    (ConditionTemplate.TREASURY_ABOVE, ConditionMetric.TREASURY, ConditionOperator.GT),
    (
        ConditionTemplate.STABILITY_BELOW,
        ConditionMetric.STABILITY,
        ConditionOperator.LT,
    ),
    (
        ConditionTemplate.WAR_EXHAUSTION_ABOVE,
        ConditionMetric.WAR_EXHAUSTION,
        ConditionOperator.GT,
    ),
    (
        ConditionTemplate.REGION_COUNT_BELOW,
        ConditionMetric.REGION_COUNT,
        ConditionOperator.LT,
    ),
    (
        ConditionTemplate.REGION_COUNT_ABOVE,
        ConditionMetric.REGION_COUNT,
        ConditionOperator.GT,
    ),
    (ConditionTemplate.TURN_AFTER, ConditionMetric.TURN, ConditionOperator.GT),
]


@pytest.mark.parametrize(("template", "metric", "operator"), TEMPLATE_CASES)
def test_template_compiles_to_comparison(template, metric, operator) -> None:
    clause = ConditionClause(template=template, faction_id="aa", value=7)
    compiled = compile_clause(clause)
    assert isinstance(compiled, Comparison)
    assert (compiled.metric, compiled.operator) == (metric, operator)
    assert compiled.subject_id == "aa"
    assert compiled.value == 7


def test_negative_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ConditionClause(
            template=ConditionTemplate.TREASURY_BELOW, faction_id="aa", value=-1
        )


def test_unknown_template_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ConditionClause.model_validate(
            {"template": "owns_moon", "faction_id": "aa", "value": 1}
        )


@pytest.mark.parametrize(
    "template", [ConditionTemplate.OWNS_REGION, ConditionTemplate.LOSES_REGION]
)
def test_region_templates_need_a_region_and_do_not_compile(template) -> None:
    with pytest.raises(ValidationError):
        ConditionClause(template=template, faction_id="aa")
    clause = ConditionClause(template=template, faction_id="aa", region_id="reg_gate")
    assert clause.value == 0
    with pytest.raises(ValueError):
        compile_clause(clause)


def test_numeric_templates_refuse_a_region_and_omit_it_when_absent() -> None:
    with pytest.raises(ValidationError):
        ConditionClause(
            template=ConditionTemplate.TREASURY_BELOW,
            faction_id="aa",
            value=5,
            region_id="reg_gate",
        )
    numeric = ConditionClause(
        template=ConditionTemplate.TREASURY_BELOW, faction_id="aa", value=5
    )
    assert "region_id" not in numeric.model_dump(mode="json")
