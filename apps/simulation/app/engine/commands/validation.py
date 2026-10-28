from collections.abc import Sequence

from app.engine.battles.captures import resolve_capture_decision
from app.engine.battles.modifiers import validate_tactic
from app.engine.battles.state import FIGHTING_STATUSES, troop_count
from app.engine.commands.ledger import queued_order, rejection_reason
from app.engine.commands.timing import DIPLOMACY_KINDS
from app.engine.diplomacy.validation import validate_diplomacy_order
from app.engine.economy.orders import apply_economy_orders
from app.engine.economy.state import start_run
from app.engine.events.answer import validate_answer
from app.engine.internal.resolution import validate_resolution
from app.engine.movement.attack import attack_problem
from app.engine.movement.engagement import armies_in_open_battle
from app.engine.movement.map_index import build_map_index
from app.engine.movement.reasons import RejectReason
from app.engine.movement.route_options import RoutePreferences
from app.engine.movement.route_planning import plan_march
from app.engine.movement.state import MovementRun
from app.engine.visibility.scouting import validate_map_scout_target
from app.exceptions.base import SimulationServiceError
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import (
    AcceptedCommand,
    CaptureDecisionCommand,
    Command,
    CommitReservesCommand,
    DelegateBattleCommand,
    ReconCommand,
    ResolveUprisingCommand,
    SetPlanCommand,
    TakeCommandCommand,
)
from app.models.orders import (
    AnswerEventOrder,
    AttackOrder,
    MapScoutOrder,
    MoveArmyOrder,
    QueuedOrder,
)
from app.models.world_army import ArmyState
from app.models.world_battle import BattleControlMode, BattleState, BattleStatus
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def command_battle(world: WorldState, command: Command) -> BattleState:
    battle = next(
        (
            battle
            for battle in world.battles
            if battle.id == getattr(command, "battle_id", None)
        ),
        None,
    )
    if battle is None or command.faction_id not in battle.contingents:
        raise CommandError("battle unavailable", "not_found", 404)
    if battle.status != BattleStatus.AWAITING_COMMANDS:
        raise CommandError("battle command window is closed")
    contingent = battle.contingents[command.faction_id]
    if contingent.status not in FIGHTING_STATUSES or not troop_count(world, contingent):
        raise CommandError("contingent cannot accept commands")
    return battle


def validate_battle_command(
    world: WorldState, command: Command, scenario: StrategyScenario
) -> bool:
    battle = command_battle(world, command)
    contingent = battle.contingents[command.faction_id]
    if isinstance(command, TakeCommandCommand | DelegateBattleCommand):
        _validate_control_choice(world, battle, command)
        return False
    _require_player_control(world, battle, command.faction_id)
    if isinstance(command, SetPlanCommand):
        try:
            validate_tactic(
                world, battle, contingent, command.plan, scenario.tuning.battle
            )
        except SimulationServiceError as error:
            raise CommandError(
                "tactic unavailable", "unsupported_tactic", 422
            ) from error
        return command.plan == contingent.plan
    if isinstance(command, CommitReservesCommand) and contingent.has_committed_reserves:
        raise CommandError("reserves already committed")
    if isinstance(command, ReconCommand):
        opponent = battle.contingents.get(command.subject_faction_id)
        if opponent is None or opponent.side == contingent.side:
            raise CommandError("reconnaissance subject unavailable", status_code=422)
    if isinstance(command, CaptureDecisionCommand):
        capture = world.scout_captures.get(command.capture_id)
        if capture is None or capture.battle_id != battle.id:
            raise CommandError("capture unavailable", "not_found", 404)
        resolve_capture_decision(
            world, command.capture_id, command.faction_id, command.decision, scenario
        )
    return False


def _require_player_control(
    world: WorldState, battle: BattleState, faction_id: str
) -> None:
    if (
        world.battle_control_ruleset
        and world.factions[faction_id].is_player
        and battle.control_mode != BattleControlMode.PLAYER
    ):
        raise CommandError(
            "take command before issuing battle orders", "control_required", 422
        )


