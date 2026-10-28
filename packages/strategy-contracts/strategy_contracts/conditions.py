from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import EntityId

SUBJECT_PLACEHOLDER = "$subject"
MAX_UNREST_THRESHOLD = 100
SubjectRef = EntityId | Literal["$subject"]


class ConditionMetric(str, Enum):
    REGION_COUNT = "region_count"
    TREASURY = "treasury"
    STABILITY = "stability"
    WAR_EXHAUSTION = "war_exhaustion"
    OWNS_REGION = "owns_region"
    HOLDS_CAPITAL_OF = "holds_capital_of"
    TURN = "turn"
    IS_FACTION_DESTROYED = "is_faction_destroyed"
    IS_RULER_ALIVE = "is_ruler_alive"
    IS_AT_PEACE_WITH_ALL = "is_at_peace_with_all"
    REGION_UNREST = "region_unrest"
    GOVERNOR_OPINION = "governor_opinion"
    ARMY_UNPAID_TURNS = "army_unpaid_turns"
    ARMY_MORALE = "army_morale"
    REGIONS_WITH_UNREST_AT_LEAST = "regions_with_unrest_at_least"


class ConditionScope(str, Enum):
    FACTION = "faction"
    REGION = "region"
    GOVERNOR = "governor"
    LEADER = "leader"
    ARMY = "army"


METRIC_SCOPES: dict[ConditionMetric, ConditionScope] = {
    ConditionMetric.REGION_UNREST: ConditionScope.REGION,
    ConditionMetric.GOVERNOR_OPINION: ConditionScope.GOVERNOR,
    ConditionMetric.ARMY_UNPAID_TURNS: ConditionScope.ARMY,
    ConditionMetric.ARMY_MORALE: ConditionScope.ARMY,
}


def metric_scope(metric: ConditionMetric) -> ConditionScope:
    return METRIC_SCOPES.get(metric, ConditionScope.FACTION)


class ConditionOperator(str, Enum):
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    GTE = "gte"
    GT = "gt"


class Comparison(StrictModel):
    kind: Literal["comparison"] = "comparison"
    metric: ConditionMetric
    subject_id: SubjectRef | None = None
    operator: ConditionOperator
    value: int
    threshold: int | None = Field(default=None, ge=0, le=MAX_UNREST_THRESHOLD)

    @model_validator(mode="after")
    def validate_threshold_matches_metric(self) -> "Comparison":
        needs_threshold = self.metric is ConditionMetric.REGIONS_WITH_UNREST_AT_LEAST
        if needs_threshold and self.threshold is None:
            raise ValueError(f"{self.metric.value} needs a threshold")
        if not needs_threshold and self.threshold is not None:
            raise ValueError(f"{self.metric.value} takes no threshold")
        return self


class AllOf(StrictModel):
    kind: Literal["all_of"] = "all_of"
    conditions: list["Condition"]


class AnyOf(StrictModel):
    kind: Literal["any_of"] = "any_of"
    conditions: list["Condition"]


class Negation(StrictModel):
    kind: Literal["not"] = "not"
    condition: "Condition"


Condition = Annotated[
    Comparison | AllOf | AnyOf | Negation,
    Field(discriminator="kind"),
]

AllOf.model_rebuild()
AnyOf.model_rebuild()
Negation.model_rebuild()


def condition_depth(condition: Comparison | AllOf | AnyOf | Negation) -> int:
    if isinstance(condition, Comparison):
        return 1
    if isinstance(condition, Negation):
        return 1 + condition_depth(condition.condition)
    child_depths = [condition_depth(child) for child in condition.conditions]
    return 1 + max(child_depths, default=0)


def iter_comparisons(
    condition: Comparison | AllOf | AnyOf | Negation,
) -> list[Comparison]:
    if isinstance(condition, Comparison):
        return [condition]
    if isinstance(condition, Negation):
        return iter_comparisons(condition.condition)
    return [
        comparison
        for child in condition.conditions
        for comparison in iter_comparisons(child)
    ]
