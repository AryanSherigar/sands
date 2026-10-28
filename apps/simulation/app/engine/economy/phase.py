from app.engine.economy.orders import apply_economy_orders
from app.engine.economy.settlement import settle_faction
from app.engine.economy.state import active_faction_ids, start_run
from app.engine.phases import PhaseContext, PhaseResult
from app.engine.vassals.tribute import collect_vassal_tribute
from app.models.world_events import PhaseName
from app.models.world_state import WorldState


class EconomyPhase:
    name = PhaseName.ECONOMY

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        run = start_run(world, context.scenario)
        apply_economy_orders(run, context.orders)
        for faction_id in active_faction_ids(run.world):
            pause = settle_faction(run, faction_id, context)
            if pause is not None:
                return PhaseResult(world=run.world, pause=pause)
        collect_vassal_tribute(run)
        return PhaseResult(world=run.world, events=run.events)
