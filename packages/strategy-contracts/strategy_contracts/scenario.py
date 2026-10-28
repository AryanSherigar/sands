from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from strategy_contracts.ai import AiTuning
from strategy_contracts.alliance import AllianceTuning
from strategy_contracts.base import StrictModel
from strategy_contracts.battle import BattleTuning
from strategy_contracts.coalition import CoalitionTuning
from strategy_contracts.conditions import Condition
from strategy_contracts.diplomacy import DiplomacyTuning
from strategy_contracts.endings import EndingsTuning
from strategy_contracts.enums import (
    ImprovementKind,
    OrderKind,
    OrdersMode,
    PayLevel,
    RelationStatus,
    TaxRate,
    Terrain,
    TroopType,
)
from strategy_contracts.events import EventDefinition
from strategy_contracts.ids import (
    AmbitionId,
    ArmyId,
    CommanderId,
    EndingId,
    EventId,
    FactionId,
    FaithId,
    GovernorId,
    LeaderId,
    Percent,
    RegionId,
    SignedPercent,
    StanceId,
    TraitId,
    WholeNumber,
)
from strategy_contracts.limits import (
    MAX_DISABLED_BUILTIN_EVENTS,
    MAX_EVENT_DEFINITIONS,
    MAX_FACTIONS,
    MAX_LEADERS,
    MAX_NAME_CHARS,
    MAX_TEXT_CHARS,
)
from strategy_contracts.map import MapDocument
from strategy_contracts.negotiation_rules import NegotiationRules
from strategy_contracts.outrage import OutrageTuning
from strategy_contracts.overtures import OvertureTuning
from strategy_contracts.peace import PeaceTuning
from strategy_contracts.pressure import PressureTuning
from strategy_contracts.stances import MAX_CUSTOM_STANCES, StanceDefinition
from strategy_contracts.traits import TraitDefinition
from strategy_contracts.vassal import VassalageSetup, VassalTuning

