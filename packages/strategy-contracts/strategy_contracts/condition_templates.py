from enum import Enum

from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.conditions import Comparison, ConditionMetric, ConditionOperator
from strategy_contracts.ids import FactionId

MAX_TEMPLATE_VALUE = 10_000


class ConditionTemplate(str, Enum):
    TREASURY_BELOW = "treasury_below"
    TREASURY_ABOVE = "treasury_above"
    STABILITY_BELOW = "stability_below"
    WAR_EXHAUSTION_ABOVE = "war_exhaustion_above"
    REGION_COUNT_BELOW = "region_count_below"
    REGION_COUNT_ABOVE = "region_count_above"
    TURN_AFTER = "turn_after"


TEMPLATE_RULES: dict[ConditionTemplate, tuple[ConditionMetric, ConditionOperator]] = {
    ConditionTemplate.TREASURY_BELOW: (ConditionMetric.TREASURY, ConditionOperator.LT),
    ConditionTemplate.TREASURY_ABOVE: (ConditionMetric.TREASURY, ConditionOperator.GT),
    ConditionTemplate.STABILITY_BELOW: (
        ConditionMetric.STABILITY,
        ConditionOperator.LT,
    ),
    ConditionTemplate.WAR_EXHAUSTION_ABOVE: (
        ConditionMetric.WAR_EXHAUSTION,
        ConditionOperator.GT,
    ),
    ConditionTemplate.REGION_COUNT_BELOW: (
        ConditionMetric.REGION_COUNT,
        ConditionOperator.LT,
    ),
    ConditionTemplate.REGION_COUNT_ABOVE: (
        ConditionMetric.REGION_COUNT,
        ConditionOperator.GT,
    ),
    ConditionTemplate.TURN_AFTER: (ConditionMetric.TURN, ConditionOperator.GT),
}


class ConditionClause(StrictModel):
    template: ConditionTemplate
    faction_id: FactionId
    value: int = Field(ge=0, le=MAX_TEMPLATE_VALUE)


def compile_clause(clause: ConditionClause) -> Comparison:
    metric, operator = TEMPLATE_RULES[clause.template]
    return Comparison(
        metric=metric,
        subject_id=clause.faction_id,
        operator=operator,
        value=clause.value,
    )
