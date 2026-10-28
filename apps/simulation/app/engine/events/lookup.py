from app.models.world_events import PendingEvent
from app.models.world_state import WorldState
from strategy_contracts.event_catalog import effective_events
from strategy_contracts.events import EventChoice, EventDefinition
from strategy_contracts.scenario import StrategyScenario


def find_pending(world: WorldState, event_id: str) -> PendingEvent | None:
    return next((item for item in world.pending_events if item.id == event_id), None)


def find_template(
    scenario: StrategyScenario, template_id: str
) -> EventDefinition | None:
    templates = effective_events(scenario.events, scenario.disabled_builtin_event_ids)
    return next((item for item in templates if item.id == template_id), None)


def find_choice(template: EventDefinition, choice_id: str) -> EventChoice | None:
    return next((item for item in template.choices if item.id == choice_id), None)