SCENARIO_SCHEMA_VERSION = 1
HEX_COLOR_PATTERN = r"^#[0-9a-f]{6}$"
DEFAULT_ORDERS_PER_TURN = 6
DEFAULT_ORDER_COST = 1
DEFAULT_HEAVY_ORDER_COST = 2
DEFAULT_SUMMARY_THRESHOLD = 10
DEFAULT_EVENT_FREQUENCY_PERCENT = 50
DEFAULT_START_YEAR = 1000
DEFAULT_START_MONTH = 3
DEFAULT_END_YEAR = 1030
DEFAULT_LEADER_AGE = 35
MAX_COMMANDER_TRAITS = 2
DEFAULT_FREE_ORDER_COST = 0
HEAVY_ORDER_KINDS = frozenset(
    {
        OrderKind.RAISE_ARMY,
        OrderKind.BUILD_IMPROVEMENT,
        OrderKind.DECLARE_WAR,
        OrderKind.CALL_NEGOTIATION,
        OrderKind.FABRICATE_CLAIM,
        OrderKind.ANNEX_VASSAL,
    }
)
FREE_ORDER_KINDS = frozenset(
    {
        OrderKind.HALT_ARMY,
        OrderKind.ANSWER_CALL,
        OrderKind.ANSWER_DEMAND,
        OrderKind.GRANT_CONSENT,
        OrderKind.RELEASE_VASSAL,
    }
)
DEFAULT_MOVEMENT_BUDGET = 100
DEFAULT_TERRAIN_COSTS: dict[Terrain, int] = {
    Terrain.PLAIN: 100,
    Terrain.COAST: 100,
    Terrain.HILLS: 150,
    Terrain.DESERT: 150,
    Terrain.FOREST: 175,
    Terrain.MARSH: 200,
    Terrain.MOUNTAIN: 250,
}
DEFAULT_TROOP_TYPE_PENALTIES: dict[TroopType, int] = {
    TroopType.CAVALRY: -20,
    TroopType.INFANTRY: 0,
    TroopType.ARCHERS_SIEGE: 30,
}
DEFAULT_ROAD_DISCOUNT_PERCENT = 50
DEFAULT_WINTER_PENALTY_PERCENT = 50
DEFAULT_SPRING_PENALTY_PERCENT = 20
DEFAULT_WINTER_MONTHS = (12, 1, 2)
DEFAULT_SPRING_MONTHS = (3, 4)
DEFAULT_SIZE_STEP_TROOPS = 1000
DEFAULT_SIZE_STEP_PERCENT = 10
DEFAULT_SIZE_CAP_PERCENT = 50
DEFAULT_LOW_MORALE_THRESHOLD = 40
DEFAULT_LOW_MORALE_MAX_PENALTY_PERCENT = 30
DEFAULT_SAFEST_HAZARD_PENALTY = 200
DEFAULT_ROADS_OFF_ROAD_PENALTY = 50
MAX_ADJUSTMENT_PERCENT = 1000
DEFAULT_TAX_RATE_PERCENT: dict[TaxRate, int] = {
    TaxRate.LOW: 50,
    TaxRate.NORMAL: 80,
    TaxRate.HIGH: 120,
}
DEFAULT_TAX_UNREST_DRIFT: dict[TaxRate, int] = {
    TaxRate.LOW: -3,
    TaxRate.NORMAL: -1,
    TaxRate.HIGH: 3,
}
DEFAULT_UPKEEP_PER_UNIT: dict[TroopType, int] = {
    TroopType.INFANTRY: 10,
    TroopType.CAVALRY: 20,
    TroopType.ARCHERS_SIEGE: 25,
}
DEFAULT_RECRUIT_COST_PER_UNIT: dict[TroopType, int] = {
    TroopType.INFANTRY: 40,
    TroopType.CAVALRY: 90,
    TroopType.ARCHERS_SIEGE: 110,
}
DEFAULT_UPKEEP_TROOP_UNIT = 100
DEFAULT_PAY_LEVEL_PERCENT: dict[PayLevel, int] = {
    PayLevel.FULL: 100,
    PayLevel.REDUCED: 60,
}
DEFAULT_MORALE_RECOVERY: dict[PayLevel, int] = {
    PayLevel.FULL: 5,
    PayLevel.REDUCED: 2,
}
DEFAULT_MOBILIZATION_TAX_BONUS_PERCENT = 10
DEFAULT_MOBILIZATION_MANPOWER_BONUS_PERCENT = 25
DEFAULT_UNPAID_MORALE_LOSS = 8
DEFAULT_DESERTION_AFTER_UNPAID_TURNS = 2
DEFAULT_DESERTION_PERCENT = 10
DEFAULT_RAISED_ARMY_MORALE = 60
DEFAULT_DISBAND_RETURN_PERCENT = 50
DEFAULT_MANPOWER_REFILL_PER_THOUSAND = 20
DEFAULT_MANPOWER_CAP_PERCENT = 20
DEFAULT_BARRACKS_REFILL_BONUS_PERCENT = 50
DEFAULT_LOAN_BASE_INTEREST_PERCENT = 4
DEFAULT_LOAN_STRIKE_SURCHARGE_PERCENT = 2
DEFAULT_LOAN_TERM_TURNS = 12
DEFAULT_LOAN_INSTALLMENT_PERCENT = 20
DEFAULT_LOAN_CAP_INCOME_TURNS = 10
DEFAULT_LOAN_REFUSED_STRIKES = 3
DEFAULT_DEFAULT_REPUTATION_PENALTY = 5
DEFAULT_CREDIT_RECOVERY_TURNS = 6
DEFAULT_SHORTFALL_ORDER_COST = 1
DEFAULT_STRAINED_ATTRITION_PERCENT = 1
DEFAULT_ISOLATED_ATTRITION_PERCENT = 5
DEFAULT_WINTER_ATTRITION_PERCENT = 2
DEFAULT_STRAINED_MORALE_LOSS = 1
DEFAULT_ISOLATED_MORALE_LOSS = 5
DEFAULT_FORCED_WITHDRAWAL_AFTER_ISOLATED_TURNS = 2
DEFAULT_MAP_SCOUT_MIN_COVERAGE = 25
DEFAULT_MAP_SCOUT_MAX_COVERAGE = 100
DEFAULT_WAR_EXHAUSTION_PER_ACTIVE_WAR = 2
DEFAULT_WAR_EXHAUSTION_PER_LOSS_UNIT = 1
DEFAULT_BATTLE_LOSS_UNIT = 100
DEFAULT_PEACE_EXHAUSTION_RECOVERY = 1
DEFAULT_STABILITY_LOSS_PER_ACTIVE_WAR = 2
DEFAULT_STABILITY_LOSS_PER_LOSS_UNIT = 1
DEFAULT_PEACE_STABILITY_RECOVERY = 1
DEFAULT_UNREST_PER_ACTIVE_WAR = 1
DEFAULT_LOW_STABILITY_UNREST_DIVISOR = 20
DEFAULT_REVOLT_UNREST_THRESHOLD = 70
DEFAULT_REVOLT_BASE_CHANCE_PERCENT = 10
DEFAULT_REVOLT_CHANCE_PER_UNREST = 2
DEFAULT_UPRISING_COOLDOWN_TURNS = 3
DEFAULT_UPRISING_INCOME_PENALTY_PERCENT = 50
DEFAULT_UPRISING_MANPOWER_PENALTY_PERCENT = 50
DEFAULT_UPRISING_SUPPLY_PENALTY_PERCENT = 50
DEFAULT_CONCESSIONS_UNREST_REDUCTION = 30
DEFAULT_CONCESSIONS_STABILITY_GAIN = 2
DEFAULT_RESTORE_ORDER_UNREST_REDUCTION = 15
DEFAULT_RESTORE_ORDER_STABILITY_LOSS = 2
DEFAULT_NEGOTIATE_UNREST_REDUCTION = 20
DEFAULT_REBELLION_WAR_EXHAUSTION = 60
DEFAULT_UPRISING_ESCALATE_AFTER_TURNS = 3
DEFAULT_UPRISING_EASE_AFTER_TURNS = 2
DEFAULT_UPRISING_STAGE_PENALTY_STEP_PERCENT = 20
DEFAULT_UPRISING_ARMED_FLIP_TURNS = 4
DEFAULT_UPRISING_GARRISON_UNREST_RELIEF = 4
DEFAULT_CONCESSIONS_REPUTATION_COST = 5
DEFAULT_REBELLION_CONCESSIONS_COST_MULTIPLIER = 2
DEFAULT_PRECEDENT_UNREST_THRESHOLD = 40
DEFAULT_PRECEDENT_UNREST = 5
DEFAULT_RESTORE_ORDER_GRUDGE_TURNS = 5
DEFAULT_RESTORE_ORDER_GRUDGE_UNREST = 3
DEFAULT_UPRISING_RESPONSE_ORDER_COST = 1
DEFAULT_REBEL_ARMY_POPULATION_PERCENT = 5
DEFAULT_REBEL_ARMY_MIN_TROOPS = 20
DEFAULT_REBEL_ARMY_MORALE = 70
DEFAULT_CRUSHED_UNREST_REDUCTION = 40
DEFAULT_CRUSHED_STABILITY_GAIN = 3
MIN_MONTH = 1
MAX_MONTH = 12

