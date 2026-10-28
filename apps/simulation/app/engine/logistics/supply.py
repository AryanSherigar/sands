from dataclasses import dataclass

from app.engine.movement.map_index import MapIndex, build_map_index
from app.models.world_internal import is_rebel_faction, uprising_for_region
from app.models.world_state import WorldState
from strategy_contracts.battle import SupplyState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.scenario import StrategyScenario


@dataclass(frozen=True)
class SupplyAssessment:
    state: SupplyState
    capacity: int
    demand: int


def supply_assessments(
    world: WorldState, scenario: StrategyScenario
) -> dict[tuple[str, str], SupplyAssessment]:
    """Classify every faction-region pair once for the campaign boundary."""
    index = build_map_index(scenario.map)
    demand = _regional_demand(world)
    factions = sorted({army.owner_id for army in world.armies.values()})
    reachable = {
        faction_id: _reachable_regions(world, scenario, index, faction_id)
        for faction_id in factions
    }
    return {
        (faction_id, region_id): _faction_assessment(
            world, scenario, index, demand, faction_id, region_id, reachable
        )
        for faction_id in factions
        for region_id in sorted(world.regions)
    }


def _faction_assessment(
    world: WorldState,
    scenario: StrategyScenario,
    index: MapIndex,
    demand: dict[str, int],
    faction_id: str,
    region_id: str,
    reachable: dict[str, set[str]],
) -> SupplyAssessment:
    if is_rebel_faction(faction_id):
        # NOTE: rebels live off the land they hold, so they are never starved out.
        troops = demand.get(region_id, 0)
        return SupplyAssessment(SupplyState.SUPPLIED, troops, troops)
    return _assessment(world, scenario, index, demand, region_id, reachable[faction_id])


def supply_assessment(
    world: WorldState, region_id: str, faction_id: str, scenario: StrategyScenario
) -> SupplyAssessment:
    return supply_assessments(world, scenario).get(
        (faction_id, region_id), SupplyAssessment(SupplyState.ISOLATED, 0, 0)
    )


def _regional_demand(world: WorldState) -> dict[str, int]:
    demand: dict[str, int] = {}
    for army in world.armies.values():
        demand[army.location_id] = demand.get(army.location_id, 0) + sum(
            army.troops.values()
        )
    return demand


def _assessment(
    world: WorldState,
    scenario: StrategyScenario,
    index: MapIndex,
    demand: dict[str, int],
    region_id: str,
    reachable: set[str],
) -> SupplyAssessment:
    if region_id not in reachable:
        return SupplyAssessment(SupplyState.ISOLATED, 0, demand.get(region_id, 0))
    capacity = _capacity(world, scenario, index, region_id)
    regional_demand = demand.get(region_id, 0)
    state = (
        SupplyState.SUPPLIED if regional_demand <= capacity else SupplyState.STRAINED
    )
    return SupplyAssessment(state, capacity, regional_demand)


def _capacity(
    world: WorldState, scenario: StrategyScenario, index: MapIndex, region_id: str
) -> int:
    region = world.regions[region_id]
    capacity = region.wealth * scenario.tuning.battle.supply_wealth_capacity
    uprising = uprising_for_region(world.uprisings, region_id)
    if uprising is not None:
        capacity = capacity * (100 - uprising.supply_penalty_percent) // 100
    if any(region_id in road for road in index.roads):
        capacity += scenario.tuning.battle.supply_road_bonus
    return capacity


def _reachable_regions(
    world: WorldState,
    scenario: StrategyScenario,
    index: MapIndex,
    faction_id: str,
) -> set[str]:
    capital_id = _capital_source(world, faction_id, scenario)
    if capital_id is None:
        return set()
    accessible = {
        identity
        for identity, region in world.regions.items()
        if region.owner_id in _supply_owners(world, faction_id)
        and region.occupation is None
    }
    pending = [capital_id]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current not in accessible or current in visited:
            continue
        visited.add(current)
        pending.extend(
            sorted(index.neighbors.get(current, frozenset()) - visited, reverse=True)
        )
    return visited


def _supply_owners(world: WorldState, faction_id: str) -> set[str]:
    owners = {faction_id}
    for relation in world.relations:
        if relation.status == RelationStatus.ALLIANCE and faction_id in (
            relation.faction_a,
            relation.faction_b,
        ):
            owners.update((relation.faction_a, relation.faction_b))
    return owners


def _capital_source(
    world: WorldState, faction_id: str, scenario: StrategyScenario
) -> str | None:
    capital_id = next(
        (
            faction.capital_region_id
            for faction in scenario.factions
            if faction.id == faction_id
        ),
        None,
    )
    capital = world.regions.get(capital_id)
    if capital is None or capital.owner_id != faction_id or capital.occupation:
        return None
    return capital_id