def _validate_control_choice(
    world: WorldState,
    battle: BattleState,
    command: TakeCommandCommand | DelegateBattleCommand,
) -> None:
    if not world.factions[command.faction_id].is_player:
        raise CommandError("battle control unavailable", "not_found", 404)
    if battle.total_exchanges or battle.control_mode.value != "undecided":
        raise CommandError("battle control window is closed", "invalid_lifecycle")
    if isinstance(command, DelegateBattleCommand):
        return
    claimed = any(
        item.control_mode.value == "player" and item.current_turn == world.clock.turn
        for item in world.battles
    )
    pending_claim = any(
        isinstance(item.command, TakeCommandCommand)
        and item.execution_turn == world.clock.turn
        and item.status.value in ("accepted", "deferred")
        for item in world.accepted_commands
    )
    if claimed or pending_claim:
        raise CommandError("battle control already claimed", "control_limit", 422)


def _validate_army(world: WorldState, command: Command) -> None:
    army_id = getattr(command, "army_id", None)
    if army_id is None:
        return
    army = world.armies.get(army_id)
    if army is None or army.owner_id != command.faction_id:
        raise CommandError("army unavailable", "not_found", 404)
    if command.kind == "disband_army" and army_id in armies_in_open_battle(world):
        raise CommandError("engaged army cannot be disbanded", "in_battle", 422)


def _validate_economy(
    world: WorldState,
    command: Command,
    scenario: StrategyScenario,
    pending: Sequence[AcceptedCommand],
) -> None:
    run = start_run(world.model_copy(deep=True), scenario)
    run.can_pay_engaged = True
    for queued in pending:
        apply_economy_orders(run, [queued_order(queued)])
    before = len(run.events)
    candidate = QueuedOrder(
        id="validation", order=command, cost=0, queued_turn=world.clock.turn
    )
    apply_economy_orders(run, [candidate])
    reason = rejection_reason(run.events[before:])
    if reason is not None:
        raise CommandError("order not possible", reason, 422)


def _validate_route(
    world: WorldState, command: MoveArmyOrder | AttackOrder, scenario: StrategyScenario
) -> None:
    run = MovementRun(world, build_map_index(scenario.map), scenario.tuning.movement)
    army = world.armies[command.army_id]
    if isinstance(command, AttackOrder):
        _require_attackable(run, army, command)
        result = plan_march(run, army, command.target_region_id, RoutePreferences())
    else:
        result = plan_march(run, army, command.to_region_id, _move_preferences(command))
    if isinstance(result, RejectReason):
        raise CommandError("movement unavailable", result.value, 422)


def _move_preferences(command: MoveArmyOrder) -> RoutePreferences:
    return RoutePreferences(
        style=command.route_style,
        via=tuple(command.via_region_ids),
        avoid=frozenset(command.avoid_region_ids),
    )


def _require_attackable(
    run: MovementRun, army: ArmyState, command: AttackOrder
) -> None:
    problem = attack_problem(run, army, command.target_region_id)
    if problem is not None:
        raise CommandError("attack target unavailable", problem.value, 422)


def validate_empire_command(
    world: WorldState,
    command: Command,
    scenario: StrategyScenario,
    pending: Sequence[AcceptedCommand] = (),
) -> None:
    """Pass the faction's queued economy commands when accepting; omit them at execution, when the world already reflects every applied order."""
    if command.kind in DIPLOMACY_KINDS:
        validate_diplomacy_order(world, command, scenario)
        return
    if isinstance(command, ResolveUprisingCommand):
        validate_resolution(world, command)
        return
    if isinstance(command, AnswerEventOrder):
        validate_answer(world, scenario, command)
        return
    _validate_army(world, command)
    if isinstance(command, MapScoutOrder):
        validate_map_scout_target(
            world,
            command.faction_id,
            command.target_region_id,
            build_map_index(scenario.map),
        )
    elif isinstance(command, MoveArmyOrder | AttackOrder):
        _validate_route(world, command, scenario)
    elif command.kind != "halt_army":
        _validate_economy(world, command, scenario, pending)