Name = Field(min_length=1, max_length=MAX_NAME_CHARS)


def _default_order_cost(kind: OrderKind) -> int:
    if kind in FREE_ORDER_KINDS:
        return DEFAULT_FREE_ORDER_COST
    if kind in HEAVY_ORDER_KINDS:
        return DEFAULT_HEAVY_ORDER_COST
    return DEFAULT_ORDER_COST


def _default_order_costs() -> dict[OrderKind, int]:
    return {kind: _default_order_cost(kind) for kind in OrderKind}


def _default_terrain_costs() -> dict[Terrain, int]:
    return dict(DEFAULT_TERRAIN_COSTS)


def _default_troop_type_penalties() -> dict[TroopType, int]:
    return dict(DEFAULT_TROOP_TYPE_PENALTIES)


def _default_tax_rate_percent() -> dict[TaxRate, int]:
    return dict(DEFAULT_TAX_RATE_PERCENT)


def _default_tax_unrest_drift() -> dict[TaxRate, int]:
    return dict(DEFAULT_TAX_UNREST_DRIFT)


def _default_upkeep_per_unit() -> dict[TroopType, int]:
    return dict(DEFAULT_UPKEEP_PER_UNIT)


def _default_recruit_cost_per_unit() -> dict[TroopType, int]:
    return dict(DEFAULT_RECRUIT_COST_PER_UNIT)


def _default_pay_level_percent() -> dict[PayLevel, int]:
    return dict(DEFAULT_PAY_LEVEL_PERCENT)


def _default_morale_recovery() -> dict[PayLevel, int]:
    return dict(DEFAULT_MORALE_RECOVERY)


class ThemeVocabulary(StrictModel):
    infantry_name: str = "Infantry"
    cavalry_name: str = "Cavalry"
    archers_siege_name: str = "Archers & Siege"
    currency_name: str = "Gold"
    ruler_title: str = "Ruler"
    temple_name: str = "Temple"
    faith_name: str = "Faith"
    region_noun: str = "Region"


