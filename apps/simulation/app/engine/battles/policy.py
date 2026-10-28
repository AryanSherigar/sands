import hashlib
import json

from app.engine.battles.modifiers import validate_tactic
from app.engine.battles.reconnaissance import intelligence_id
from app.engine.battles.views import IntentBriefing
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import (
    BattleCommand,
    DeceiveCommand,
    ReconCommand,
    SetPlanCommand,
    SurrenderCommand,
    WithdrawCommand,
)
from app.models.battle_intelligence import (
    BattleIntent,
    IntentKind,
    IntentSource,
    MissionTarget,
)
from app.models.world_battle import BattleAction, BattleState, StandingPlan
from app.models.world_state import WorldState
from strategy_contracts.battle import (
    BattleTuning,
    Formation,
    SupplyState,
    Tactic,
    WithdrawalPolicy,
)
from strategy_contracts.scenario import StrategyScenario

POLICY_VERSION = "battle-intent-v1"


def fallback_intent(
    briefing: IntentBriefing, tuning: BattleTuning, should_press: bool = False
) -> IntentKind:
    """Estimate advantage only from the observer's reports and broad contact estimate."""
    own = briefing.battle.own_contingent
    if own.morale <= tuning.intent_low_morale or own.supply == SupplyState.ISOLATED:
        return IntentKind.PRESERVE
    if should_press:
        return IntentKind.PRESS
    estimated = sum(opponent.strength.maximum for opponent in briefing.battle.opponents)
    if sum(own.troops.values()) > estimated * tuning.intent_advantage_ratio:
        return IntentKind.PRESS
    return IntentKind.DELAY


def _desired_plan(briefing: IntentBriefing, intent: IntentKind) -> StandingPlan:
    own = briefing.battle.own_contingent
    plan = own.plan.model_copy(deep=True)
    if intent == IntentKind.PRESS:
        plan.formation = Formation.CONCENTRATED
        plan.tactic = Tactic.PRESS
        plan.withdrawal_policy = WithdrawalPolicy.BALANCED
    else:
        plan.formation = Formation.DEFENSIVE
        plan.tactic = Tactic.HOLD
        plan.withdrawal_policy = WithdrawalPolicy.PRESERVE
    if plan.tactic not in briefing.legal_tactics:
        plan.tactic = Tactic.HOLD
    return plan


def _support_instruction(
    briefing: IntentBriefing, intent: IntentKind
) -> BattleCommand | None:
    battle = briefing.battle
    if intent == IntentKind.PRESERVE and BattleAction.DECEIVE in battle.legal_commands:
        return DeceiveCommand(faction_id=briefing.faction_id, battle_id=battle.id)
    subjects = [
        opponent.faction_id
        for opponent in battle.opponents
        if not any(
            report.observed_turn == battle.current_turn
            and report.observed_exchange == battle.total_exchanges
            for report in opponent.reports
        )
    ]
    if subjects and BattleAction.RECONNOITRE in battle.legal_commands:
        return ReconCommand(
            faction_id=briefing.faction_id,
            battle_id=battle.id,
            subject_faction_id=sorted(subjects)[0],
            target=MissionTarget.COMPOSITION,
        )
    return None


def choose_instruction(
    briefing: IntentBriefing, intent: IntentKind, tuning: BattleTuning
) -> BattleCommand | None:
    """Propose one affordable command; the global owner reserves the shared faction budget."""
    if (
        briefing.orders_remaining < tuning.command_cost
        or not briefing.battle.legal_commands
    ):
        return None
    faction_id, battle_id = briefing.faction_id, briefing.battle.id
    if intent == IntentKind.SURRENDER:
        return SurrenderCommand(faction_id=faction_id, battle_id=battle_id)
    if intent == IntentKind.WITHDRAW:
        return WithdrawCommand(faction_id=faction_id, battle_id=battle_id)
    plan = _desired_plan(briefing, intent)
    if plan != briefing.battle.own_contingent.plan:
        return SetPlanCommand(faction_id=faction_id, battle_id=battle_id, plan=plan)
    return _support_instruction(briefing, intent)


def _fingerprint(briefing: IntentBriefing, tuning: BattleTuning) -> tuple[str, str]:
    observation = json.dumps(
        briefing.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    fingerprint = hashlib.sha256(observation.encode()).hexdigest()
    encoded = f"{POLICY_VERSION}:{tuning.rule_version}:{fingerprint}".encode()
    return fingerprint, hashlib.sha256(encoded).hexdigest()


def _matches(candidate: BattleIntent, expected: BattleIntent) -> bool:
    names = (
        "battle_id",
        "faction_id",
        "campaign_turn",
        "input_hash",
        "observation_fingerprint",
        "policy_version",
        "intended_wave",
        "activation_wave",
        "activation_exchange",
    )
    return all(getattr(candidate, name) == getattr(expected, name) for name in names)


def select_intent(
    briefing: IntentBriefing,
    tuning: BattleTuning,
    candidate: BattleIntent | None = None,
    should_press: bool = False,
) -> BattleIntent:
    """Freeze matching recorded input or deterministic fallback; no transport or timing I/O."""
    fingerprint, input_hash = _fingerprint(briefing, tuning)
    battle = briefing.battle
    wave = battle.exchanges_used + 1
    expected = BattleIntent(
        id=intelligence_id("battle_intent", battle.id, briefing.faction_id, input_hash),
        battle_id=battle.id,
        faction_id=briefing.faction_id,
        campaign_turn=battle.current_turn,
        kind=fallback_intent(briefing, tuning, should_press),
        source=IntentSource.FALLBACK,
        input_hash=input_hash,
        observation_fingerprint=fingerprint,
        policy_version=POLICY_VERSION,
        intended_wave=wave,
        activation_wave=wave,
        activation_exchange=battle.total_exchanges + 1,
    )
    if candidate is not None and _matches(candidate, expected):
        return candidate.model_copy(deep=True)
    return expected


def normalize_standing_plans(
    world: WorldState, battle: BattleState, scenario: StrategyScenario
) -> None:
    for _, contingent in sorted(battle.contingents.items()):
        try:
            validate_tactic(
                world, battle, contingent, contingent.plan, scenario.tuning.battle
            )
        except SimulationServiceError:
            contingent.plan.tactic = Tactic.HOLD
