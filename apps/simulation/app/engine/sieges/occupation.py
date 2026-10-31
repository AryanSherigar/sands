from app.engine.diplomacy.transfers import cede_region, hand_over_region
from app.engine.diplomacy.validation import is_at_war
from app.engine.sieges.events import occupation_lifted, region_conquered
from app.engine.sieges.presence import armies_at
from app.models.world_events import EventLogEntry
from app.models.world_region import RegionState
from app.models.world_state import WorldState
from strategy_contracts.ids import RegionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import CedeRegionTerm

MAX_UNREST = 100


def lift_occupation(world: WorldState, region_id: RegionId) -> EventLogEntry | None:
    region = world.regions[region_id]
    if region.occupation is None:
        return None
    occupier_id = region.occupation.occupier_id
    region.occupation = None
    return occupation_lifted(occupier_id, region.owner_id, region_id)


def hold_occupations(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for region_id in sorted(world.regions):
        region = world.regions[region_id]
        if region.occupation is not None:
            events.extend(_hold_region(world, scenario, region))
    return events


def _is_occupation_held(world: WorldState, region: RegionState) -> bool:
    occupation = region.occupation
    if occupation is None or region.owner_id is None:
        return False
    if not armies_at(world, occupation.occupier_id, region.id):
        return False
    return is_at_war(world, occupation.occupier_id, region.owner_id)


def _hold_region(
    world: WorldState, scenario: StrategyScenario, region: RegionState
) -> list[EventLogEntry]:
    if not _is_occupation_held(world, region):
        lifted = lift_occupation(world, region.id)
        return [] if lifted is None else [lifted]
    region.occupation.hold_turns += 1
    if region.occupation.hold_turns < scenario.tuning.siege.hold_delay:
        return []
    return [_transfer_region(world, scenario, region)]


def _transfer_region(
    world: WorldState, scenario: StrategyScenario, region: RegionState
) -> EventLogEntry:
    occupier_id = region.occupation.occupier_id
    previous_owner_id = region.owner_id
    region.occupation = None
    term = CedeRegionTerm(
        from_faction_id=previous_owner_id,
        to_faction_id=occupier_id,
        region_id=region.id,
    )
    cede_region(world, scenario, term)
    hand_over_region(world, region.id, previous_owner_id, occupier_id)
    region.unrest = min(
        MAX_UNREST, region.unrest + scenario.tuning.siege.conquest_unrest
    )
    return region_conquered(occupier_id, previous_owner_id, region.id)
