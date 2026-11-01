"""Evidence rows: memory_source, memory_span, memory_event."""

from datetime import datetime
from uuid import UUID

from app.models.common import EventKind, ScopeKind, SourceKind
from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    scope_kind: ScopeKind
    scope_id: UUID
    source_kind: SourceKind
    source_ref: str
    sequence: int
    actor_participant_id: UUID | None = None
    content: str
    content_hash: str


class SourceRow(SourceCreate):
    source_id: UUID
    created_at: datetime


class SpanCreate(BaseModel):
    source_id: UUID
    scope_kind: ScopeKind
    scope_id: UUID
    sequence: int
    ordinal: int
    start_offset: int
    end_offset: int
    text: str
    token_count: int
    label: str
    entity_ids: list[UUID] = Field(default_factory=list)
    is_hidden: bool = False
    authored_fact_id: UUID | None = None
    conditional: bool = False


class SpanRow(SpanCreate):
    span_id: UUID


class EventCreate(BaseModel):
    playthrough_id: UUID
    sequence: int
    turn_id: UUID
    event_kind: EventKind
    event_key: str
    is_accepted: bool
    payload: dict[str, object]
    actor_participant_id: UUID | None = None


class EventRow(EventCreate):
    event_id: UUID


class SpanDraft(BaseModel):
    ordinal: int
    start_offset: int
    end_offset: int
    text: str
    token_count: int
    label: str
