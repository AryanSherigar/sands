from datetime import datetime
from uuid import UUID

from app.models.base import WorldModel
from strategy_contracts.summary import SummaryBriefing, SummaryStatus


class SummaryDelivery(WorldModel):
    summary_id: UUID
    playthrough_id: UUID
    engine_request_id: str
    briefing: SummaryBriefing
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
