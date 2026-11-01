"""Wire models for the greenfield memory service's POST /v1/ingest/items.

Mirrors apps/memory/app/models/ingest.py. The two services are separate
packages, so the shapes are duplicated by design; a change to memory's ingest
contract must be made here in the same commit.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from app.models.accepted_delta import AcceptedDelta
from pydantic import BaseModel, Field


class RegisterPlayerEntity(BaseModel):
    """The authored player entity as chosen at playthrough setup."""

    authored_entity_id: UUID
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    entity_type: str


class RegisterSetupFact(BaseModel):
    """One ground-truth fact derived from the player's setup choices."""

    fact_id: UUID
    subject_entity_id: UUID
    predicate: str
    object_entity_id: UUID | None = None
    object_literal: str | None = None


class ParticipantPayload(BaseModel):
    """A participant and the name extraction attributes their actions to."""

    participant_id: UUID
    display_name: str


class RegisterPayload(BaseModel):
    """Payload of a register_playthrough item, as stored by Core."""

    scenario_id: UUID
    publish_revision: int = Field(ge=0)
    player_entity: RegisterPlayerEntity | None = None
    setup_facts: list[RegisterSetupFact] = Field(default_factory=list)
    participants: list[ParticipantPayload] = Field(default_factory=list)
    tracked_fields: list[str] = Field(default_factory=list)


class ParticipantsPayload(BaseModel):
    """Payload of a participants item, as stored by Core."""

    participants: list[ParticipantPayload]


class RejectedCall(BaseModel):
    """A tool call the validator rejected; never becomes an occurred fact."""

    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] = Field(default_factory=dict)


class TurnPayload(BaseModel):
    """One committed turn, built from its TurnLog row."""

    turn_id: UUID
    turn_number: int = Field(ge=1)
    participant_id: UUID
    action_mode: str = Field(min_length=1)
    action_text: str = ""
    narration_text: str = ""
    accepted_delta: AcceptedDelta = Field(default_factory=AcceptedDelta)
    rejected_calls: list[RejectedCall] = Field(default_factory=list)
    created_at: datetime


class RegisterItem(BaseModel):
    item_kind: Literal["register_playthrough"] = "register_playthrough"
    sequence: Literal[0] = 0
    payload: RegisterPayload


class TurnItem(BaseModel):
    item_kind: Literal["turn"] = "turn"
    sequence: int = Field(ge=1)
    payload: TurnPayload


class ParticipantsItem(BaseModel):
    item_kind: Literal["participants"] = "participants"
    sequence: int = Field(ge=0)
    payload: ParticipantsPayload


class FlushItem(BaseModel):
    item_kind: Literal["flush"] = "flush"
    sequence: int = Field(ge=1)


IngestItem = Annotated[
    RegisterItem | TurnItem | ParticipantsItem | FlushItem,
    Field(discriminator="item_kind"),
]


class IngestRequest(BaseModel):
    """Request body for POST /v1/ingest/items."""

    delivery_id: UUID | None = None
    playthrough_id: UUID
    items: list[IngestItem] = Field(min_length=1)


class IngestItemOutcome(BaseModel):
    item_kind: str
    sequence: int
    outcome: Literal["applied", "duplicate"]


class IngestResponse(BaseModel):
    """Response body for POST /v1/ingest/items."""

    playthrough_id: UUID
    ingested_seq: int
    latest_seq_seen: int
    items: list[IngestItemOutcome]
