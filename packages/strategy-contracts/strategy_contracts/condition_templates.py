from enum import Enum

from pydantic import (
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)

from strategy_contracts.base import StrictModel
from strategy_contracts.conditions import Comparison, ConditionMetric, ConditionOperator
from strategy_contracts.ids import FactionId, RegionId

MAX_TEMPLATE_VALUE = 10_000


class ConditionTemplate(str, Enum):
    TREASURY_BELOW = "treasury_below"
    TREASURY_ABOVE = "treasury_above"
    STABILITY_BELOW = "stability_below"
    WAR_EXHAUSTION_ABOVE = "war_exhaustion_above"
    REGION_COUNT_BELOW = "region_count_below"
    REGION_COUNT_ABOVE = "region_count_above"
    TURN_AFTER = "turn_after"
    OWNS_REGION = "owns_region"
    LOSES_REGION = "loses_region"


REGION_TEMPLATES = frozenset(
    {ConditionTemplate.OWNS_REGION, ConditionTemplate.LOSES_REGION}
)

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
    value: int = Field(default=0, ge=0, le=MAX_TEMPLATE_VALUE)
    region_id: RegionId | None = None

    @model_validator(mode="after")
    def validate_region_matches_template(self) -> "ConditionClause":
        needs_region = self.template in REGION_TEMPLATES
        if needs_region and self.region_id is None:
            raise ValueError(f"{self.template.value} needs a region")
        if not needs_region and self.region_id is not None:
            raise ValueError(f"{self.template.value} takes no region")
        return self

    @model_serializer(mode="wrap")
    def omit_absent_region(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        document = handler(self)
        if document.get("region_id") is None:
            document.pop("region_id", None)
        return document


def compile_clause(clause: ConditionClause) -> Comparison:
    if clause.template in REGION_TEMPLATES:
        raise ValueError(f"{clause.template.value} reads region ownership directly")
    metric, operator = TEMPLATE_RULES[clause.template]
    return Comparison(
        metric=metric,
        subject_id=clause.faction_id,
        operator=operator,
        value=clause.value,
    )
