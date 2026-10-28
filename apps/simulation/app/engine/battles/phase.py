from app.engine.battle_records import populate_battle_contingents
from app.engine.battles.captures import expire_captures
from app.engine.battles.control import pending_decisions
from app.engine.battles.deployment import initialize_targets, reconcile_deployments
from app.engine.battles.significance import classify_battle
from app.engine.battles.weather import refresh_conditions
from app.engine.movement.map_index import build_map_index
from app.engine.phases import PhaseCheckpoint, PhaseContext, PhaseResult
from app.models.world_battle import BattleState, BattleStatus
from app.models.world_events import PhaseName
from app.models.world_state import WorldState


def active_battles(world: WorldState) -> list[BattleState]:
    return sorted(
        (battle for battle in world.battles if battle.status != BattleStatus.RESOLVED),
        key=lambda battle: battle.id,
    )


def _open_battle(world: WorldState, battle: BattleState, context: PhaseContext) -> None:
    populate_battle_contingents(world, battle)
    if world.battle_control_ruleset and not battle.total_exchanges:
        classify_battle(world, battle)
    battle.terrain = build_map_index(context.scenario.map).terrain[battle.region_id]
    if battle.current_turn != world.clock.turn:
        battle.current_turn = world.clock.turn
        battle.exchanges_used = 0
        battle.status = BattleStatus.AWAITING_COMMANDS
    if not battle.total_exchanges and not any(
        contingent.deployments for contingent in battle.contingents.values()
    ):
        initialize_targets(world, battle, context.scenario.tuning.battle)
    refresh_conditions(world, battle.id, context.scenario)
    reconcile_deployments(world, battle, context.scenario.tuning.battle)


class BattlePhase:
    name = PhaseName.BATTLES

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        expired = expire_captures(world, context.scenario)
        world.scout_captures.update(expired.captures)
        world.battles = [
            expired.battles.get(battle.id, battle) for battle in world.battles
        ]
        for battle in active_battles(world):
            _open_battle(world, battle, context)
        if pending_decisions(world):
            return PhaseResult(
                world, checkpoint=PhaseCheckpoint("awaiting_battle_decision")
            )
        if (
            active_battles(world)
            and world.progress.completed_waves
            < context.scenario.tuning.battle.max_exchanges_per_turn
        ):
            return PhaseResult(world, checkpoint=PhaseCheckpoint())
        world.progress.waiting_reason = None
        return PhaseResult(world)
