import itertools
from collections.abc import Callable
from dataclasses import dataclass

from app.engine.movement.map_index import MapIndex
from app.models.world_army import ArmyState
from app.models.world_clock import MONTHS_PER_TURN, MONTHS_PER_YEAR, TurnClock
from strategy_contracts.ids import RegionId
from strategy_contracts.scenario import MovementTuning

PERCENT = 100
MIN_LEG_COST = 1
MIN_COST_PERCENT = 10
ROAD_REASON = "road"
WINTER_REASON = "winter"
SPRING_REASON = "spring"
SIZE_REASON = "size"
TROOP_MIX_REASON = "troop_mix"
MORALE_REASON = "morale"


@dataclass(frozen=True)
class Adjustment:
    reason: str
    percent: int


@dataclass(frozen=True)
class LegCost:
    base: int
    adjustments: tuple[Adjustment, ...]
    total: int


@dataclass(frozen=True)
class LegContext:
    index: MapIndex
    army: ArmyState
    clock: TurnClock
    tuning: MovementTuning
    from_id: RegionId
    to_id: RegionId


def months_of_turn(clock: TurnClock) -> tuple[int, int]:
    first = (clock.start_month - 1 + MONTHS_PER_TURN * clock.turn) % MONTHS_PER_YEAR
    return first + 1, (first + 1) % MONTHS_PER_YEAR + 1


def _non_zero(reason: str, percent: int) -> list[Adjustment]:
    return [Adjustment(reason, percent)] if percent else []


def road_rule(leg: LegContext) -> list[Adjustment]:
    if not leg.index.has_road(leg.from_id, leg.to_id):
        return []
    return [Adjustment(ROAD_REASON, -leg.tuning.road_discount_percent)]


def _share_of_turn(months: tuple[int, int], season_months: tuple[int, ...]) -> int:
    return sum(1 for month in months if month in season_months)


def season_rule(leg: LegContext) -> list[Adjustment]:
    months = months_of_turn(leg.clock)
    tuning = leg.tuning
    winter = tuning.winter_penalty_percent * _share_of_turn(
        months, tuning.winter_months
    )
    spring = tuning.spring_penalty_percent * _share_of_turn(
        months, tuning.spring_months
    )
    return _non_zero(WINTER_REASON, winter // MONTHS_PER_TURN) + _non_zero(
        SPRING_REASON, spring // MONTHS_PER_TURN
    )


def size_rule(leg: LegContext) -> list[Adjustment]:
    tuning = leg.tuning
    steps = sum(leg.army.troops.values()) // tuning.size_step_troops
    percent = min(tuning.size_cap_percent, steps * tuning.size_step_percent)
    return _non_zero(SIZE_REASON, percent)


def troop_mix_rule(leg: LegContext) -> list[Adjustment]:
    penalties = [
        leg.tuning.troop_type_penalty_percent[troop_type]
        for troop_type, count in leg.army.troops.items()
        if count > 0
    ]
    return _non_zero(TROOP_MIX_REASON, max(penalties, default=0))


def morale_rule(leg: LegContext) -> list[Adjustment]:
    tuning = leg.tuning
    shortfall = max(0, tuning.low_morale_threshold - leg.army.morale)
    percent = (
        tuning.low_morale_max_penalty_percent * shortfall // tuning.low_morale_threshold
    )
    return _non_zero(MORALE_REASON, percent)


LEG_RULES: tuple[Callable[[LegContext], list[Adjustment]], ...] = (
    road_rule,
    season_rule,
    size_rule,
    troop_mix_rule,
    morale_rule,
)


def _apply_percent(base: int, percent: int) -> int:
    factor = max(MIN_COST_PERCENT, PERCENT + percent)
    return max(MIN_LEG_COST, base * factor // PERCENT)


def leg_cost(
    index: MapIndex,
    army: ArmyState,
    clock: TurnClock,
    tuning: MovementTuning,
    from_id: RegionId,
    to_id: RegionId,
) -> LegCost:
    leg = LegContext(index, army, clock, tuning, from_id, to_id)
    adjustments = tuple(adjustment for rule in LEG_RULES for adjustment in rule(leg))
    base = tuning.terrain_costs[index.terrain[to_id]]
    total = _apply_percent(base, sum(adjustment.percent for adjustment in adjustments))
    return LegCost(base=base, adjustments=adjustments, total=total)


def route_base_cost(
    index: MapIndex, tuning: MovementTuning, from_id: RegionId, to_id: RegionId
) -> int:
    base = tuning.terrain_costs[index.terrain[to_id]]
    if not index.has_road(from_id, to_id):
        return base
    return _apply_percent(base, -tuning.road_discount_percent)


def route_total_cost(
    index: MapIndex, tuning: MovementTuning, start: RegionId, route: list[RegionId]
) -> int:
    stops = [start, *route]
    return sum(
        route_base_cost(index, tuning, left, right)
        for left, right in itertools.pairwise(stops)
    )
