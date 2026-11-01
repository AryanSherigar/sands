"""Scope registry rows: memory_template and memory_playthrough."""

from datetime import datetime
from uuid import UUID

from app.models.common import (
    TemplateDirectStatus,
    TemplateEnrichmentStatus,
    TemplateMode,
)
from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    scenario_id: UUID
    publish_revision: int
    mode: TemplateMode
    direct_status: TemplateDirectStatus
    enrichment_status: TemplateEnrichmentStatus
    content_hash: str


class TemplateRow(TemplateCreate):
    template_id: UUID
    created_at: datetime
    enrichment_error: str | None = None


class ParticipantPayload(BaseModel):
    participant_id: UUID
    display_name: str


class PlaythroughCreate(BaseModel):
    """playthrough_id is the product playthrough id, which is also its scope_id."""

    playthrough_id: UUID
    template_id: UUID | None
    player_entity_id: UUID | None = None
    participants: list[ParticipantPayload] = Field(default_factory=list)
    tracked_fields: list[str] = Field(default_factory=list)


class PlaythroughRow(PlaythroughCreate):
    ingested_seq: int
    indexed_seq: int
    extracted_seq: int
    latest_seq_seen: int
    flush_requested_through_seq: int | None
    created_at: datetime


class TemplateEntityPayload(BaseModel):
    entity_id: UUID
    entity_type: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    is_player: bool = False


class TemplateFactPayload(BaseModel):
    fact_id: UUID
    subject_entity_id: UUID
    predicate: str
    object_entity_id: UUID | None = None
    object_literal: str | None = None
    when_active: dict[str, object] | None = None
    hidden: bool = False
    superseded_fact_id: UUID | None = None


class TemplateConnectionPayload(BaseModel):
    connection_id: UUID
    entity_id_a: UUID
    entity_id_b: UUID
    label: str | None = None


class MasterTemplateContent(BaseModel):
    entities: list[TemplateEntityPayload] = Field(default_factory=list)
    facts: list[TemplateFactPayload] = Field(default_factory=list)
    map_connections: list[TemplateConnectionPayload] = Field(default_factory=list)


class StoryCardPayload(BaseModel):
    card_id: str
    type: str
    name: str
    content: str


class NewbieTemplateContent(BaseModel):
    story_cards: list[StoryCardPayload] = Field(default_factory=list)
    entities: list[TemplateEntityPayload] = Field(default_factory=list)
    facts: list[TemplateFactPayload] = Field(default_factory=list)
    world_lore: str = ""
    single_lore_prompt: str = ""
    main_conflict: str = ""
    opening_prompt: str = ""


class TemplateBuildRequest(BaseModel):
    scenario_id: UUID
    publish_revision: int
    mode: TemplateMode
    content_hash: str
    master: MasterTemplateContent | None = None
    newbie: NewbieTemplateContent | None = None


class TemplateBuildResponse(BaseModel):
    template_id: UUID
    direct_status: TemplateDirectStatus
    enrichment_status: TemplateEnrichmentStatus
