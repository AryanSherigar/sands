"""Wire models for the greenfield memory service's POST /v1/templates.

Mirrors apps/memory/app/models/templates.py. Only fields memory accepts are
declared here: no valid_from and no narrator_instruction.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

TemplateMode = Literal["master", "newbie"]
TemplateDirectStatus = Literal["building", "ready", "failed"]
TemplateEnrichmentStatus = Literal[
    "pending", "running", "ready", "failed", "not_needed"
]


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
    when_active: dict[str, Any] | None = None
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


class TemplateBuildOutcome(BaseModel):
    """What the client reports back: memory's body plus whether the row is new
    (201) or an idempotent replay (200)."""

    response: TemplateBuildResponse
    was_created: bool
