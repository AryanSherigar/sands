from collections.abc import Sequence

from app.engine.sieges.events import occupation_lifted
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_siege import SiegeState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId

FactionPair = tuple[FactionId, FactionId]


def _pair_key(first: FactionId, second: FactionId) -> FactionPair:
    return (first, second) if first <= second else (second, first)


def lift_pair_sieges(
    world: WorldState, pairs: Sequence[FactionPair], phase: PhaseName
) -> list[EventLogEntry]:
    """Phase is passed in because the pipeline requires an event's phase to match the running phase."""
    if world.siege_ruleset < 1:
        return []
    keys = {_pair_key(*pair) for pair in pairs}
    world.sieges = [
        siege for siege in world.sieges if not _is_pair_siege(world, siege, keys)
    ]
    return _lift_occupations(world, keys, phase)


def _is_pair_siege(
    world: WorldState, siege: SiegeState, keys: set[FactionPair]
) -> bool:
    owner_id = world.regions[siege.region_id].owner_id
    return owner_id is not None and _pair_key(siege.besieger_id, owner_id) in keys


def _lift_occupations(
    world: WorldState, keys: set[FactionPair], phase: PhaseName
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for region_id in sorted(world.regions):
        region = world.regions[region_id]
        if region.occupation is None or region.owner_id is None:
            continue
        occupier_id = region.occupation.occupier_id
        is_stale = occupier_id == region.owner_id
        if is_stale or _pair_key(occupier_id, region.owner_id) in keys:
            region.occupation = None
            events.append(
                occupation_lifted(occupier_id, region.owner_id, region_id, phase)
            )
    return events
