from pydantic import Field, field_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.conditions import (
    AllOf,
    AnyOf,
    Comparison,
    Condition,
    ConditionMetric,
    Negation,
)
from strategy_contracts.ids import EntityId, FactionId
from strategy_contracts.limits import MAX_NEGOTIATION_TRIGGERS
from strategy_contracts.terms import TermKind

DEFAULT_BASE_ACCEPT = 20
DEFAULT_AXIS_WEIGHT = 5
DEFAULT_OPINION_DIVISOR = 4
DEFAULT_HAGGLE_MARGIN = 20
DEFAULT_PACT_VALUE_PER_TURN = 6
DEFAULT_MAX_PACT_TURNS = 12
DEFAULT_TRIGGER_COOLDOWN_TURNS = 5
PRICED_TERM_KINDS = frozenset(
    {TermKind.NON_AGGRESSION, TermKind.ALLIANCE, TermKind.VASSAL}
)
PEACE_TERM_KINDS = (
    TermKind.PEACE,
    TermKind.CEDE_REGION,
    TermKind.PAY_GOLD,
    TermKind.TRIBUTE,
    TermKind.RELEASE_PRISONERS,
    TermKind.HOSTAGE,
    TermKind.TRADE_DEAL,
)
TRIGGER_METRICS = frozenset(
    {
        ConditionMetric.TURN,
        ConditionMetric.TREASURY,
        ConditionMetric.STABILITY,
        ConditionMetric.WAR_EXHAUSTION,
        ConditionMetric.REGION_COUNT,
        ConditionMetric.IS_FACTION_DESTROYED,
    }
)


def _default_allowed_term_kinds() -> list[TermKind]:
    return [TermKind.NON_AGGRESSION]


def condition_metrics(condition: Condition) -> set[ConditionMetric]:
    if isinstance(condition, Comparison):
        return {condition.metric}
    if isinstance(condition, Negation):
        return condition_metrics(condition.condition)
    assert isinstance(condition, (AllOf, AnyOf))
    return {
        metric for child in condition.conditions for metric in condition_metrics(child)
    }


class NegotiationTrigger(StrictModel):
    """An AI faction approaches the player once its condition holds."""

    id: EntityId
    initiator_faction_id: FactionId
    condition: Condition
    is_declinable: bool = True
    cooldown_turns: int = Field(default=DEFAULT_TRIGGER_COOLDOWN_TURNS, ge=1)

    @field_validator("condition")
    @classmethod
    def validate_supported_metrics(cls, condition: Condition) -> Condition:
        unsupported = condition_metrics(condition) - TRIGGER_METRICS
        if unsupported:
            names = ", ".join(sorted(metric.value for metric in unsupported))
            raise ValueError(f"trigger conditions cannot use: {names}")
        return condition


class NegotiationRules(StrictModel):
    base_accept: int = DEFAULT_BASE_ACCEPT
    axis_weight: int = Field(default=DEFAULT_AXIS_WEIGHT, ge=0)
    opinion_divisor: int = Field(default=DEFAULT_OPINION_DIVISOR, ge=1)
    haggle_margin: int = Field(default=DEFAULT_HAGGLE_MARGIN, ge=0)
    pact_value_per_turn: int = Field(default=DEFAULT_PACT_VALUE_PER_TURN, ge=1)
    max_pact_turns: int = Field(default=DEFAULT_MAX_PACT_TURNS, ge=1)
    allowed_term_kinds: list[TermKind] = Field(
        default_factory=_default_allowed_term_kinds, min_length=1
    )
    triggers: list[NegotiationTrigger] = Field(
        default_factory=list, max_length=MAX_NEGOTIATION_TRIGGERS
    )

    @field_validator("allowed_term_kinds")
    @classmethod
    def validate_priced_kinds(cls, kinds: list[TermKind]) -> list[TermKind]:
        unpriced = [kind.value for kind in kinds if kind not in PRICED_TERM_KINDS]
        if unpriced:
            raise ValueError(f"term kinds have no price yet: {', '.join(unpriced)}")
        return kinds
