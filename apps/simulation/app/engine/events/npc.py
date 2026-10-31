from app.engine.events.answer import gold_cost
from app.engine.events.candidates import list_subjects
from app.engine.events.constants import NEGLECTED_CHOICE_KEY
from app.engine.events.effects import EffectContext, apply_effect
from app.engine.events.firing import (
    Firing,
    cap_firings,
    cause_inputs,
    escalated_tier,
    gate_firings,
)
from app.engine.events.log import event_npc_resolved
from app.engine.events.lookup import templates_in_force
from app.engine.events.memory import add_scar, record_firing
from app.engine.rng import DeterministicRng
from app.models.world_events import EventLogEntry, StateChange
from app.models.world_state import WorldState
from strategy_contracts.events import EffectSpec, EventChoice, EventDefinition
from strategy_contracts.scenario import StrategyScenario


def _npc_faction_ids(world: WorldState) -> list[str]:
    return [
        faction_id
        for faction_id, faction in sorted(world.factions.items())
        if not faction.is_player
        and not faction.is_destroyed
        and faction.leader_id is not None
    ]


def _npc_firings(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: str,
    rng: DeterministicRng,
) -> list[Firing]:
    templates = [
        template
        for template in templates_in_force(world, scenario)
        if template.applies_to_npcs
    ]
    firings = [
        Firing(template, subject, tier)
        for template in templates
        for subject in list_subjects(world, template.subject_kind, faction_id)
        if (tier := escalated_tier(world, template, subject, faction_id))
    ]
    frequency = scenario.tuning.event_frequency_percent
    return cap_firings(gate_firings(firings, rng, frequency))


def _affordable_first_choice(
    world: WorldState, faction_id: str, template: EventDefinition
) -> EventChoice | None:
    first = template.choices[0]
    is_affordable = gold_cost(first) <= world.factions[faction_id].treasury
    return first if is_affordable else None


def _apply_all(context: EffectContext, effects: list[EffectSpec]) -> list[StateChange]:
    return [change for effect in effects for change in apply_effect(context, effect)]


def _resolve(
    world: WorldState, scenario: StrategyScenario, faction_id: str, firing: Firing
) -> EventLogEntry:
    template = firing.template
    choice = _affordable_first_choice(world, faction_id, template)
    effects = template.neglect_effects if choice is None else choice.effects
    scar = template.neglect_scar if choice is None else choice.scar_amount
    inputs = {**cause_inputs(world, firing, faction_id), "tier": firing.tier}
    context = EffectContext(world, faction_id, firing.subject, scenario)
    changes = _apply_all(context, effects)
    record_firing(world, template.id, firing.subject.id, firing.tier)
    add_scar(world, template.id, firing.subject.id, scar)
    outcome = NEGLECTED_CHOICE_KEY if choice is None else choice.id
    return event_npc_resolved(template.cause_key, faction_id, outcome, inputs, changes)


def resolve_npc_events(
    world: WorldState, scenario: StrategyScenario, rng: DeterministicRng
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for faction_id in _npc_faction_ids(world):
        for firing in _npc_firings(world, scenario, faction_id, rng):
            events.append(_resolve(world, scenario, faction_id, firing))
    return events
