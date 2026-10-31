from datetime import datetime
from uuid import UUID

from app.models.base import WorldModel
from strategy_contracts.agents import DispatchBriefing, DispatchStatus


class DispatchDelivery(WorldModel):
    playthrough_id: UUID
    rumor_id: str
    turn: int
    briefing: DispatchBriefing
    status: DispatchStatus
    attempts: int
    claim_id: UUID | None
    lease_token: UUID | None
    lease_expires_at: datetime | None
    narration: str | None
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None
