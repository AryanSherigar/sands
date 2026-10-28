from app.engine.economy.income import owned_regions
from app.engine.economy.manpower import manpower_cap
from app.engine.outrage.effects import mobilization_strain
from app.engine.pressure.wars import wars_of
from app.models.world_diplomacy import WarState
from app.models.world_pressure import StrainReading
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

FULL_PERCENT = 100
MAX_STRAIN = 100
DEBT_WEIGHT = 25
EMPTY_TREASURY_STRAIN = 10
MANPOWER_WEIGHT = 20
DEVASTATION_WEIGHT = 20
UNREST_WEIGHT = 15
SUPPLY_STRAIN_PER_ARMY = 5
SUPPLY_STRAIN_CAP = 15


def _treasury_debt(world: WorldState, faction_id: FactionId) -> int:
    faction = world.factions[faction_id]
    debt = sum(loan.principal for loan in faction.loans)
    share = FULL_PERCENT * debt // (debt + max(0, faction.treasury) + 1)
    empty = EMPTY_TREASURY_STRAIN if faction.treasury <= 0 else 0
    return DEBT_WEIGHT * share // FULL_PERCENT + empty


def _manpower(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    regions = owned_regions(world, faction_id)
    capacity = sum(manpower_cap(region, scenario.tuning.economy) for region in regions)
    if not capacity:
        return 0
    current = min(sum(region.manpower for region in regions), capacity)
    depletion = FULL_PERCENT - FULL_PERCENT * current // capacity
    return MANPOWER_WEIGHT * depletion // FULL_PERCENT


def _average(values: list[int]) -> int:
    return sum(values) // len(values) if values else 0


def _devastation(world: WorldState, faction_id: FactionId) -> int:
    regions = owned_regions(world, faction_id)
    average = _average([world.pressure.devastation.get(r.id, 0) for r in regions])
    return DEVASTATION_WEIGHT * average // FULL_PERCENT


def _unrest(world: WorldState, faction_id: FactionId) -> int:
    average = _average([r.unrest for r in owned_regions(world, faction_id)])
    return UNREST_WEIGHT * average // FULL_PERCENT


def _supply(world: WorldState, faction_id: FactionId) -> int:
    starving = sum(
        1
        for army_id, turns in world.supply_failure_turns.items()
        if turns > 0 and world.armies[army_id].owner_id == faction_id
    )
    return min(SUPPLY_STRAIN_CAP, starving * SUPPLY_STRAIN_PER_ARMY)


def _stalemate(
    world: WorldState, scenario: StrategyScenario, wars: list[WarState]
) -> int:
    idle = max(
        (world.pressure.stalemate_turns.get(war.id, 0) for war in wars), default=0
    )
    return idle // scenario.tuning.pressure.stalemate_turns_per_strain


def compute_strain(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> StrainReading:
    wars = wars_of(world, faction_id)
    if not wars or world.factions[faction_id].is_destroyed:
        return StrainReading(value=0)
    factors = {
        "treasury_debt": _treasury_debt(world, faction_id),
        "manpower": _manpower(world, scenario, faction_id),
        "devastation": _devastation(world, faction_id),
        "supply": _supply(world, faction_id),
        "unrest": _unrest(world, faction_id),
        "stalemate": _stalemate(world, scenario, wars),
        "second_front": (len(wars) - 1) * scenario.tuning.pressure.second_front_strain,
    }
    mobilization = mobilization_strain(world, scenario, faction_id)
    if mobilization:
        factors["mobilization"] = mobilization
    return StrainReading(value=min(MAX_STRAIN, sum(factors.values())), factors=factors)
