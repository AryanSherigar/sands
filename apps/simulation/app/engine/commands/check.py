from dataclasses import dataclass

from app.engine.commands.application import check_acceptance
from app.exceptions.command_exceptions import CommandError
from app.models.api_orders import OrderFlag
from app.models.battle_command import Command
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

OVER_BUDGET_CODES = frozenset(("insufficient_points", "insufficient_funds"))
NOT_YOUR_ARMY_CODES = frozenset(("not_found", "unknown_army", "not_your_army"))


@dataclass(frozen=True)
class CommandCheck:
    flag: OrderFlag | None
    reason: str | None
    orders_remaining: int


def order_flag(code: str) -> OrderFlag:
    if code in OVER_BUDGET_CODES:
        return OrderFlag.OVER_BUDGET
    if code in NOT_YOUR_ARMY_CODES:
        return OrderFlag.NOT_YOUR_ARMY
    return OrderFlag.IMPOSSIBLE


def check_command(
    world: WorldState,
    scenario: StrategyScenario,
    command: Command,
    *,
    faction_id: FactionId,
    expected_turn: int,
    expected_wave: int,
) -> CommandCheck:
    """Report whether accept_command would take this order; never charges points or mutates the world."""
    remaining = world.factions[faction_id].orders_remaining
    try:
        check_acceptance(
            world,
            scenario,
            command,
            faction_id=faction_id,
            expected_turn=expected_turn,
            expected_wave=expected_wave,
        )
    except CommandError as error:
        return CommandCheck(order_flag(error.code), error.code, remaining)
    return CommandCheck(None, None, remaining)
