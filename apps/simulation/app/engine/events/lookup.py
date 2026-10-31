from app.models.world_events import PendingEvent
from app.models.world_state import DISASTER_EVENTS_RULESET, WorldState
from strategy_contracts.event_catalog import effective_events
from strategy_contracts.events import EventChoice, EventDefinition
from strategy_contracts.scenario import StrategyScenario


def find_pending(world: WorldState, event_id: str) -> PendingEvent | None:
    return next((item for item in world.pending_events if item.id == event_id), None)


def templates_in_force(
    world: WorldState, scenario: StrategyScenario
) -> list[EventDefinition]:
    return effective_events(
        scenario.events,
        scenario.disabled_builtin_event_ids,
        has_disasters=world.events_ruleset >= DISASTER_EVENTS_RULESET,
    )


def find_template(
    world: WorldState, scenario: StrategyScenario, template_id: str
) -> EventDefinition | None:
    templates = templates_in_force(world, scenario)
    return next((item for item in templates if item.id == template_id), None)


def find_choice(template: EventDefinition, choice_id: str) -> EventChoice | None:
    return next((item for item in template.choices if item.id == choice_id), None)