class SystemToggles(StrictModel):
    is_religion_enabled: bool = True
    is_succession_enabled: bool = True
    is_loans_enabled: bool = True
    is_fog_enabled: bool = True
    is_prisoners_enabled: bool = True
    is_events_enabled: bool = True
    is_outrage_enabled: bool = True
    is_overtures_enabled: bool = True
    is_orders_budget_enabled: bool = True


class FaithDefinition(StrictModel):
    id: FaithId
    name: str = Name


class FactionSetup(StrictModel):
    id: FactionId
    name: str = Name
    color: str = Field(pattern=HEX_COLOR_PATTERN)
    capital_region_id: RegionId | None = None
    leader_id: LeaderId | None = None
    treasury: WholeNumber = 0
    manpower: WholeNumber = 0
    stability: Percent = 50
    is_playable: bool = False
    stance_ids: list[StanceId] | None = None


class LeaderSetup(StrictModel):
    id: LeaderId
    name: str = Name
    faction_id: FactionId
    trait_ids: list[TraitId] = Field(default_factory=list)
    ambition_ids: list[AmbitionId] = Field(default_factory=list)
    history: str = Field(default="", max_length=MAX_TEXT_CHARS)
    age: int = Field(default=DEFAULT_LEADER_AGE, ge=0)
    portrait_url: str | None = None
    avatar_url: str | None = None


class PlayerRulerCustomization(StrictModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_CHARS)
    epithet: str | None = Field(default=None, max_length=MAX_NAME_CHARS)
    portrait_url: str | None = None
    avatar_url: str | None = None
    trait_ids: list[TraitId] = Field(min_length=2, max_length=3)
    ambition_ids: list[AmbitionId] = Field(min_length=1, max_length=2)
    backstory: str = Field(default="", max_length=MAX_TEXT_CHARS)


class GovernorSetup(StrictModel):
    id: GovernorId
    name: str = Name
    region_id: RegionId
    trait_ids: list[TraitId] = Field(default_factory=list)


class CommanderSetup(StrictModel):
    id: CommanderId
    name: str = Name
    faction_id: FactionId
    trait_ids: list[TraitId] = Field(
        default_factory=list, max_length=MAX_COMMANDER_TRAITS
    )
    is_important: bool = False


class RegionSetup(StrictModel):
    region_id: RegionId
    owner_id: FactionId | None = None
    population: WholeNumber = 0
    wealth: WholeNumber = 0
    manpower: WholeNumber = 0
    unrest: Percent = 0
    garrison: WholeNumber = 0
    faith_id: FaithId | None = None
    improvement_kinds: list[ImprovementKind] = Field(default_factory=list)
    governor_id: GovernorId | None = None


class ArmySetup(StrictModel):
    id: ArmyId
    owner_id: FactionId
    location_id: RegionId
    troops: dict[TroopType, WholeNumber] = Field(default_factory=dict)
    commander_id: CommanderId | None = None
    morale: Percent = 70


class RelationSetup(StrictModel):
    faction_a: FactionId
    faction_b: FactionId
    status: RelationStatus
    vassalage: VassalageSetup | None = None

    @model_validator(mode="after")
    def validate_vassalage(self) -> "RelationSetup":
        if self.vassalage is None:
            return self
        if self.vassalage.overlord_id not in {self.faction_a, self.faction_b}:
            raise ValueError("the overlord must be one of the pair")
        if self.status != RelationStatus.PEACE:
            raise ValueError("a vassalage needs a peace relation")
        return self


class ClaimSetup(StrictModel):
    faction_id: FactionId
    region_id: RegionId


class GrudgeSetup(StrictModel):
    holder_id: LeaderId
    target_id: LeaderId
    opinion: SignedPercent
    reason: str = Field(max_length=MAX_TEXT_CHARS)


class StartingSituation(StrictModel):
    regions: list[RegionSetup] = Field(default_factory=list)
    armies: list[ArmySetup] = Field(default_factory=list)
    relations: list[RelationSetup] = Field(default_factory=list)
    claims: list[ClaimSetup] = Field(default_factory=list)
    grudges: list[GrudgeSetup] = Field(default_factory=list)


class AmbitionDefinition(StrictModel):
    id: AmbitionId
    name: str = Name
    condition: Condition


class EndingKind(str, Enum):
    VICTORY = "victory"
    DEFEAT = "defeat"
    GRADED = "graded"


