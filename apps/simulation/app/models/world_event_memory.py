from app.models.base import WorldModel
from strategy_contracts.ids import EntityId, EventId, WholeNumber


class EventMemory(WorldModel):
    template_id: EventId
    subject_id: EntityId
    last_tier: WholeNumber = 0
    calm_turns: WholeNumber = 0
    scar: WholeNumber = 0
