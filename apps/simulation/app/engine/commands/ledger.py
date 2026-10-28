from collections.abc import Sequence

from app.engine.commands.timing import owning_phase
from app.engine.economy.orders import apply_economy_orders
from app.engine.economy.state import start_run
from app.models.battle_command import AcceptedCommand, CommandStatus
from app.models.orders import QueuedOrder
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

PENDING_STATUSES = (CommandStatus.ACCEPTED, CommandStatus.DEFERRED)
REJECTION_KINDS = ("economy_order_rejected", "movement_order_rejected")


def queued_order(command: AcceptedCommand) -> QueuedOrder:
    return QueuedOrder(
        id=command.id, order=command.command, cost=0, queued_turn=command.accepted_turn
    )


def pending_economy_commands(
    world: WorldState, faction_id: FactionId
) -> list[AcceptedCommand]:
    return [
        command
        for command in world.accepted_commands
        if command.faction_id == faction_id
        and command.status in PENDING_STATUSES
        and owning_phase(command) == PhaseName.ECONOMY
    ]


def due_commands(world: WorldState, phase: PhaseName) -> list[AcceptedCommand]:
    return [
        command
        for command in world.accepted_commands
        if command.status in PENDING_STATUSES
        and command.execution_turn == world.clock.turn
        and owning_phase(command) == phase
    ]


def rejection_reason(events: Sequence[EventLogEntry]) -> str | None:
    for event in events:
        if event.kind in REJECTION_KINDS:
            return event.cause.summary_key.removeprefix(f"{event.kind}_")
    return None


def unaffordable_pending_ids(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> set[str]:
    """Queued economy commands that would be rejected if they ran now, in queue order."""
    run = start_run(world.model_copy(deep=True), scenario)
    run.can_pay_engaged = True
    rejected: set[str] = set()
    for command in pending_economy_commands(world, faction_id):
        before = len(run.events)
        apply_economy_orders(run, [queued_order(command)])
        if rejection_reason(run.events[before:]) is not None:
            rejected.add(command.id)
    return rejected