class EndingDefinition(StrictModel):
    id: EndingId
    kind: EndingKind
    name: str = Name
    condition: Condition
    epilogue_hint: str = Field(default="", max_length=MAX_TEXT_CHARS)


class MovementTuning(StrictModel):
    budget_per_turn: int = Field(default=DEFAULT_MOVEMENT_BUDGET, ge=1)
    terrain_costs: dict[Terrain, int] = Field(default_factory=_default_terrain_costs)
    troop_type_penalty_percent: dict[TroopType, int] = Field(
        default_factory=_default_troop_type_penalties
    )
    road_discount_percent: int = Field(
        default=DEFAULT_ROAD_DISCOUNT_PERCENT, ge=0, le=MAX_ADJUSTMENT_PERCENT
    )
    winter_penalty_percent: int = Field(
        default=DEFAULT_WINTER_PENALTY_PERCENT, ge=0, le=MAX_ADJUSTMENT_PERCENT
    )
    spring_penalty_percent: int = Field(
        default=DEFAULT_SPRING_PENALTY_PERCENT, ge=0, le=MAX_ADJUSTMENT_PERCENT
    )
    winter_months: tuple[int, ...] = DEFAULT_WINTER_MONTHS
    spring_months: tuple[int, ...] = DEFAULT_SPRING_MONTHS
    size_step_troops: int = Field(default=DEFAULT_SIZE_STEP_TROOPS, ge=1)
    size_step_percent: int = Field(
        default=DEFAULT_SIZE_STEP_PERCENT, ge=0, le=MAX_ADJUSTMENT_PERCENT
    )
    size_cap_percent: int = Field(
        default=DEFAULT_SIZE_CAP_PERCENT, ge=0, le=MAX_ADJUSTMENT_PERCENT
    )
    low_morale_threshold: int = Field(
        default=DEFAULT_LOW_MORALE_THRESHOLD, ge=1, le=100
    )
    low_morale_max_penalty_percent: int = Field(
        default=DEFAULT_LOW_MORALE_MAX_PENALTY_PERCENT,
        ge=0,
        le=MAX_ADJUSTMENT_PERCENT,
    )

    safest_hazard_penalty: int = Field(default=DEFAULT_SAFEST_HAZARD_PENALTY, ge=0)
    roads_off_road_penalty: int = Field(default=DEFAULT_ROADS_OFF_ROAD_PENALTY, ge=0)

    @field_validator("terrain_costs")
    @classmethod
    def validate_terrain_costs(cls, costs: dict[Terrain, int]) -> dict[Terrain, int]:
        if set(costs) != set(Terrain):
            raise ValueError("terrain_costs must define every terrain")
        if any(cost < 1 for cost in costs.values()):
            raise ValueError("terrain costs must be at least 1")
        return costs

    @field_validator("troop_type_penalty_percent")
    @classmethod
    def validate_troop_penalties(
        cls, penalties: dict[TroopType, int]
    ) -> dict[TroopType, int]:
        if set(penalties) != set(TroopType):
            raise ValueError("troop_type_penalty_percent must define every troop type")
        return penalties

    @field_validator("winter_months", "spring_months")
    @classmethod
    def validate_months(cls, months: tuple[int, ...]) -> tuple[int, ...]:
        if any(month < MIN_MONTH or month > MAX_MONTH for month in months):
            raise ValueError("months must be between 1 and 12")
        return months


