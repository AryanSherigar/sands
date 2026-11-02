from datetime import datetime
from uuid import UUID

from app.models.base import WorldModel
from strategy_contracts.epilogue import EpilogueBriefing
from strategy_contracts.summary import SummaryStatus


class EpilogueDelivery(WorldModel):
    playthrough_id: UUID
    briefing: EpilogueBriefing
    input_hash: str
    status: SummaryStatus
    attempts: int
    claim_id: UUID | None
    lease_token: UUID | None
    lease_expires_at: datetime | None
    narration: str | None
    completion_hash: str | None
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None
