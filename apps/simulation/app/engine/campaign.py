from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from app.engine.ai.planner import plan_ai_orders
from app.engine.battles.control import has_player_control
from app.engine.battles.phase import BattlePhase
from app.engine.battles.waves import advance_wave
from app.engine.commands.phases import CampaignEconomyPhase, CampaignMovementPhase
from app.engine.diplomacy.phase import DiplomacyPhase, TimePhase
from app.engine.endings import require_game_not_ended
from app.engine.events import EventsPhase
from app.engine.hashing import world_hash
from app.engine.internal import InternalPhase
from app.engine.phases import Phase, PhaseCheckpoint, PhaseContext, PhaseResult
from app.engine.pipeline import TurnResult, run_turn
from app.engine.story_check import StoryCheckPhase
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.battle_intelligence import BattleIntent
from app.models.orders import QueuedOrder
from app.models.stance import StanceChoice
from app.models.world_battle import ExchangeReceipt
from app.models.world_events import PHASE_ORDER, EventLogEntry, PhaseName, TurnStatus
from app.models.world_state import WorldState
from strategy_contracts.ids import LeaderId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import SceneOutcome

RecordedStances = Mapping[LeaderId, StanceChoice]

SUPPORTED_NOOP_PHASES = frozenset(
    set(PHASE_ORDER)
    - {
        PhaseName.DIPLOMACY,
        PhaseName.TIME,
        PhaseName.MOVEMENT,
        PhaseName.BATTLES,
        PhaseName.ECONOMY,
        PhaseName.INTERNAL,
        PhaseName.EVENTS,
        PhaseName.STORY_CHECK,
    }
)


class SupportedNoopPhase:
    def __init__(self, name: PhaseName) -> None:
        if name not in SUPPORTED_NOOP_PHASES:
            raise CampaignProgressError("phase has a supported implementation")
        self.name = name

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        return PhaseResult(world)


def campaign_phases() -> dict[PhaseName, Phase]:
    return {name: SupportedNoopPhase(name) for name in SUPPORTED_NOOP_PHASES} | {
        PhaseName.DIPLOMACY: DiplomacyPhase(),
        PhaseName.TIME: TimePhase(),
        PhaseName.MOVEMENT: CampaignMovementPhase(),
        PhaseName.BATTLES: BattlePhase(),
        PhaseName.ECONOMY: CampaignEconomyPhase(),
        PhaseName.INTERNAL: InternalPhase(),
        PhaseName.EVENTS: EventsPhase(),
        PhaseName.STORY_CHECK: StoryCheckPhase(),
    }


def begin_campaign(
    world: WorldState,
    scenario: StrategyScenario,
    orders: Sequence[QueuedOrder] = (),
    recorded_stances: RecordedStances | None = None,
) -> TurnResult:
    """Run pre-battle phases and return the initial command window, scene pause, or completion."""
    require_game_not_ended(world)
    if world.progress.phase is not None or world.progress.is_campaign_active:
        raise CampaignProgressError("campaign already started", "invalid_lifecycle")
    owned = world.model_copy(deep=True)
    owned.progress.is_campaign_active = True
    planning_events: list[EventLogEntry] = []
    if owned.ai_ruleset:
        plan = plan_ai_orders(owned, scenario)
        owned, planning_events = plan.world, plan.events
    result = run_turn(
        owned, scenario, orders, campaign_phases(), {}, {}, recorded_stances
    )
    result.events = planning_events + result.events
    return _automatic_waves(result, scenario, recorded_stances)


def resume_campaign(
    world: WorldState,
    scenario: StrategyScenario,
    resolved_outcomes: Mapping[UUID, SceneOutcome],
    orders: Sequence[QueuedOrder] = (),
    recorded_stances: RecordedStances | None = None,
) -> TurnResult:
    """Resume a completed wave or a real economy scene; battle windows require advance_wave."""
    require_game_not_ended(world)
    if not world.progress.is_campaign_active or world.progress.waiting_reason in (
        "awaiting_commands",
        "awaiting_battle_decision",
    ):
        raise CampaignProgressError(
            "campaign is not ready to resume", "invalid_lifecycle"
        )
    return run_turn(
        world,
        scenario,
        orders,
        campaign_phases(),
        resolved_outcomes,
        {},
        recorded_stances,
    )


@dataclass(frozen=True)
class CampaignAdvance:
    result: TurnResult
    receipts: list[ExchangeReceipt]


def advance_campaign(
    world: WorldState,
    scenario: StrategyScenario,
    *,
    expected_turn: int,
    expected_wave: int,
    recorded_intents: Mapping[str, BattleIntent] | None = None,
    recorded_stances: RecordedStances | None = None,
) -> CampaignAdvance:
    """One atomic persistence unit: one wave plus remaining campaign phases when complete."""
    require_game_not_ended(world)
    wave = advance_wave(
        world,
        scenario,
        expected_turn=expected_turn,
        expected_wave=expected_wave,
        recorded_intents=recorded_intents,
    )
    if wave.is_complete:
        result = resume_campaign(
            wave.world, scenario, {}, recorded_stances=recorded_stances
        )
        result.events = wave.events + result.events
    else:
        result = TurnResult(
            wave.world,
            wave.events,
            TurnStatus.AWAITING_COMMANDS,
            world_hash=world_hash(wave.world),
            checkpoint=PhaseCheckpoint(),
        )
    result = _automatic_waves(result, scenario, recorded_stances)
    return CampaignAdvance(result, wave.receipts + result.receipts)


def _automatic_waves(
    result: TurnResult,
    scenario: StrategyScenario,
    recorded_stances: RecordedStances | None = None,
) -> TurnResult:
    if not result.world.battle_control_ruleset:
        return result
    events = list(result.events)
    receipts = list(result.receipts)
    while result.world.progress.waiting_reason == "awaiting_commands":
        if has_player_control(result.world):
            break
        wave = advance_wave(
            result.world,
            scenario,
            expected_turn=result.world.clock.turn,
            expected_wave=result.world.progress.completed_waves + 1,
        )
        events.extend(wave.events)
        receipts.extend(wave.receipts)
        result = TurnResult(wave.world, [], TurnStatus.AWAITING_COMMANDS)
        if wave.is_complete:
            result = resume_campaign(
                wave.world, scenario, {}, recorded_stances=recorded_stances
            )
            events.extend(result.events)
    result.events = events
    result.receipts = receipts
    return result