class EconomyTuning(StrictModel):
    tax_rate_percent: dict[TaxRate, int] = Field(
        default_factory=_default_tax_rate_percent
    )
    tax_unrest_drift: dict[TaxRate, int] = Field(
        default_factory=_default_tax_unrest_drift
    )
    upkeep_per_unit: dict[TroopType, int] = Field(
        default_factory=_default_upkeep_per_unit
    )
    recruit_cost_per_unit: dict[TroopType, int] = Field(
        default_factory=_default_recruit_cost_per_unit
    )
    upkeep_troop_unit: int = Field(default=DEFAULT_UPKEEP_TROOP_UNIT, ge=1)
    pay_level_percent: dict[PayLevel, int] = Field(
        default_factory=_default_pay_level_percent
    )
    morale_recovery: dict[PayLevel, int] = Field(
        default_factory=_default_morale_recovery
    )
    unpaid_morale_loss: int = Field(default=DEFAULT_UNPAID_MORALE_LOSS, ge=0, le=100)
    mobilization_tax_bonus_percent: int = Field(
        default=DEFAULT_MOBILIZATION_TAX_BONUS_PERCENT, ge=0
    )
    mobilization_manpower_bonus_percent: int = Field(
        default=DEFAULT_MOBILIZATION_MANPOWER_BONUS_PERCENT, ge=0
    )
    desertion_after_unpaid_turns: int = Field(
        default=DEFAULT_DESERTION_AFTER_UNPAID_TURNS, ge=1
    )
    desertion_percent: Percent = DEFAULT_DESERTION_PERCENT
    raised_army_morale: Percent = DEFAULT_RAISED_ARMY_MORALE
    disband_return_percent: Percent = DEFAULT_DISBAND_RETURN_PERCENT
    manpower_refill_per_thousand: int = Field(
        default=DEFAULT_MANPOWER_REFILL_PER_THOUSAND, ge=0, le=1000
    )
    manpower_cap_percent: Percent = DEFAULT_MANPOWER_CAP_PERCENT
    barracks_refill_bonus_percent: int = Field(
        default=DEFAULT_BARRACKS_REFILL_BONUS_PERCENT, ge=0, le=MAX_ADJUSTMENT_PERCENT
    )
    loan_base_interest_percent: Percent = DEFAULT_LOAN_BASE_INTEREST_PERCENT
    loan_strike_surcharge_percent: Percent = DEFAULT_LOAN_STRIKE_SURCHARGE_PERCENT
    loan_term_turns: int = Field(default=DEFAULT_LOAN_TERM_TURNS, ge=1)
    loan_installment_percent: int = Field(
        default=DEFAULT_LOAN_INSTALLMENT_PERCENT, ge=1, le=100
    )
    loan_cap_income_turns: int = Field(default=DEFAULT_LOAN_CAP_INCOME_TURNS, ge=0)
    loan_refused_strikes: int = Field(default=DEFAULT_LOAN_REFUSED_STRIKES, ge=1)
    default_reputation_penalty: Percent = DEFAULT_DEFAULT_REPUTATION_PENALTY
    credit_recovery_turns: int = Field(default=DEFAULT_CREDIT_RECOVERY_TURNS, ge=1)
    shortfall_order_cost: int = Field(default=DEFAULT_SHORTFALL_ORDER_COST, ge=0)

    @field_validator("tax_rate_percent", "tax_unrest_drift")
    @classmethod
    def validate_every_tax_rate(cls, values: dict[TaxRate, int]) -> dict[TaxRate, int]:
        if set(values) != set(TaxRate):
            raise ValueError("tax tables must define every tax rate")
        return values

    @field_validator("upkeep_per_unit", "recruit_cost_per_unit")
    @classmethod
    def validate_every_troop_type(
        cls, values: dict[TroopType, int]
    ) -> dict[TroopType, int]:
        if set(values) != set(TroopType):
            raise ValueError("troop cost tables must define every troop type")
        if any(cost < 0 for cost in values.values()):
            raise ValueError("troop costs cannot be negative")
        return values

    @field_validator("pay_level_percent", "morale_recovery")
    @classmethod
    def validate_every_pay_level(
        cls, values: dict[PayLevel, int]
    ) -> dict[PayLevel, int]:
        if set(values) != set(PayLevel):
            raise ValueError("pay tables must define every pay level")
        if any(value < 0 for value in values.values()):
            raise ValueError("pay tables cannot be negative")
        return values


class VisibilityTuning(StrictModel):
    ruleset_version: Literal[1] = 1
    map_scout_min_coverage: Percent = DEFAULT_MAP_SCOUT_MIN_COVERAGE
    map_scout_max_coverage: Percent = DEFAULT_MAP_SCOUT_MAX_COVERAGE

    @model_validator(mode="after")
    def validate_map_scout_coverage(self) -> "VisibilityTuning":
        if self.map_scout_max_coverage < self.map_scout_min_coverage:
            raise ValueError("map scout coverage cannot be below the minimum")
        return self


