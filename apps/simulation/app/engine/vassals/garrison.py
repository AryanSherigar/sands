from app.engine.diplomacy.events import diplomacy_event
from app.engine.vassals.registry import is_vassalage_in_force, vassal_term
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario

GARRISON_UNREST = "garrison_unrest"


def has_garrison_access(
    world: WorldState, overlord_id: FactionId, vassal_id: FactionId
) -> bool:
    for commitment in world.commitments:
        if not is_vassalage_in_force(world, commitment):
            continue
        term = vassal_term(commitment)
        if (term.overlord_id, term.vassal_id) != (overlord_id, vassal_id):
            continue
        until = world.vassal.garrison_until.get(commitment.id, 0)
        return term.has_garrison_rights or until > world.clock.turn
    return False


def _garrisoned_region_ids(
    world: WorldState, overlord_id: FactionId, vassal_id: FactionId
) -> list[RegionId]:
    stationed = {
        army.location_id
        for army in world.armies.values()
        if army.owner_id == overlord_id
    }
    return sorted(
        region_id
        for region_id in stationed
        if region_id in world.regions and world.regions[region_id].owner_id == vassal_id
    )


def apply_garrison_unrest(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    step = scenario.tuning.vassal.garrison_unrest_per_turn
    events: list[EventLogEntry] = []
    for commitment in sorted(world.commitments, key=lambda item: item.id):
        if not is_vassalage_in_force(world, commitment):
            continue
        term = vassal_term(commitment)
        if not has_garrison_access(world, term.overlord_id, term.vassal_id):
            continue
        for region_id in _garrisoned_region_ids(
            world, term.overlord_id, term.vassal_id
        ):
            region = world.regions[region_id]
            region.unrest = min(FULL_SHARE_PERCENT, region.unrest + step)
            events.append(
                diplomacy_event(
                    GARRISON_UNREST,
                    [term.overlord_id, term.vassal_id, region_id],
                    {"unrest": region.unrest},
                    phase=PhaseName.TIME,
                )
            )
    return events
