from app.engine.movement.advance import advance_all
from app.engine.movement.map_index import build_map_index
from app.engine.movement.order_intake import apply_orders
from app.engine.movement.road_meetings import resolve_road_meetings
from app.engine.movement.state import MovementRun
from app.engine.phases import PhaseContext, PhaseResult
from app.models.world_events import PhaseName
from app.models.world_state import WorldState


class MovementPhase:
    name = PhaseName.MOVEMENT

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        run = MovementRun(
            world=world,
            index=build_map_index(context.scenario.map),
            tuning=context.scenario.tuning.movement,
        )
        apply_orders(run, context.orders)
        advance_all(run)
        resolve_road_meetings(run)
        return PhaseResult(world=run.world, events=run.events)
