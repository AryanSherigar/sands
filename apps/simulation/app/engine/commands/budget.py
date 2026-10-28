from app.engine.commands.timing import is_uprising_queued
from app.engine.events.answer import resolve_answer
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import Command
from app.models.orders import AnswerEventOrder
from app.models.world_state import WorldState
from strategy_contracts.enums import OrderKind
from strategy_contracts.scenario import StrategyScenario

FREE_BATTLE_COMMANDS = frozenset(("take_command", "delegate_battle"))


def command_cost(
    command: Command, scenario: StrategyScenario, world: WorldState
) -> int:
    if command.kind in FREE_BATTLE_COMMANDS:
        return 0
    if command.kind == "resolve_uprising":
        return _uprising_cost(world, scenario)
    if isinstance(command, AnswerEventOrder):
        return resolve_answer(world, scenario, command)[2].order_cost
    if getattr(command, "battle_id", None) is not None:
        return scenario.tuning.battle.command_cost
    return scenario.tuning.order_costs[OrderKind(command.kind)]


def _uprising_cost(world: WorldState, scenario: StrategyScenario) -> int:
    if not is_uprising_queued(world):
        return 0
    return scenario.tuning.internal.uprising_response_order_cost


def reserve_cost(world: WorldState, faction_id: str, cost: int) -> None:
    faction = world.factions[faction_id]
    if faction.orders_remaining < cost:
        raise CommandError("insufficient command points", "insufficient_points")
    faction.orders_remaining -= cost
