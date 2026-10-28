from app.engine.commands.ledger import PENDING_STATUSES
from app.engine.events.effects import EffectContext, apply_effect
from app.engine.events.log import event_answered
from app.engine.events.lookup import find_choice, find_pending, find_template
from app.engine.events.memory import add_scar
from app.engine.subjects import Subject
from app.exceptions.command_exceptions import CommandError
from app.models.orders import AnswerEventOrder
from app.models.world_events import EventLogEntry, PendingEvent
from app.models.world_state import WorldState
from strategy_contracts.events import EffectKind, EventChoice, EventDefinition
from strategy_contracts.scenario import StrategyScenario


def resolve_answer(
    world: WorldState, scenario: StrategyScenario, order: AnswerEventOrder
) -> tuple[PendingEvent, EventDefinition, EventChoice]:
    """The pending event, its template and the chosen option, or a command error."""
    pending = find_pending(world, order.event_id)
    if pending is None or not world.factions[order.faction_id].is_player:
        raise CommandError("event unavailable", "not_found", 404)
    if pending.deadline_turn < world.clock.turn:
        raise CommandError("event has expired", "event_expired")
    template = find_template(scenario, pending.template_id)
    choice = find_choice(template, order.choice_id) if template else None
    if choice is None or choice.id not in pending.choice_ids:
        raise CommandError("choice unavailable", "invalid_choice", 422)
    return pending, template, choice


def gold_cost(choice: EventChoice) -> int:
    return sum(
        -effect.amount
        for effect in choice.effects
        if effect.kind is EffectKind.GOLD and effect.amount < 0
    )


def committed_gold(
    world: WorldState, scenario: StrategyScenario, order: AnswerEventOrder
) -> int:
    """Gold already promised by the faction's other queued event answers."""
    total = 0
    for queued in world.accepted_commands:
        other = queued.command
        is_other_answer = (
            isinstance(other, AnswerEventOrder)
            and other.faction_id == order.faction_id
            and other.event_id != order.event_id
            and queued.status in PENDING_STATUSES
        )
        if is_other_answer:
            total += gold_cost(resolve_answer(world, scenario, other)[2])
    return total


def validate_answer(
    world: WorldState, scenario: StrategyScenario, order: AnswerEventOrder
) -> None:
    _, _, choice = resolve_answer(world, scenario, order)
    available = world.factions[order.faction_id].treasury - committed_gold(
        world, scenario, order
    )
    if gold_cost(choice) > available:
        raise CommandError("insufficient funds", "insufficient_funds", 422)


def apply_answer(
    world: WorldState, scenario: StrategyScenario, order: AnswerEventOrder
) -> EventLogEntry:
    pending, template, choice = resolve_answer(world, scenario, order)
    subject = Subject(pending.subject_kind, pending.subject_id)
    context = EffectContext(world, order.faction_id, subject, scenario)
    changes = [
        change for effect in choice.effects for change in apply_effect(context, effect)
    ]
    add_scar(world, template.id, subject.id, choice.scar_amount)
    world.pending_events.remove(pending)
    return event_answered(pending, choice.id, changes)
