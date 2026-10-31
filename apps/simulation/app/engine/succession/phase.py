from app.engine.rng import DeterministicRng
from app.engine.succession.ageing import age_leaders
from app.engine.succession.crisis import tick_crises
from app.engine.succession.install import kill_ruler
from app.engine.succession.roll import roll_ruler_deaths
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def tick_succession(
    world: WorldState, scenario: StrategyScenario, rng: DeterministicRng
) -> list[EventLogEntry]:
    if not world.succession_ruleset:
        return []
    age_leaders(world)
    events: list[EventLogEntry] = []
    for faction_id, cause in roll_ruler_deaths(world, scenario, rng):
        events += kill_ruler(world, scenario, faction_id, cause)
    events += tick_crises(world, scenario)
    return events
