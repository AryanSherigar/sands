from app.engine.phases import PhaseContext, PhaseResult
from app.engine.sieges.advance import advance_sieges
from app.engine.sieges.occupation import hold_occupations
from app.engine.sieges.starts import start_sieges
from app.models.world_events import PhaseName
from app.models.world_state import WorldState


class SiegePhase:
    name = PhaseName.SIEGES

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        if world.siege_ruleset < 1:
            return PhaseResult(world)
        scenario = context.scenario
        events = hold_occupations(world, scenario)
        events += start_sieges(world, scenario)
        events += advance_sieges(world, scenario)
        return PhaseResult(world, events)