class InternalTuning(StrictModel):
    rule_version: str = "internal-v1"
    war_exhaustion_per_active_war: Percent = DEFAULT_WAR_EXHAUSTION_PER_ACTIVE_WAR
    war_exhaustion_per_loss_unit: Percent = DEFAULT_WAR_EXHAUSTION_PER_LOSS_UNIT
    battle_loss_unit: int = Field(default=DEFAULT_BATTLE_LOSS_UNIT, ge=1)
    peace_exhaustion_recovery: Percent = DEFAULT_PEACE_EXHAUSTION_RECOVERY
    stability_loss_per_active_war: Percent = DEFAULT_STABILITY_LOSS_PER_ACTIVE_WAR
    stability_loss_per_loss_unit: Percent = DEFAULT_STABILITY_LOSS_PER_LOSS_UNIT
    peace_stability_recovery: Percent = DEFAULT_PEACE_STABILITY_RECOVERY
    unrest_per_active_war: Percent = DEFAULT_UNREST_PER_ACTIVE_WAR
    low_stability_unrest_divisor: int = Field(
        default=DEFAULT_LOW_STABILITY_UNREST_DIVISOR, ge=1
    )
    revolt_unrest_threshold: Percent = DEFAULT_REVOLT_UNREST_THRESHOLD
    revolt_base_chance_percent: Percent = DEFAULT_REVOLT_BASE_CHANCE_PERCENT
    revolt_chance_per_unrest: Percent = DEFAULT_REVOLT_CHANCE_PER_UNREST
    uprising_cooldown_turns: int = Field(default=DEFAULT_UPRISING_COOLDOWN_TURNS, ge=0)
    uprising_income_penalty_percent: Percent = DEFAULT_UPRISING_INCOME_PENALTY_PERCENT
    uprising_manpower_penalty_percent: Percent = (
        DEFAULT_UPRISING_MANPOWER_PENALTY_PERCENT
    )
    uprising_supply_penalty_percent: Percent = DEFAULT_UPRISING_SUPPLY_PENALTY_PERCENT
    concessions_unrest_reduction: Percent = DEFAULT_CONCESSIONS_UNREST_REDUCTION
    concessions_stability_gain: Percent = DEFAULT_CONCESSIONS_STABILITY_GAIN
    restore_order_unrest_reduction: Percent = DEFAULT_RESTORE_ORDER_UNREST_REDUCTION
    restore_order_stability_loss: Percent = DEFAULT_RESTORE_ORDER_STABILITY_LOSS
    negotiate_unrest_reduction: Percent = DEFAULT_NEGOTIATE_UNREST_REDUCTION
    rebellion_war_exhaustion: Percent = DEFAULT_REBELLION_WAR_EXHAUSTION
    uprising_escalate_after_turns: int = Field(
        default=DEFAULT_UPRISING_ESCALATE_AFTER_TURNS, ge=1
    )
    uprising_ease_after_turns: int = Field(
        default=DEFAULT_UPRISING_EASE_AFTER_TURNS, ge=1
    )
    uprising_stage_penalty_step_percent: Percent = (
        DEFAULT_UPRISING_STAGE_PENALTY_STEP_PERCENT
    )
    uprising_armed_flip_turns: int = Field(
        default=DEFAULT_UPRISING_ARMED_FLIP_TURNS, ge=1
    )
    uprising_garrison_unrest_relief: Percent = DEFAULT_UPRISING_GARRISON_UNREST_RELIEF
    concessions_reputation_cost: Percent = DEFAULT_CONCESSIONS_REPUTATION_COST
    rebellion_concessions_cost_multiplier: int = Field(
        default=DEFAULT_REBELLION_CONCESSIONS_COST_MULTIPLIER, ge=1
    )
    precedent_unrest_threshold: Percent = DEFAULT_PRECEDENT_UNREST_THRESHOLD
    precedent_unrest: Percent = DEFAULT_PRECEDENT_UNREST
    restore_order_grudge_turns: int = Field(
        default=DEFAULT_RESTORE_ORDER_GRUDGE_TURNS, ge=0
    )
    restore_order_grudge_unrest: Percent = DEFAULT_RESTORE_ORDER_GRUDGE_UNREST
    uprising_response_order_cost: int = Field(
        default=DEFAULT_UPRISING_RESPONSE_ORDER_COST, ge=1
    )
    rebel_army_population_percent: Percent = DEFAULT_REBEL_ARMY_POPULATION_PERCENT
    rebel_army_min_troops: int = Field(default=DEFAULT_REBEL_ARMY_MIN_TROOPS, ge=1)
    rebel_army_morale: Percent = DEFAULT_REBEL_ARMY_MORALE
    crushed_unrest_reduction: Percent = DEFAULT_CRUSHED_UNREST_REDUCTION
    crushed_stability_gain: Percent = DEFAULT_CRUSHED_STABILITY_GAIN


