from app.engine.commands.ledger import PENDING_STATUSES, unaffordable_pending_ids
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import AcceptedCommand
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def _find_cancellable(
    world: WorldState, command_id: str, faction_id: FactionId
) -> AcceptedCommand:
    command = next(
        (
            item
            for item in world.accepted_commands
            if item.id == command_id
            and item.faction_id == faction_id
            and item.status in PENDING_STATUSES
        ),
        None,
    )
    if command is None:
        raise CommandError("order unavailable", "not_found", 404)
    if command.battle_id is not None or command.accepted_turn != world.clock.turn:
        raise CommandError("order can no longer be removed", "not_cancellable")
    return command


def _require_planning(world: WorldState, expected_turn: int) -> None:
    if expected_turn != world.clock.turn:
        raise CommandError("stale planning cursor", "stale_cursor")
    if world.progress.phase is not None:
        raise CommandError("orders are locked once the turn ends", "invalid_lifecycle")


def cancel_command(
    world: WorldState,
    scenario: StrategyScenario,
    command_id: str,
    *,
    faction_id: FactionId,
    expected_turn: int,
) -> WorldState:
    """Delete a queued planning order and return its points; the input world is never mutated.

    An order is refused if removing it would leave another queued order unaffordable.
    """
    _require_planning(world, expected_turn)
    command = _find_cancellable(world, command_id, faction_id)
    owned = world.model_copy(deep=True)
    owned.accepted_commands = [
        item for item in owned.accepted_commands if item.id != command_id
    ]
    owned.factions[faction_id].orders_remaining += command.reserved_cost
    newly_broken = unaffordable_pending_ids(
        owned, scenario, faction_id
    ) - unaffordable_pending_ids(world, scenario, faction_id)
    if newly_broken:
        raise CommandError("remove the dependent orders first", "order_has_dependents")
    return owned
