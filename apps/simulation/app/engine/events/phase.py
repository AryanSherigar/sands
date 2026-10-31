from app.engine.commands.ledger import due_commands
from app.engine.events.answer import apply_answer, validate_answer
from app.engine.events.candidates import list_subjects
from app.engine.events.constants import (
    ANSWER_WINDOW_TURNS,
    PENDING_EVENT_ID_PREFIX,
)
from app.engine.events.decay import decay_memories
from app.engine.events.expiry import expire_pending
from app.engine.events.firing import (
    Firing,
    cap_firings,
    cause_inputs,
    escalated_tier,
    gate_firings,
)
from app.engine.events.log import event_fired
from app.engine.events.lookup import templates_in_force
from app.engine.events.memory import record_firing
from app.engine.events.naming import subject_name
from app.engine.events.npc import resolve_npc_events
from app.engine.negotiation import player_faction_id
from app.engine.phases import PhaseContext, PhaseResult
from app.engine.subjects import related_entity_id
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import CommandStatus
from app.models.orders import AnswerEventOrder
from app.models.world_clock import (
    MONTHS_PER_TURN,
    MONTHS_PER_YEAR,
    TurnClock,
    current_month,
)
from app.models.world_events import EventLogEntry, PendingEvent, PhaseName
from app.models.world_state import (
    DISASTER_EVENTS_RULESET,
    CounterKind,
    WorldState,
)
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.events import EventNarrativeBriefing
from strategy_contracts.scenario import StrategyScenario


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
        frequency = scenario.tuning.event_frequency_percent
        chosen = cap_firings(gate_firings(due, context.rng, frequency))
        events += [_fire(world, scenario, faction_id, firing) for firing in chosen]
        if world.events_ruleset >= DISASTER_EVENTS_RULESET:
            events += resolve_npc_events(world, scenario, context.rng)
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
    return [
        Firing(template, subject, tier)
        for template in templates_in_force(world, scenario)
        for subject in list_subjects(world, template.subject_kind, faction_id)
        if not _is_pending(world, template.id, subject.id)
        if (tier := escalated_tier(world, template, subject, faction_id))
    ]


def _is_pending(world: WorldState, template_id: str, subject_id: str) -> bool:
    return any(
        pending.template_id == template_id and pending.subject_id == subject_id
        for pending in world.pending_events
    )


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
        cause_inputs=cause_inputs(world, firing, faction_id),
    )
    world.pending_events.append(pending)
    briefing = build_event_briefing(world, scenario, firing, pending)
    world.pending_event_deliveries.append(briefing)
    record_firing(world, firing.template.id, firing.subject.id, firing.tier)
    return event_fired(pending)


def _season_of(clock: TurnClock) -> str:
    month = current_month(clock)
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Autumn"


def _year_of(clock: TurnClock) -> int:
    elapsed_months = clock.start_month - 1 + MONTHS_PER_TURN * clock.turn
    return clock.start_year + elapsed_months // MONTHS_PER_YEAR


def _cause_description(firing: Firing, cause_data: dict[str, int]) -> str:
    if cause_data:
        return ", ".join(f"{k} is {v}" for k, v in cause_data.items())
    return f"{firing.template.cause_key} triggered"


def build_event_briefing(
    world: WorldState,
    scenario: StrategyScenario,
    firing: Firing,
    pending: PendingEvent,
) -> EventNarrativeBriefing:
    reg_id = (
        firing.subject.id
        if firing.subject.kind is ConditionScope.REGION
        else related_entity_id(world, firing.subject, ConditionScope.REGION)
    )
    season_str = f"{_season_of(world.clock)} {_year_of(world.clock)}"
    offered_choices = [
        {"id": choice.id, "label": choice.label_hint}
        for choice in firing.template.choices
        if choice.id in pending.choice_ids
    ]
    return EventNarrativeBriefing(
        playthrough_id=world.playthrough_id,
        event_id=pending.id,
        template_id=firing.template.id,
        template_name=firing.template.name,
        subject_name=pending.subject_name,
        region_id=reg_id,
        tier=firing.tier,
        cause_description=_cause_description(firing, pending.cause_inputs),
        ruler_name=world.ruler.name,
        ruler_traits=list(world.ruler.trait_ids),
        season_year=season_str,
        choices=offered_choices,
    )


def _offered_choice_ids(firing: Firing) -> list[str]:
    tier = next(item for item in firing.template.tiers if item.level == firing.tier)
    return tier.choice_ids or [choice.id for choice in firing.template.choices]
