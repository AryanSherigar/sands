from app.engine.battles.modifiers import validate_tactic
from app.engine.battles.morale import weighted_attribute
from app.engine.battles.reconnaissance import contact_strength
from app.engine.battles.state import FIGHTING_STATUSES, contingent_armies, troop_count
from app.exceptions.base import SimulationServiceError
from app.models.battle_intelligence import ReconReport, ScoutCaptureStatus
from app.models.intent_briefing import IntentBriefing
from app.models.world_battle import (
    BattleAction,
    BattleControlMode,
    BattleState,
    BattleStatus,
    BattleView,
    ContingentView,
    OpponentView,
    StandingPlan,
)
from app.models.world_state import WorldState
from strategy_contracts.battle import SupplyState, Tactic, Weather
from strategy_contracts.enums import TroopType
from strategy_contracts.scenario import StrategyScenario


def observed_battle(
    world: WorldState, battle_id: str, observer_faction_id: str
) -> BattleState:
    battle = next((battle for battle in world.battles if battle.id == battle_id), None)
    if battle is None or observer_faction_id not in battle.contingents:
        raise SimulationServiceError(
            "battle observation is unavailable", status_code=404
        )
    return battle


def _own_contingent(
    world: WorldState, battle: BattleState, faction_id: str
) -> ContingentView:
    contingent = battle.contingents[faction_id]
    armies = contingent_armies(world, contingent)
    troops = {
        troop_type: sum(army.troops.get(troop_type, 0) for army in armies)
        for troop_type in TroopType
    }
    return ContingentView(
        faction_id=faction_id,
        army_ids=sorted(contingent.army_ids),
        troops={troop_type: count for troop_type, count in troops.items() if count},
        morale=weighted_attribute(world, contingent, "morale"),
        fatigue=weighted_attribute(world, contingent, "fatigue"),
        plan=contingent.plan.model_copy(deep=True),
        supply=contingent.supply or SupplyState.ISOLATED,
        status=contingent.status,
    )


def visible_reports(
    world: WorldState, battle: BattleState, observer: str, subject: str
) -> list[ReconReport]:
    return [
        report.model_copy(deep=True)
        for _, report in sorted(world.recon_reports.items())
        if report.battle_id == battle.id
        and report.observer_faction_id == observer
        and report.subject_faction_id == subject
        and (
            report.observed_turn < world.clock.turn
            or (
                report.observed_turn == world.clock.turn
                and report.available_from_wave <= battle.exchanges_used + 1
            )
        )
    ]


def _opponents(
    world: WorldState, battle: BattleState, observer: str
) -> list[OpponentView]:
    own_side = battle.contingents[observer].side
    opponents = []
    for identity, contingent in sorted(battle.contingents.items()):
        if contingent.side == own_side:
            continue
        reports = visible_reports(world, battle, observer, identity)
        latest = _latest_report(reports)
        strength = (
            latest.strength
            if latest
            else contact_strength(troop_count(world, contingent))
        )
        opponents.append(
            OpponentView(
                faction_id=identity,
                strength=strength.model_copy(deep=True),
                reports=reports,
            )
        )
    return opponents


def _capture_ids(world: WorldState, battle: BattleState, observer: str) -> list[str]:
    return [
        identity
        for identity, capture in sorted(world.scout_captures.items())
        if capture.battle_id == battle.id
        and capture.captor_faction_id == observer
        and capture.status == ScoutCaptureStatus.DETAINED
        and not capture.has_decided
        and capture.expires_turn > world.clock.turn
    ]


def _legal_commands(
    world: WorldState, battle: BattleState, observer: str
) -> list[BattleAction]:
    contingent = battle.contingents[observer]
    if (
        battle.status != BattleStatus.AWAITING_COMMANDS
        or contingent.status not in FIGHTING_STATUSES
        or not troop_count(world, contingent)
    ):
        return []
    actions = [
        action for action in BattleAction if action != BattleAction.CAPTURE_DECISION
    ]
    if _capture_ids(world, battle, observer):
        actions.append(BattleAction.CAPTURE_DECISION)
    if world.battle_control_ruleset:
        actions = _control_actions(world, battle, observer, actions)
    return actions


def _control_actions(
    world: WorldState, battle: BattleState, observer: str, actions: list[BattleAction]
) -> list[BattleAction]:
    choices = [BattleAction.TAKE_COMMAND, BattleAction.DELEGATE_BATTLE]
    if not world.factions[observer].is_player:
        return [action for action in actions if action not in choices]
    if (
        battle.control_mode == BattleControlMode.UNDECIDED
        and not battle.total_exchanges
    ):
        has_claim = any(
            item.control_mode == BattleControlMode.PLAYER
            and item.current_turn == world.clock.turn
            for item in world.battles
        )
        return [BattleAction.DELEGATE_BATTLE] if has_claim else choices
    if battle.control_mode != BattleControlMode.PLAYER:
        return []
    return [action for action in actions if action not in choices]


def project_battle(
    world: WorldState,
    battle_id: str,
    observer_faction_id: str,
    scenario: StrategyScenario,
) -> BattleView:
    """Project allowlisted observations without RNG draws or live hidden army details."""
    battle = observed_battle(world, battle_id, observer_faction_id)
    return BattleView(
        id=battle.id,
        region_id=battle.region_id,
        status=battle.status,
        outcome=battle.outcome,
        current_turn=battle.current_turn,
        exchanges_used=battle.exchanges_used,
        total_exchanges=battle.total_exchanges,
        is_big=battle.is_big,
        control_mode=battle.control_mode,
        terrain=battle.terrain,
        weather=battle.weather or Weather.CLEAR,
        own_contingent=_own_contingent(world, battle, observer_faction_id),
        opponents=_opponents(world, battle, observer_faction_id),
        legal_commands=_legal_commands(world, battle, observer_faction_id),
        command_cost=scenario.tuning.battle.command_cost,
    )


def validate_observed_plan(
    world: WorldState,
    battle_id: str,
    observer_faction_id: str,
    plan: StandingPlan,
    scenario: StrategyScenario,
) -> None:
    battle = observed_battle(world, battle_id, observer_faction_id)
    validate_tactic(
        world,
        battle,
        battle.contingents[observer_faction_id],
        plan,
        scenario.tuning.battle,
    )


def _legal_tactics(
    world: WorldState, battle: BattleState, observer: str, scenario: StrategyScenario
) -> list[Tactic]:
    legal = []
    for tactic in Tactic:
        try:
            validate_tactic(
                world,
                battle,
                battle.contingents[observer],
                StandingPlan(tactic=tactic),
                scenario.tuning.battle,
            )
        except SimulationServiceError:
            continue
        legal.append(tactic)
    return legal


def intent_briefing(
    world: WorldState,
    battle_id: str,
    observer_faction_id: str,
    scenario: StrategyScenario,
) -> IntentBriefing:
    """The provider and pure policy share this observer-only input contract."""
    battle = observed_battle(world, battle_id, observer_faction_id)
    faction = world.factions[observer_faction_id]
    return IntentBriefing(
        battle=project_battle(world, battle_id, observer_faction_id, scenario),
        faction_id=observer_faction_id,
        orders_remaining=faction.orders_remaining,
        treasury=faction.treasury,
        legal_tactics=_legal_tactics(world, battle, observer_faction_id, scenario),
        capture_ids=_capture_ids(world, battle, observer_faction_id),
    )


def _latest_report(reports: list[ReconReport]) -> ReconReport | None:
    return max(
        reports,
        key=lambda report: (report.observed_turn, report.observed_exchange, report.id),
        default=None,
    )
