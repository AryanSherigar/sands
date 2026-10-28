from dataclasses import dataclass

from app.engine.commands.ledger import due_commands
from app.engine.conditions import read_metric
from app.engine.events.answer import apply_answer, validate_answer
from app.engine.events.candidates import list_subjects
from app.engine.events.constants import (
    ANSWER_WINDOW_TURNS,
    FREQUENCY_ROLL_RANGE,
    MAX_NEW_EVENTS_PER_TURN,
    PENDING_EVENT_ID_PREFIX,
)
from app.engine.events.decay import decay_memories
from app.engine.events.expiry import expire_pending
from app.engine.events.log import event_fired
from app.engine.events.memory import find_memory, record_firing
from app.engine.events.naming import subject_name
from app.engine.events.tiers import tier_level
from app.engine.negotiation import player_faction_id
from app.engine.phases import PhaseContext, PhaseResult
from app.engine.rng import DeterministicRng
from app.engine.subjects import Subject
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import CommandStatus
from app.models.orders import AnswerEventOrder
from app.models.world_events import EventLogEntry, PendingEvent, PhaseName
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.conditions import (
    SUBJECT_PLACEHOLDER,
    Comparison,
    ConditionMetric,
    ConditionOperator,
    ConditionScope,
    iter_comparisons,
    metric_scope,
)
from strategy_contracts.event_catalog import effective_events
from strategy_contracts.events import EventDefinition
from strategy_contracts.scenario import StrategyScenario


@dataclass(frozen=True)
class Firing:
    template: EventDefinition
    subject: Subject
    tier: int


class EventsPhase:
    name = PhaseName.EVENTS

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        scenario = context.scenario
        if not world.events_ruleset or not scenario.toggles.is_events_enabled:
            return PhaseResult(world)
        faction_id = player_faction_id(world)
        decay_memories(world, scenario, faction_id)
        events = _apply_due_answers(world, scenario)
        events += expire_pending(world, scenario, faction_id)
        due = _due_firings(world, scenario, faction_id)
        chosen = _cap(_gate(due, context.rng, scenario.tuning.event_frequency_percent))
        events += [_fire(world, scenario, faction_id, firing) for firing in chosen]
        return PhaseResult(world, events)


def _apply_due_answers(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for command in due_commands(world, PhaseName.EVENTS):
        order = command.command
        if not isinstance(order, AnswerEventOrder):
            continue
        try:
            validate_answer(world, scenario, order)
        except SimulationServiceError:
            command.status = CommandStatus.FAILED
            command.failure_reason = "command_unavailable"
            continue
        events.append(apply_answer(world, scenario, order))
        command.status = CommandStatus.APPLIED
        command.applied_turn = world.clock.turn
        command.applied_wave = world.progress.completed_waves
    return events


def _due_firings(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> list[Firing]:
    templates = effective_events(scenario.events, scenario.disabled_builtin_event_ids)
    return [
        Firing(template, subject, tier)
        for template in templates
        for subject in list_subjects(world, template.subject_kind, faction_id)
        if not _is_pending(world, template.id, subject.id)
        if (tier := _escalated_tier(world, template, subject, faction_id))
    ]


def _is_pending(world: WorldState, template_id: str, subject_id: str) -> bool:
    return any(
        pending.template_id == template_id and pending.subject_id == subject_id
        for pending in world.pending_events
    )


def _escalated_tier(
    world: WorldState, template: EventDefinition, subject: Subject, faction_id: str
) -> int:
    memory = find_memory(world, template.id, subject.id)
    scar = memory.scar if memory is not None else 0
    last_tier = memory.last_tier if memory is not None else 0
    tier = tier_level(world, template, subject, scar=scar, faction_id=faction_id)
    return tier if tier > last_tier else 0


def _gate(
    firings: list[Firing], rng: DeterministicRng, frequency_percent: int
) -> list[Firing]:
    return [
        firing
        for firing in firings
        if rng.fork(firing.template.id, firing.subject.id).roll(FREQUENCY_ROLL_RANGE)
        < frequency_percent
    ]


def _cap(firings: list[Firing]) -> list[Firing]:
    ranked = sorted(
        firings, key=lambda item: (-item.tier, item.template.id, item.subject.id)
    )
    return ranked[:MAX_NEW_EVENTS_PER_TURN]


def _fire(
    world: WorldState, scenario: StrategyScenario, faction_id: str, firing: Firing
) -> EventLogEntry:
    count = world.counters.get(CounterKind.PENDING_EVENT, 0) + 1
    world.counters[CounterKind.PENDING_EVENT] = count
    pending = PendingEvent(
        id=f"{PENDING_EVENT_ID_PREFIX}_{count}",
        template_id=firing.template.id,
        choice_ids=_offered_choice_ids(firing),
        subject_kind=firing.subject.kind,
        subject_id=firing.subject.id,
        subject_name=subject_name(world, scenario, firing.subject),
        tier=firing.tier,
        created_turn=world.clock.turn,
        deadline_turn=world.clock.turn + ANSWER_WINDOW_TURNS,
        cause_key=firing.template.cause_key,
        cause_inputs=_cause_inputs(world, firing, faction_id),
    )
    world.pending_events.append(pending)
    record_firing(world, firing.template.id, firing.subject.id, firing.tier)
    return event_fired(pending)


def _offered_choice_ids(firing: Firing) -> list[str]:
    tier = next(item for item in firing.template.tiers if item.level == firing.tier)
    return tier.choice_ids or [choice.id for choice in firing.template.choices]


def _cause_inputs(world: WorldState, firing: Firing, faction_id: str) -> dict[str, int]:
    inputs: dict[str, int] = {}
    for metric in firing.template.cause_metrics:
        value = read_metric(
            world,
            _probe(firing.template, metric),
            faction_id=faction_id,
            subject=firing.subject,
        )
        if value is not None:
            inputs[metric.value] = value
    return inputs


def _probe(template: EventDefinition, metric: ConditionMetric) -> Comparison:
    is_scoped = metric_scope(metric) is not ConditionScope.FACTION
    return Comparison(
        metric=metric,
        operator=ConditionOperator.GTE,
        value=0,
        subject_id=SUBJECT_PLACEHOLDER if is_scoped else None,
        threshold=_template_threshold(template, metric),
    )


def _template_threshold(
    template: EventDefinition, metric: ConditionMetric
) -> int | None:
    for tier in template.tiers:
        for comparison in iter_comparisons(tier.trigger):
            if comparison.metric is metric and comparison.threshold is not None:
                return comparison.threshold
    return None
