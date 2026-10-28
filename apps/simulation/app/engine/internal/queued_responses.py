from app.engine.commands.ledger import due_commands
from app.engine.internal.resolution import apply_resolution
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import CommandStatus, ResolveUprisingCommand
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.scenario import InternalTuning

FAILURE_REASON_UNAVAILABLE = "command_unavailable"


def apply_queued_responses(
    world: WorldState, tuning: InternalTuning
) -> list[EventLogEntry]:
    """Answers queued during planning land before this turn's escalation."""
    logged: list[EventLogEntry] = []
    for accepted in due_commands(world, PhaseName.INTERNAL):
        order = accepted.command
        if not isinstance(order, ResolveUprisingCommand):
            continue
        try:
            logged.append(apply_resolution(world, order, tuning))
        except SimulationServiceError:
            accepted.status = CommandStatus.FAILED
            accepted.failure_reason = FAILURE_REASON_UNAVAILABLE
            continue
        accepted.status = CommandStatus.APPLIED
        accepted.applied_turn = world.clock.turn
        accepted.applied_wave = world.progress.completed_waves
    return logged