class LogisticsTuning(StrictModel):
    """Campaign-end supply losses. Battle modifiers keep using BattleTuning."""

    rule_version: str = "logistics-v1"
    strained_attrition_percent: Percent = DEFAULT_STRAINED_ATTRITION_PERCENT
    isolated_attrition_percent: Percent = DEFAULT_ISOLATED_ATTRITION_PERCENT
    winter_attrition_percent: Percent = DEFAULT_WINTER_ATTRITION_PERCENT
    strained_morale_loss: Percent = DEFAULT_STRAINED_MORALE_LOSS
    isolated_morale_loss: Percent = DEFAULT_ISOLATED_MORALE_LOSS
    forced_withdrawal_after_isolated_turns: int = Field(
        default=DEFAULT_FORCED_WITHDRAWAL_AFTER_ISOLATED_TURNS, ge=1
    )


class Tuning(StrictModel):
    orders_mode: OrdersMode = OrdersMode.BUDGET
    orders_per_turn: int = Field(default=DEFAULT_ORDERS_PER_TURN, ge=0)
    order_costs: dict[OrderKind, int] = Field(default_factory=_default_order_costs)
    summary_significance_threshold: int = Field(default=DEFAULT_SUMMARY_THRESHOLD, ge=1)
    event_frequency_percent: Percent = DEFAULT_EVENT_FREQUENCY_PERCENT
    start_year: int = DEFAULT_START_YEAR
    start_month: int = Field(default=DEFAULT_START_MONTH, ge=1, le=12)
    end_year: int = DEFAULT_END_YEAR
    movement: MovementTuning = Field(default_factory=MovementTuning)
    economy: EconomyTuning = Field(default_factory=EconomyTuning)
    battle: BattleTuning = Field(default_factory=BattleTuning)
    visibility: VisibilityTuning = Field(default_factory=VisibilityTuning)
    internal: InternalTuning = Field(default_factory=InternalTuning)
    logistics: LogisticsTuning = Field(default_factory=LogisticsTuning)
    diplomacy: DiplomacyTuning = Field(default_factory=DiplomacyTuning)
    pressure: PressureTuning = Field(default_factory=PressureTuning)
    peace: PeaceTuning = Field(default_factory=PeaceTuning)
    alliance: AllianceTuning = Field(default_factory=AllianceTuning)
    vassal: VassalTuning = Field(default_factory=VassalTuning)
    coalition: CoalitionTuning = Field(default_factory=CoalitionTuning)
    outrage: OutrageTuning = Field(default_factory=OutrageTuning)
    overtures: OvertureTuning = Field(default_factory=OvertureTuning)
    ai: AiTuning = Field(default_factory=AiTuning)
    endings: EndingsTuning = Field(default_factory=EndingsTuning)

    @field_validator("order_costs")
    @classmethod
    def fill_missing_order_costs(
        cls, costs: dict[OrderKind, int]
    ) -> dict[OrderKind, int]:
        return _default_order_costs() | costs


class StrategyScenario(StrictModel):
    schema_version: int = SCENARIO_SCHEMA_VERSION
    theme: ThemeVocabulary = Field(default_factory=ThemeVocabulary)
    toggles: SystemToggles = Field(default_factory=SystemToggles)
    map: MapDocument = Field(default_factory=MapDocument)
    factions: list[FactionSetup] = Field(default_factory=list, max_length=MAX_FACTIONS)
    leaders: list[LeaderSetup] = Field(default_factory=list, max_length=MAX_LEADERS)
    governors: list[GovernorSetup] = Field(default_factory=list)
    commanders: list[CommanderSetup] = Field(default_factory=list)
    faiths: list[FaithDefinition] = Field(default_factory=list)
    starting: StartingSituation = Field(default_factory=StartingSituation)
    custom_traits: list[TraitDefinition] = Field(default_factory=list)
    ambitions: list[AmbitionDefinition] = Field(default_factory=list)
    custom_stances: list[StanceDefinition] = Field(
        default_factory=list, max_length=MAX_CUSTOM_STANCES
    )
    is_using_default_endings: bool = True
    endings: list[EndingDefinition] = Field(default_factory=list)
    disabled_builtin_event_ids: list[EventId] = Field(
        default_factory=list, max_length=MAX_DISABLED_BUILTIN_EVENTS
    )
    events: list[EventDefinition] = Field(
        default_factory=list, max_length=MAX_EVENT_DEFINITIONS
    )
    negotiation: NegotiationRules = Field(default_factory=NegotiationRules)
    tuning: Tuning = Field(default_factory=Tuning)
