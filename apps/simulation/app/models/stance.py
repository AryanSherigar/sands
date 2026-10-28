from datetime import datetime
from enum import Enum
from uuid import UUID

from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import FactionId, LeaderId, StanceId
from strategy_contracts.limits import MAX_NAME_CHARS, MAX_TEXT_CHARS


class StanceSource(str, Enum):
    MODEL = "model"
    FALLBACK = "fallback"


class StanceMenuItem(WorldModel):
    id: StanceId
    name: str = Field(max_length=MAX_NAME_CHARS)
    description: str = Field(max_length=MAX_TEXT_CHARS)


class StanceBriefing(WorldModel):
    leader_name: str = Field(max_length=MAX_NAME_CHARS)
    trait_notes: list[str]
    ambitions: list[str]
    memories: list[str]
    opinions: list[str]
    current_option_id: StanceId | None
    menu: list[StanceMenuItem]


class StanceRequestState(str, Enum):
    PENDING = "pending"
    LEASED = "leased"
    COMPLETED = "completed"
    FALLBACK = "fallback"
    ACTIVATED = "activated"


class StanceChoice(WorldModel):
    leader_id: LeaderId
    faction_id: FactionId
    due_turn: int = Field(ge=0)
    option_id: StanceId
    source: StanceSource
    reason_code: str = Field(min_length=1, max_length=MAX_NAME_CHARS)
    input_hash: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)


class StanceRequest(WorldModel):
    playthrough_id: UUID
    request_id: str
    leader_id: LeaderId
    faction_id: FactionId
    due_turn: int = Field(ge=0)
    input_hash: str
    briefing: StanceBriefing
    fallback: StanceChoice
    candidate: StanceChoice | None = None
    state: StanceRequestState = StanceRequestState.PENDING
    attempts: int = Field(default=0, ge=0, le=1)
    lease_token: UUID | None = None
    lease_expires_at: datetime | None = None
    created_at: datetime | None = None
