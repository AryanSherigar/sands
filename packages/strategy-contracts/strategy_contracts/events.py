from enum import Enum

from pydantic import Field, model_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.conditions import (
    SUBJECT_PLACEHOLDER,
    Comparison,
    Condition,
    ConditionMetric,
    ConditionScope,
    SubjectRef,
    iter_comparisons,
    metric_scope,
)
from strategy_contracts.ids import EntityId, EventId
from strategy_contracts.limits import (
    MAX_CAUSE_METRICS,
    MAX_EFFECT_AMOUNT,
    MAX_EVENT_CHOICES,
    MAX_EVENT_ORDER_COST,
    MAX_NAME_CHARS,
    MAX_SCAR_POINTS,
    MAX_SEVERITY_TIERS,
    MAX_TEXT_CHARS,
    MIN_EVENT_CHOICES,
)

DEFAULT_EVENT_ORDER_COST = 1
DEFAULT_SCAR_DECAY_PER_TURN = 1
DEFAULT_POINTS_PER_TIER_BUMP = 20
DEFAULT_NEGLECT_SCAR = 30
DEFAULT_TIER_CALM_TURNS = 3
MAX_TERMS_PER_CHOICE = 8

EVENT_SUBJECT_SCOPES = frozenset(
    {
        ConditionScope.REGION,
        ConditionScope.GOVERNOR,
        ConditionScope.ARMY,
        ConditionScope.FACTION,
    }
)
READABLE_SCOPES: dict[ConditionScope, frozenset[ConditionScope]] = {
    ConditionScope.REGION: frozenset(
        {ConditionScope.FACTION, ConditionScope.REGION, ConditionScope.GOVERNOR}
    ),
    ConditionScope.GOVERNOR: frozenset(
        {ConditionScope.FACTION, ConditionScope.REGION, ConditionScope.GOVERNOR}
    ),
    ConditionScope.ARMY: frozenset(
        {ConditionScope.FACTION, ConditionScope.REGION, ConditionScope.ARMY}
    ),
    ConditionScope.FACTION: frozenset({ConditionScope.FACTION}),
}


class EffectKind(str, Enum):
    GOLD = "gold"
    UNREST = "unrest"
    REGION_UNREST = "region_unrest"
    STABILITY = "stability"
    MANPOWER = "manpower"
    REPUTATION = "reputation"
    OPINION = "opinion"
    GOVERNOR_OPINION = "governor_opinion"
    ARMY_MORALE = "army_morale"
    ADD_MEMORY = "add_memory"
    START_DIPLOMATIC_PLAY = "start_diplomatic_play"
    RULER_DIES = "ruler_dies"


SUPPORTED_EFFECT_KINDS = frozenset(
    {
        EffectKind.GOLD,
        EffectKind.UNREST,
        EffectKind.REGION_UNREST,
        EffectKind.STABILITY,
        EffectKind.MANPOWER,
        EffectKind.REPUTATION,
        EffectKind.GOVERNOR_OPINION,
        EffectKind.ARMY_MORALE,
        EffectKind.RULER_DIES,
    }
)


class EffectSpec(StrictModel):
    """A whole-number delta. UNREST hits every region of the acting faction;
    the REGION_/GOVERNOR_/ARMY_ kinds hit the event subject or its related
    region, governor or army when ``target_id`` is ``$subject``. RULER_DIES
    ignores ``amount`` and removes the ruler of ``target_id`` (default: the
    acting faction); a player ruler is never removed."""

    kind: EffectKind
    amount: int = Field(default=0, ge=-MAX_EFFECT_AMOUNT, le=MAX_EFFECT_AMOUNT)
    target_id: SubjectRef | None = None

    @model_validator(mode="after")
    def validate_kind_is_supported(self) -> "EffectSpec":
        if self.kind not in SUPPORTED_EFFECT_KINDS:
            raise ValueError(f"effect {self.kind.value} is not supported yet")
        return self


