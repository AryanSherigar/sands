from app.engine.commands.ledger import PENDING_STATUSES
from app.engine.events.answer import committed_gold, gold_cost
from app.engine.events.lookup import find_template
from app.engine.events.naming import subject_name
from app.engine.subjects import Subject, related_entity_id
from app.models.api_world_view import (
    EffectPreview,
    EventChoiceView,
    EventMemoryView,
    PendingEventView,
)
from app.models.orders import AnswerEventOrder
from app.models.world_events import PendingEvent
from app.models.world_state import WorldState
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.events import EffectSpec, EventChoice, EventDefinition
from strategy_contracts.scenario import StrategyScenario


def project_pending_events(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> list[PendingEventView]:
    views: list[PendingEventView] = []
    for pending in sorted(world.pending_events, key=lambda item: item.id):
        template = find_template(scenario, pending.template_id)
        if template is not None:
            views.append(_pending_view(world, scenario, faction_id, pending, template))
    return views


def _pending_view(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: str,
    pending: PendingEvent,
    template: EventDefinition,
) -> PendingEventView:
    queued = _queued_answer(world, faction_id, pending.id)
    offered = [choice for choice in template.choices if choice.id in pending.choice_ids]
    return PendingEventView(
        id=pending.id,
        template_id=template.id,
        name=template.name,
        subject_kind=pending.subject_kind,
        subject_id=pending.subject_id,
        subject_name=pending.subject_name,
        region_id=_region_of(world, Subject(pending.subject_kind, pending.subject_id)),
        tier=pending.tier,
        max_tier=template.tiers[-1].level,
        created_turn=pending.created_turn,
        deadline_turn=pending.deadline_turn,
        cause_key=pending.cause_key,
        cause_inputs=pending.cause_inputs,
        choices=[
            _choice_view(world, scenario, faction_id, pending, choice)
            for choice in offered
        ],
        neglect_effects=_previews(template.neglect_effects),
        queued_choice_id=queued[1] if queued else None,
        queued_command_id=queued[0] if queued else None,
    )


def _region_of(world: WorldState, subject: Subject) -> str | None:
    return related_entity_id(world, subject, ConditionScope.REGION)


def _queued_answer(
    world: WorldState, faction_id: str, event_id: str
) -> tuple[str, str] | None:
    for command in world.accepted_commands:
        order = command.command
        if (
            isinstance(order, AnswerEventOrder)
            and order.event_id == event_id
            and command.faction_id == faction_id
            and command.status in PENDING_STATUSES
        ):
            return command.id, order.choice_id
    return None


def _choice_view(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: str,
    pending: PendingEvent,
    choice: EventChoice,
) -> EventChoiceView:
    order = AnswerEventOrder(
        faction_id=faction_id, event_id=pending.id, choice_id=choice.id
    )
    faction = world.factions[faction_id]
    treasury_left = faction.treasury - committed_gold(world, scenario, order)
    return EventChoiceView(
        id=choice.id,
        label_hint=choice.label_hint,
        order_cost=choice.order_cost,
        effects=_previews(choice.effects),
        is_affordable=faction.orders_remaining >= choice.order_cost
        and gold_cost(choice) <= treasury_left,
    )


def _previews(effects: list[EffectSpec]) -> list[EffectPreview]:
    return [EffectPreview(kind=effect.kind, amount=effect.amount) for effect in effects]


def project_event_memories(
    world: WorldState, scenario: StrategyScenario
) -> list[EventMemoryView]:
    views: list[EventMemoryView] = []
    for memory in world.event_memories:
        template = find_template(scenario, memory.template_id)
        if template is None or not (memory.last_tier or memory.scar):
            continue
        subject = Subject(template.subject_kind, memory.subject_id)
        views.append(
            EventMemoryView(
                template_id=template.id,
                name=template.name,
                subject_id=memory.subject_id,
                subject_name=subject_name(world, scenario, subject),
                region_id=_region_of(world, subject),
                last_tier=memory.last_tier,
                max_tier=template.tiers[-1].level,
                scar=memory.scar,
            )
        )
    return views
