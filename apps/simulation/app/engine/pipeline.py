from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.engine.campaign_completion import complete_campaign
from app.engine.hashing import world_hash
from app.engine.negotiation_triggers import arm_triggered_negotiation
from app.engine.ordering import canonicalize_lists
from app.engine.phases import (
    Phase,
    PhaseCheckpoint,
    PhaseContext,
    PhaseResult,
    ScenePause,
)
from app.engine.rng import derive_rng
from app.engine.stances.apply import apply_due_stances
from app.engine.summaries.triggers import evaluate_summary_triggers
from app.exceptions.world_exceptions import MissingPhaseError, PhaseEventMismatchError
from app.models.orders import QueuedOrder
from app.models.stance import StanceChoice
from app.models.world_battle import ExchangeReceipt
from app.models.world_events import (
    PHASE_ORDER,
    EventLogEntry,
    PhaseName,
    TurnProgress,
    TurnStatus,
)
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.ids import LeaderId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import SceneOutcome


@dataclass
class TurnResult:
    world: WorldState
    events: list[EventLogEntry]
    status: TurnStatus
    pause: ScenePause | None = None
    world_hash: str | None = None
    checkpoint: PhaseCheckpoint | None = None
    receipts: list[ExchangeReceipt] = field(default_factory=list)


def _start_index(world: WorldState) -> int:
    phase = world.progress.phase
    return PHASE_ORDER.index(phase) if phase is not None else 0


def _require_phases(
    remaining: Sequence[PhaseName], phases: Mapping[PhaseName, Phase]
) -> None:
    missing = [name.value for name in remaining if name not in phases]
    if missing:
        raise MissingPhaseError(missing)


def _stamp_events(
    world: WorldState, name: PhaseName, events: list[EventLogEntry]
) -> list[EventLogEntry]:
    for event in events:
        if event.phase is not name:
            raise PhaseEventMismatchError(name.value, event.phase.value)
    last_seq = world.counters.get(CounterKind.EVENT_SEQ, 0)
    stamped = [
        event.model_copy(update={"seq": last_seq + offset, "turn": world.clock.turn})
        for offset, event in enumerate(events, start=1)
    ]
    world.counters[CounterKind.EVENT_SEQ] = last_seq + len(stamped)
    return stamped


def _run_phase(
    phase: Phase,
    name: PhaseName,
    world: WorldState,
    context_fields: dict[str, object],
) -> PhaseResult:
    rng = derive_rng(world.rng.seed, world.clock.turn, name.value)
    context = PhaseContext(rng=rng, **context_fields)
    return phase.run(world.model_copy(deep=True), context)


def _finalize_phase(result: PhaseResult, name: PhaseName) -> list[EventLogEntry]:
    canonicalize_lists(result.world)
    return _stamp_events(result.world, name, result.events)


def _pause_turn(
    world: WorldState, events: list[EventLogEntry], name: PhaseName, pause: ScenePause
) -> TurnResult:
    world.progress = world.progress.model_copy(
        update={
            "phase": name,
            "pending_scene_id": None,
            "waiting_reason": "awaiting_scene"
            if world.progress.is_campaign_active
            else None,
        }
    )
    return TurnResult(world, events, TurnStatus.PAUSED, pause)


def _checkpoint_turn(
    world: WorldState,
    events: list[EventLogEntry],
    name: PhaseName,
    checkpoint: PhaseCheckpoint,
) -> TurnResult:
    world.progress.phase = name
    world.progress.waiting_reason = checkpoint.waiting_reason
    return TurnResult(
        world, events, TurnStatus.AWAITING_COMMANDS, checkpoint=checkpoint
    )


def _complete_turn(
    world: WorldState,
    scenario: StrategyScenario,
    events: list[EventLogEntry],
    recorded_stances: Mapping[LeaderId, StanceChoice],
) -> TurnResult:
    previous = world.model_copy(deep=True) if world.summary_ruleset == 2 else None
    if world.progress.is_campaign_active:
        events.extend(
            _stamp_events(world, PhaseName.TIME, complete_campaign(world, scenario))
        )
    evaluate_summary_triggers(world, scenario, events, previous)
    world.clock.turn += 1
    apply_due_stances(world, recorded_stances)
    world.progress = TurnProgress()
    arm_triggered_negotiation(world, scenario)
    return TurnResult(world, events, TurnStatus.RESOLVED, None, world_hash(world))


def run_turn(
    world: WorldState,
    scenario: StrategyScenario,
    orders: Sequence[QueuedOrder],
    phases: Mapping[PhaseName, Phase],
    resolved_outcomes: Mapping[UUID, SceneOutcome],
    recorded_answers: Mapping[str, str],
    recorded_stances: Mapping[LeaderId, StanceChoice] | None = None,
) -> TurnResult:
    remaining = PHASE_ORDER[_start_index(world) :]
    _require_phases(remaining, phases)
    context_fields: dict[str, object] = {
        "scenario": scenario,
        "orders": tuple(sorted(orders, key=lambda order: order.id)),
        "resolved_outcomes": resolved_outcomes,
        "recorded_answers": recorded_answers,
    }
    working = world.model_copy(deep=True)
    events: list[EventLogEntry] = []
    for name in remaining:
        result = _run_phase(phases[name], name, working, context_fields)
        if result.pause is not None:
            return _pause_turn(working, events, name, result.pause)
        stamped = _finalize_phase(result, name)
        if result.world.summary_ruleset == 2:
            evaluate_summary_triggers(result.world, scenario, stamped, working)
        events += stamped
        working = result.world
        if result.checkpoint is not None:
            return _checkpoint_turn(working, events, name, result.checkpoint)
    return _complete_turn(working, scenario, events, recorded_stances or {})
