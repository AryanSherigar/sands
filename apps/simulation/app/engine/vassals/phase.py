from app.engine.vassals.collapse import free_vassals_of_collapsed_overlords
from app.engine.vassals.consent import expire_consents
from app.engine.vassals.demands import resolve_demands
from app.engine.vassals.garrison import apply_garrison_unrest
from app.engine.vassals.overlord_rule import npc_overlord_demands
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def tick_vassals(world: WorldState, scenario: StrategyScenario) -> list[EventLogEntry]:
    if world.vassal_ruleset < 1:
        return []
    events = free_vassals_of_collapsed_overlords(world, scenario)
    expire_consents(world)
    return events + apply_garrison_unrest(world, scenario)


def run_vassal_diplomacy(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    if world.vassal_ruleset < 1:
        return []
    events = resolve_demands(world, scenario)
    return events + npc_overlord_demands(world, scenario)
