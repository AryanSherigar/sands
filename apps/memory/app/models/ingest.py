"""Wire contract for POST /v1/ingest/items."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from app.models.templates import ParticipantPayload
from pydantic import BaseModel, Field, field_validator, model_validator

ITEM_KIND_ORDER: dict[str, int] = {
    "register_playthrough": 0,
    "turn": 1,
    "participants": 2,
    "flush": 3,
}


class AcceptedDeltaItem(BaseModel):
    kind: Literal[
        "state_mutation",
        "automatic_effect",
        "encounter_outcome",
        "roll",
        "map_discovery",
    ]
    key: str
    before: object | None = None
    after: object | None = None
    detail: dict[str, object] = Field(default_factory=dict)


class AcceptedDelta(BaseModel):
    items: list[AcceptedDeltaItem] = Field(default_factory=list)


class RejectedCall(BaseModel):
    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] = Field(default_factory=dict)


class PlayerEntityPayload(BaseModel):
    authored_entity_id: UUID
    canonical_name: str
    aliases: list[str] = []
    entity_type: str


class SetupFactPayload(BaseModel):
    fact_id: UUID
    subject_entity_id: UUID
    predicate: str
    object_entity_id: UUID | None = None
    object_literal: str | None = None


class RegisterPayload(BaseModel):
    scenario_id: UUID
    publish_revision: int = Field(ge=0)
    player_entity: PlayerEntityPayload | None = None
    setup_facts: list[SetupFactPayload] = []
    participants: list[ParticipantPayload] = []
    tracked_fields: list[str] = []


class TurnPayload(BaseModel):
    turn_id: UUID
    turn_number: int = Field(ge=1)
    participant_id: UUID
    action_mode: str = Field(min_length=1)
    action_text: str = ""
    narration_text: str = ""
    accepted_delta: AcceptedDelta = Field(default_factory=AcceptedDelta)
    rejected_calls: list[RejectedCall] = []
    created_at: datetime = Field(default_factory=datetime.now)


class RegisterItem(BaseModel):
    item_kind: Literal["register_playthrough"]
    sequence: Literal[0]
    payload: RegisterPayload

    @field_validator("sequence")
    @classmethod
    def validate_sequence_is_zero(cls, v: int) -> int:
        if v != 0:
            raise ValueError("RegisterItem sequence must be 0")
        return v


class TurnItem(BaseModel):
    item_kind: Literal["turn"]
    sequence: int = Field(ge=1)
    payload: TurnPayload

    @model_validator(mode="after")
    def validate_sequence_matches_turn_number(self) -> "TurnItem":
        if self.sequence != self.payload.turn_number:
            raise ValueError(
                f"sequence ({self.sequence}) must match payload.turn_number "
                f"({self.payload.turn_number})"
            )
        return self


class ParticipantsPayload(BaseModel):
    participants: list[ParticipantPayload]


class ParticipantsItem(BaseModel):
    item_kind: Literal["participants"]
    sequence: int = Field(ge=0)
    payload: ParticipantsPayload


class FlushItem(BaseModel):
    item_kind: Literal["flush"]
    sequence: int = Field(ge=1)


IngestItem = Annotated[
    RegisterItem | TurnItem | ParticipantsItem | FlushItem,
    Field(discriminator="item_kind"),
]


class IngestRequest(BaseModel):
    delivery_id: UUID | None = None
    playthrough_id: UUID
    items: list[IngestItem] = Field(min_length=1)


class IngestItemOutcome(BaseModel):
    item_kind: str
    sequence: int
    outcome: Literal["applied", "duplicate"]


class IngestResponse(BaseModel):
    playthrough_id: UUID
    ingested_seq: int
    latest_seq_seen: int
    items: list[IngestItemOutcome]
