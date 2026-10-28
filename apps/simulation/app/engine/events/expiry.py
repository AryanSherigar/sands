from app.engine.events.effects import EffectContext, apply_effect
from app.engine.events.log import event_neglected
from app.engine.events.lookup import find_template
from app.engine.events.memory import add_scar
from app.engine.subjects import Subject
from app.models.world_events import EventLogEntry, PendingEvent, StateChange
from app.models.world_state import WorldState
from strategy_contracts.events import EventDefinition
from strategy_contracts.scenario import StrategyScenario


def expire_pending(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> list[EventLogEntry]:
    """Apply the neglect outcome of every unanswered event past its deadline."""
    due = sorted(
        (
            item
            for item in world.pending_events
            if item.deadline_turn <= world.clock.turn
        ),
        key=lambda item: item.id,
    )
    events: list[EventLogEntry] = []
    for pending in due:
        world.pending_events.remove(pending)
        template = find_template(scenario, pending.template_id)
        if template is not None:
            events.append(_neglect(world, scenario, faction_id, pending, template))
    return events


def _neglect(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: str,
    pending: PendingEvent,
    template: EventDefinition,
) -> EventLogEntry:
    subject = Subject(pending.subject_kind, pending.subject_id)
    context = EffectContext(world, faction_id, subject, scenario)
    changes: list[StateChange] = [
        change
        for effect in template.neglect_effects
        for change in apply_effect(context, effect)
    ]
    add_scar(world, template.id, subject.id, template.neglect_scar)
    return event_neglected(pending, changes)
