from datetime import datetime
from uuid import UUID

from app.models.base import WorldModel
from strategy_contracts.art import ArtKind, ArtStatus


class ArtDelivery(WorldModel):
    playthrough_id: UUID
    kind: ArtKind
    item_id: str
    status: ArtStatus
    attempts: int
    claim_id: UUID | None
    lease_token: UUID | None
    lease_expires_at: datetime | None
    art_url: str | None
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None