class EventChoice(StrictModel):
    id: EntityId
    label_hint: str = Field(max_length=MAX_TEXT_CHARS)
    effects: list[EffectSpec] = Field(max_length=MAX_TERMS_PER_CHOICE)
    order_cost: int = Field(
        default=DEFAULT_EVENT_ORDER_COST, ge=1, le=MAX_EVENT_ORDER_COST
    )
    scar_amount: int = Field(default=0, ge=0, le=MAX_SCAR_POINTS)


class SeverityTier(StrictModel):
    level: int = Field(ge=1, le=MAX_SEVERITY_TIERS)
    trigger: Condition
    choice_ids: list[EntityId] | None = None


class ScarSpec(StrictModel):
    """A scar of ``points_per_tier_bump`` points raises the tier the subject
    is judged at by one rung, so repeat trouble arrives sooner."""

    decay_per_turn: int = Field(
        default=DEFAULT_SCAR_DECAY_PER_TURN, ge=1, le=MAX_SCAR_POINTS
    )
    points_per_tier_bump: int = Field(
        default=DEFAULT_POINTS_PER_TIER_BUMP, ge=1, le=MAX_SCAR_POINTS
    )


class EventDefinition(StrictModel):
    id: EventId
    name: str = Field(min_length=1, max_length=MAX_NAME_CHARS)
    subject_kind: ConditionScope
    tiers: list[SeverityTier] = Field(min_length=1, max_length=MAX_SEVERITY_TIERS)
    choices: list[EventChoice] = Field(
        min_length=MIN_EVENT_CHOICES, max_length=MAX_EVENT_CHOICES
    )
    neglect_effects: list[EffectSpec] = Field(
        min_length=1, max_length=MAX_TERMS_PER_CHOICE
    )
    neglect_scar: int = Field(default=DEFAULT_NEGLECT_SCAR, ge=0, le=MAX_SCAR_POINTS)
    scar: ScarSpec = Field(default_factory=ScarSpec)
    tier_calm_turns: int = Field(default=DEFAULT_TIER_CALM_TURNS, ge=1)
    cause_key: EntityId
    cause_metrics: list[ConditionMetric] = Field(
        default_factory=list, max_length=MAX_CAUSE_METRICS
    )

    @model_validator(mode="after")
    def validate_shape(self) -> "EventDefinition":
        self._validate_subject_kind()
        self._validate_tier_levels()
        self._validate_choice_ids()
        self._validate_trigger_scopes()
        return self

    def _validate_subject_kind(self) -> None:
        if self.subject_kind not in EVENT_SUBJECT_SCOPES:
            raise ValueError(f"events cannot be about a {self.subject_kind.value}")

    def _validate_tier_levels(self) -> None:
        levels = [tier.level for tier in self.tiers]
        if levels != sorted(set(levels)):
            raise ValueError("tier levels must strictly increase")

    def _validate_choice_ids(self) -> None:
        ids = [choice.id for choice in self.choices]
        if len(set(ids)) != len(ids):
            raise ValueError("choice ids must be unique")
        for tier in self.tiers:
            unknown = set(tier.choice_ids or []) - set(ids)
            if unknown:
                raise ValueError(f"tier names unknown choices: {sorted(unknown)}")

    def _validate_trigger_scopes(self) -> None:
        readable = READABLE_SCOPES[self.subject_kind]
        for tier in self.tiers:
            for comparison in iter_comparisons(tier.trigger):
                self._validate_comparison_scope(comparison, readable)

    def _validate_comparison_scope(
        self, comparison: Comparison, readable: frozenset[ConditionScope]
    ) -> None:
        scope = metric_scope(comparison.metric)
        if scope not in readable:
            raise ValueError(
                f"{comparison.metric.value} cannot be read by a "
                f"{self.subject_kind.value} event"
            )
        if scope is not ConditionScope.FACTION and (
            comparison.subject_id != SUBJECT_PLACEHOLDER
        ):
            raise ValueError(
                f"{comparison.metric.value} must use {SUBJECT_PLACEHOLDER}"
            )
