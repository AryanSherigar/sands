from app.models.battle_command import AcceptedCommand, CommandStatus, TakeCommandCommand
from app.models.world_battle import BattleControlMode, BattleState, BattleStatus
from app.models.world_state import WorldState


def pending_decisions(world: WorldState) -> list[BattleState]:
    if not world.battle_control_ruleset:
        return []
    return [
        battle
        for battle in world.battles
        if battle.status != BattleStatus.RESOLVED
        and not battle.total_exchanges
        and battle.is_big
        and battle.control_mode == BattleControlMode.UNDECIDED
        and any(world.factions[item].is_player for item in battle.contingents)
    ]


def has_player_control(world: WorldState) -> bool:
    return any(
        battle.status != BattleStatus.RESOLVED
        and battle.control_mode == BattleControlMode.PLAYER
        for battle in world.battles
    )


def apply_control_choice(world: WorldState, accepted: AcceptedCommand) -> None:
    battle = next(item for item in world.battles if item.id == accepted.battle_id)
    battle.control_mode = BattleControlMode.DELEGATED
    if isinstance(accepted.command, TakeCommandCommand):
        battle.control_mode = BattleControlMode.PLAYER
    accepted.status = CommandStatus.APPLIED
    accepted.applied_turn = world.clock.turn
    accepted.applied_wave = world.progress.completed_waves
    world.progress.waiting_reason = (
        "awaiting_battle_decision" if pending_decisions(world) else "awaiting_commands"
    )
