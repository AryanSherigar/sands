from datetime import datetime
from typing import Literal
from uuid import UUID

from app.models.base import WorldModel
from strategy_contracts.events import EventNarrativeBriefing, EventNarrativePayload


class EventDelivery(WorldModel):
    playthrough_id: UUID
    event_id: str
    turn: int
    briefing: EventNarrativeBriefing
    status: Literal["pending", "generating", "completed", "failed"]
    attempts: int = 0
    claim_id: UUID | None = None
    lease_token: UUID | None = None
    lease_expires_at: datetime | None = None
    narration: EventNarrativePayload | None = None
    error_code: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
