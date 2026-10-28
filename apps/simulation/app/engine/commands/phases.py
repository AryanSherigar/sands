from app.engine.commands.ledger import due_commands, queued_order
from app.engine.commands.validation import validate_empire_command
from app.engine.economy.orders import apply_economy_orders
from app.engine.economy.settlement import settle_faction
from app.engine.economy.state import active_faction_ids, start_run
from app.engine.movement.advance import advance_all
from app.engine.movement.map_index import build_map_index
from app.engine.movement.order_intake import apply_orders
from app.engine.movement.road_meetings import resolve_road_meetings
from app.engine.movement.state import MovementRun
from app.engine.phases import PhaseContext, PhaseResult
from app.engine.visibility.scouting import resolve_map_scout
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import AcceptedCommand, CommandStatus
from app.models.orders import MapScoutOrder
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState


def _failure(command: AcceptedCommand, reason: str) -> None:
    command.status = CommandStatus.FAILED
    command.failure_reason = reason


def _validate_due(
    world: WorldState, command: AcceptedCommand, context: PhaseContext
) -> bool:
    try:
        validate_empire_command(world, command.command, context.scenario)
    except SimulationServiceError:
        _failure(command, "command_unavailable")
        return False
    return True


def _mark_application(
    world: WorldState, command: AcceptedCommand, events: list[EventLogEntry]
) -> None:
    rejection = next(
        (
            event
            for event in events
            if event.kind in ("economy_order_rejected", "movement_order_rejected")
        ),
        None,
    )
    if rejection is not None:
        _failure(command, "command_unavailable")
        return
    command.status = CommandStatus.APPLIED
    command.applied_turn = world.clock.turn
    command.applied_wave = world.progress.completed_waves


class CampaignEconomyPhase:
    name = PhaseName.ECONOMY

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        run = start_run(world, context.scenario)
        run.can_pay_engaged = True
        apply_economy_orders(run, context.orders)
        for command in due_commands(world, self.name):
            if not _validate_due(world, command, context):
                continue
            if isinstance(command.command, MapScoutOrder):
                _apply_map_scout(world, command, context)
                continue
            before = len(run.events)
            apply_economy_orders(run, [queued_order(command)])
            _mark_application(world, command, run.events[before:])
        for faction_id in active_faction_ids(world):
            pause = settle_faction(run, faction_id, context)
            if pause is not None:
                return PhaseResult(world, pause=pause)
        return PhaseResult(world, run.events)


def _apply_map_scout(
    world: WorldState, command: AcceptedCommand, context: PhaseContext
) -> None:
    scout_order = command.command
    if not isinstance(scout_order, MapScoutOrder):
        return
    report = resolve_map_scout(
        world,
        context.scenario,
        scout_order.faction_id,
        scout_order.target_region_id,
        command.id,
    )
    world.map_scout_reports[report.id] = report
    command.status = CommandStatus.APPLIED
    command.applied_turn = world.clock.turn
    command.applied_wave = world.progress.completed_waves


class CampaignMovementPhase:
    name = PhaseName.MOVEMENT

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        run = MovementRun(
            world,
            build_map_index(context.scenario.map),
            context.scenario.tuning.movement,
        )
        apply_orders(run, context.orders)
        for command in due_commands(world, self.name):
            if not _validate_due(world, command, context):
                continue
            before = len(run.events)
            apply_orders(run, [queued_order(command)])
            _mark_application(world, command, run.events[before:])
        advance_all(run)
        resolve_road_meetings(run)
        return PhaseResult(world, run.events)
