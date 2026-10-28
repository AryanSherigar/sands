from collections.abc import Mapping, Sequence

from app.engine.battle_records import populate_battle_contingents
from app.engine.battles.casualties import resolve_combat
from app.engine.battles.deployment import initialize_targets, reconcile_deployments
from app.engine.battles.instructions import (
    activate_intents,
    apply_instructions,
    eligible_commands,
    resolve_declarations,
)
from app.engine.battles.lifecycle import (
    finalize_exchange,
    remove_empty_armies,
    resolve_policy_departures,
)
from app.engine.battles.modifiers import validate_tactic
from app.engine.battles.policy import normalize_standing_plans
from app.engine.battles.results import exchange_result
from app.engine.battles.state import ExchangeResult, ExchangeRun, fighting_contingents
from app.engine.battles.support import resolve_support
from app.engine.battles.weather import refresh_conditions
from app.engine.movement.map_index import build_map_index
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import AcceptedCommand
from app.models.battle_intelligence import BattleIntent
from app.models.world_battle import BattleState, BattleStatus, LossAccounting
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def _battle_for(
    world: WorldState, battle_id: str, scenario: StrategyScenario
) -> BattleState:
    battle = next((battle for battle in world.battles if battle.id == battle_id), None)
    if battle is None:
        raise SimulationServiceError("battle does not exist", status_code=404)
    if battle.status == BattleStatus.RESOLVED:
        raise SimulationServiceError("battle is already resolved")
    if battle.exchanges_used >= scenario.tuning.battle.max_exchanges_per_turn:
        raise SimulationServiceError("battle exchange allowance is exhausted")
    if battle.current_turn != world.clock.turn:
        raise SimulationServiceError("battle must be opened for the current campaign")
    return battle


def _prepare_run(
    world: WorldState, battle_id: str, scenario: StrategyScenario
) -> ExchangeRun:
    owned_world = world.model_copy(deep=True)
    battle = _battle_for(owned_world, battle_id, scenario)
    has_contingents = bool(battle.contingents)
    populate_battle_contingents(owned_world, battle)
    battle.terrain = build_map_index(scenario.map).terrain[battle.region_id]
    if not has_contingents or (
        not battle.total_exchanges
        and not any(
            contingent.deployments for contingent in battle.contingents.values()
        )
    ):
        initialize_targets(owned_world, battle, scenario.tuning.battle)
    refresh_conditions(owned_world, battle_id, scenario)
    normalize_standing_plans(owned_world, battle, scenario)
    return ExchangeRun(
        owned_world, battle, scenario, _initial_accounting(owned_world, battle)
    )


def _initial_accounting(
    world: WorldState, battle: BattleState
) -> dict[str, LossAccounting]:
    army_ids = sorted(
        {
            army_id
            for contingent in fighting_contingents(battle)
            for army_id in contingent.army_ids
            if army_id in world.armies
        }
    )
    return {
        army_id: LossAccounting(
            army_id=army_id,
            before=dict(world.armies[army_id].troops),
            survivors=dict(world.armies[army_id].troops),
        )
        for army_id in army_ids
    }


def resolve_exchange(
    world: WorldState,
    battle_id: str,
    scenario: StrategyScenario,
    commands: Sequence[AcceptedCommand],
    recorded_intents: Mapping[str, BattleIntent],
) -> ExchangeResult:
    """Return a deep-copied proposal without spending orders or resetting allowance.

    Support rules refresh weather/supply. The owner freezes intent policy. Compose battles
    using delta; the global reducer owns event sequences, counters and retreat claims.
    """
    run = _prepare_run(world, battle_id, scenario)
    selected = eligible_commands(run, commands)
    withdrawing, surrendering = apply_instructions(run, selected)
    activate_intents(run, recorded_intents)
    resolve_support(run, selected)
    for contingent in fighting_contingents(run.battle):
        validate_tactic(
            run.world, run.battle, contingent, contingent.plan, scenario.tuning.battle
        )
    reconcile_deployments(run.world, run.battle, scenario.tuning.battle)
    resolve_declarations(run, withdrawing, surrendering)
    _resolve_fighting(run)
    return exchange_result(world, run, selected)


def _resolve_fighting(run: ExchangeRun) -> None:
    resolve_combat(run)
    remove_empty_armies(run)
    resolve_policy_departures(run)
    remove_empty_armies(run)
    reconcile_deployments(run.world, run.battle, run.scenario.tuning.battle)
    finalize_exchange(run)
