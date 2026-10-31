from dataclasses import dataclass

from app.engine.diplomacy.validation import is_at_war
from app.engine.sieges.events import region_occupied, siege_progressed
from app.engine.sieges.presence import armies_at
from app.engine.sieges.progress import progress_per_turn
from app.models.world_events import EventLogEntry
from app.models.world_region import OccupationState
from app.models.world_siege import SiegeState
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def advance_sieges(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    remaining: list[SiegeState] = []
    for siege in sorted(world.sieges, key=lambda item: item.region_id):
        step = _advance_siege(world, scenario, siege)
        events.extend(step.events)
        if step.is_ongoing:
            remaining.append(siege)
    world.sieges = remaining
    return events


@dataclass
class _SiegeStep:
    events: list[EventLogEntry]
    is_ongoing: bool


def is_siege_valid(world: WorldState, siege: SiegeState) -> bool:
    region = world.regions[siege.region_id]
    owner = region.owner_id
    if owner is None or owner == siege.besieger_id or region.occupation is not None:
        return False
    return is_at_war(world, siege.besieger_id, owner)


def _advance_siege(
    world: WorldState, scenario: StrategyScenario, siege: SiegeState
) -> _SiegeStep:
    siege.army_ids = armies_at(world, siege.besieger_id, siege.region_id)
    if not siege.army_ids or not is_siege_valid(world, siege):
        return _SiegeStep([], False)
    tuning = scenario.tuning.siege
    region = world.regions[siege.region_id]
    troops = sum(
        sum(world.armies[army_id].troops.values()) for army_id in siege.army_ids
    )
    before = siege.progress
    siege.progress = before + progress_per_turn(troops, region.garrison, tuning)
    if siege.progress < tuning.full_progress:
        return _SiegeStep(
            [
                siege_progressed(
                    siege.besieger_id, siege.region_id, before, siege.progress
                )
            ],
            True,
        )
    region.occupation = OccupationState(
        occupier_id=siege.besieger_id, siege_progress=tuning.full_progress
    )
    return _SiegeStep([region_occupied(siege.besieger_id, siege.region_id)], False)
