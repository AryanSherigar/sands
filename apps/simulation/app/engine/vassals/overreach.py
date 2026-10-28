from dataclasses import dataclass

from app.engine.vassals.registry import granted_share, vassal_term
from app.models.world_diplomacy import CommitmentState
from app.models.world_state import WorldState
from app.models.world_vassal import DemandState
from strategy_contracts.ids import RegionId
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.vassal import DemandKind, VassalTuning

MAX_EXCESS_PERCENT = 300
HALF_DIVISOR = 2


@dataclass(frozen=True)
class DemandFigures:
    granted: int
    excess: int
    excess_percent: int


def _percent_over(granted: int, excess: int) -> int:
    return min(MAX_EXCESS_PERCENT, excess * FULL_SHARE_PERCENT // max(granted, 1))


def demand_figures(
    commitment: CommitmentState,
    kind: DemandKind,
    amount: int,
    tuning: VassalTuning,
) -> DemandFigures:
    granted = granted_share(commitment, kind)
    if kind is DemandKind.GARRISON:
        if vassal_term(commitment).has_garrison_rights:
            return DemandFigures(granted, 0, 0)
        return DemandFigures(granted, amount, tuning.garrison_excess_percent)
    excess = amount - granted
    return DemandFigures(granted, excess, _percent_over(granted, excess))


def excess_percent_of(demand: DemandState, tuning: VassalTuning) -> int:
    if demand.kind is DemandKind.GARRISON:
        return tuning.garrison_excess_percent
    return _percent_over(demand.granted, demand.amount - demand.granted)


def _vassal_regions(world: WorldState, demand: DemandState) -> list[RegionId]:
    return [
        region_id
        for region_id, region in sorted(world.regions.items())
        if region.owner_id == demand.vassal_id
    ]


def _stationed_region_ids(world: WorldState, demand: DemandState) -> set[RegionId]:
    return {
        army.location_id
        for army in world.armies.values()
        if army.owner_id == demand.overlord_id
    }


def affected_region_ids(world: WorldState, demand: DemandState) -> list[RegionId]:
    owned = _vassal_regions(world, demand)
    if demand.kind is DemandKind.LEVY:
        return [item for item in owned if world.regions[item].manpower > 0]
    if demand.kind is DemandKind.GARRISON:
        stationed = _stationed_region_ids(world, demand)
        return [item for item in owned if item in stationed] or owned
    return owned


def raise_unrest(
    world: WorldState, scenario: StrategyScenario, demand: DemandState
) -> list[RegionId]:
    tuning = scenario.tuning.vassal
    step = min(
        excess_percent_of(demand, tuning) // tuning.unrest_per_excess_divisor,
        tuning.unrest_cap_per_demand,
    )
    affected = affected_region_ids(world, demand)
    for region_id in affected:
        region = world.regions[region_id]
        region.unrest = min(FULL_SHARE_PERCENT, region.unrest + step)
    return affected
