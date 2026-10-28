from dataclasses import dataclass

from app.engine.battles.control import apply_control_choice
from app.engine.commands.budget import command_cost, reserve_cost
from app.engine.commands.ledger import pending_economy_commands
from app.engine.commands.timing import (
    command_slot,
    execution_boundary,
    is_uprising_queued,
    require_window,
)
from app.engine.commands.validation import (
    validate_battle_command,
    validate_empire_command,
)
from app.engine.internal.resolution import apply_resolution
from app.engine.summaries.triggers import evaluate_summary_triggers
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import (
    AcceptedCommand,
    Command,
    CommandStatus,
    DelegateBattleCommand,
    ResolveUprisingCommand,
    TakeCommandCommand,
)
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.scenario import StrategyScenario


@dataclass(frozen=True)
class CommandAcceptance:
    world: WorldState
    command: AcceptedCommand | None
    events: list[EventLogEntry]


def _existing(
    world: WorldState, identity: str, command: Command, actor_id: str
) -> AcceptedCommand | None:
    previous = next(
        (item for item in world.accepted_commands if item.id == identity), None
    )
    if previous is not None and (
        previous.command != command or previous.actor_id != actor_id
    ):
        raise CommandError("command identity conflicts", "idempotency_conflict")
    return previous


def require_slot(world: WorldState, command: Command) -> None:
    turn, wave = execution_boundary(world, command)
    key = (
        command.faction_id,
        getattr(command, "battle_id", None),
        turn,
        wave,
        command_slot(command),
    )
    for previous in world.accepted_commands:
        previous_key = (
            previous.faction_id,
            previous.battle_id,
            previous.execution_turn,
            previous.execution_wave,
            command_slot(previous.command),
        )
        if previous_key == key:
            raise CommandError("command slot already reserved", "duplicate_slot")


def _record(
    world: WorldState,
    scenario: StrategyScenario,
    command: Command,
    identity: str,
    operation_id: str,
    actor_id: str,
) -> CommandAcceptance:
    turn, wave = execution_boundary(world, command)
    accepted = AcceptedCommand(
        id=identity,
        operation_id=operation_id,
        actor_id=actor_id,
        faction_id=command.faction_id,
        battle_id=getattr(command, "battle_id", None),
        accepted_turn=world.clock.turn,
        accepted_wave=world.progress.completed_waves,
        execution_turn=turn,
        execution_wave=wave,
        reserved_cost=command_cost(command, scenario, world),
        command=command.model_copy(deep=True),
        status=CommandStatus.DEFERRED
        if turn > world.clock.turn
        else CommandStatus.ACCEPTED,
    )
    return _store_acceptance(world, accepted, scenario)


def _store_acceptance(
    world: WorldState, accepted: AcceptedCommand, scenario: StrategyScenario
) -> CommandAcceptance:
    owned = world.model_copy(deep=True)
    reserve_cost(owned, accepted.faction_id, accepted.reserved_cost)
    owned.accepted_commands.append(accepted)
    if owned.battle_control_ruleset and isinstance(
        accepted.command, TakeCommandCommand | DelegateBattleCommand
    ):
        apply_control_choice(owned, accepted)
    is_immediate_answer = isinstance(
        accepted.command, ResolveUprisingCommand
    ) and not is_uprising_queued(owned)
    if is_immediate_answer:
        event = apply_resolution(owned, accepted.command, scenario.tuning.internal)
        accepted.status = CommandStatus.APPLIED
        accepted.applied_turn = owned.clock.turn
        accepted.applied_wave = 0
        events = _stamp_events(owned, [event])
        if owned.summary_ruleset == 2:
            evaluate_summary_triggers(owned, scenario, events, world)
        return CommandAcceptance(owned, accepted, events)
    return CommandAcceptance(owned, accepted, [])


def _stamp_events(
    world: WorldState, events: list[EventLogEntry]
) -> list[EventLogEntry]:
    last_sequence = world.counters.get(CounterKind.EVENT_SEQ, 0)
    stamped = [
        event.model_copy(
            update={"seq": last_sequence + index, "turn": world.clock.turn}
        )
        for index, event in enumerate(events, start=1)
    ]
    world.counters[CounterKind.EVENT_SEQ] = last_sequence + len(stamped)
    return stamped


def _authorize(world: WorldState, command: Command, faction_id: str) -> None:
    if (
        command.faction_id != faction_id
        or faction_id not in world.factions
        or world.factions[faction_id].is_destroyed
    ):
        raise CommandError("faction unavailable", "not_found", 404)


def _validate_acceptance(
    world: WorldState,
    scenario: StrategyScenario,
    command: Command,
    expected_turn: int,
    expected_wave: int,
) -> bool:
    can_choose_control = isinstance(command, TakeCommandCommand | DelegateBattleCommand)
    if world.progress.phase is not None:
        require_window(
            world, expected_turn, expected_wave, can_choose_control=can_choose_control
        )
    elif expected_turn != world.clock.turn or expected_wave != 0:
        raise CommandError("stale planning cursor", "stale_cursor")
    require_slot(world, command)
    if getattr(command, "battle_id", None) is not None:
        require_window(
            world, expected_turn, expected_wave, can_choose_control=can_choose_control
        )
        return validate_battle_command(world, command, scenario)
    validate_empire_command(
        world, command, scenario, pending_economy_commands(world, command.faction_id)
    )
    return False


def check_acceptance(
    world: WorldState,
    scenario: StrategyScenario,
    command: Command,
    *,
    faction_id: str,
    expected_turn: int,
    expected_wave: int,
) -> None:
    """Raise the CommandError accept_command would raise, without copying or recording."""
    _authorize(world, command, faction_id)
    is_unchanged = _validate_acceptance(
        world, scenario, command, expected_turn, expected_wave
    )
    if is_unchanged:
        return
    cost = command_cost(command, scenario, world)
    if world.factions[command.faction_id].orders_remaining < cost:
        raise CommandError("insufficient command points", "insufficient_points")


def accept_command(
    world: WorldState,
    scenario: StrategyScenario,
    command: Command,
    *,
    command_id: str,
    operation_id: str,
    actor_id: str,
    faction_id: str,
    expected_turn: int,
    expected_wave: int,
) -> CommandAcceptance:
    """Reserve one owned command; the service must authorize actor/faction binding and durable operation retries."""
    _authorize(world, command, faction_id)
    previous = _existing(world, command_id, command, actor_id)
    if previous is not None:
        return CommandAcceptance(
            world.model_copy(deep=True), previous.model_copy(deep=True), []
        )
    is_unchanged = _validate_acceptance(
        world, scenario, command, expected_turn, expected_wave
    )
    if is_unchanged:
        return CommandAcceptance(world.model_copy(deep=True), None, [])
    return _record(world, scenario, command, command_id, operation_id, actor_id)
