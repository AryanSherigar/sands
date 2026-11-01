"""Derived knowledge rows: entities, aliases, facts, supersession, commitments, scene."""

from datetime import datetime
from uuid import UUID

from app.models.common import (
    Assertion,
    Authority,
    CommitmentKind,
    CommitmentStatusValue,
    EntityProvenance,
    ScopeKind,
)
from pydantic import BaseModel


class EntityCreate(BaseModel):
    scope_kind: ScopeKind
    scope_id: UUID
    authored_entity_id: UUID | None = None
    entity_type: str
    canonical_name: str
    provenance: EntityProvenance
    first_seen_seq: int
    is_player: bool = False


class EntityRow(EntityCreate):
    entity_id: UUID


class AliasCreate(BaseModel):
    entity_id: UUID
    scope_kind: ScopeKind
    scope_id: UUID
    alias: str
    alias_normalized: str


class AliasRow(AliasCreate):
    pass


class FactCreate(BaseModel):
    scope_kind: ScopeKind
    scope_id: UUID
    subject_entity_id: UUID
    predicate: str
    object_entity_id: UUID | None = None
    object_literal: str | None = None
    authority: Authority
    assertion: Assertion
    speaker_entity_id: UUID | None = None
    valid_from_seq: int
    authored_fact_id: UUID | None = None
    is_hidden: bool = False
    conditional: bool = False
    supersedes_authored_fact_id: UUID | None = None
    extraction_batch_id: UUID | None = None
    event_id: UUID | None = None


class FactRow(FactCreate):
    fact_id: UUID
    created_at: datetime


class FactSourceCreate(BaseModel):
    fact_id: UUID
    span_id: UUID


class FactSourceRow(FactSourceCreate):
    pass


class SupersessionCreate(BaseModel):
    playthrough_id: UUID
    fact_id: UUID
    at_seq: int
    superseding_fact_id: UUID | None = None
    authority: Authority
    evidence_span_id: UUID | None = None
    extraction_batch_id: UUID | None = None
    event_id: UUID | None = None


class SupersessionRow(SupersessionCreate):
    supersession_id: UUID


class CommitmentCreate(BaseModel):
    playthrough_id: UUID
    kind: CommitmentKind
    owner_entity_id: UUID
    counterparty_entity_id: UUID | None = None
    summary: str
    opened_seq: int
    opening_span_id: UUID
    extraction_batch_id: UUID


class CommitmentRow(CommitmentCreate):
    commitment_id: UUID


class CommitmentStatusCreate(BaseModel):
    commitment_id: UUID
    at_seq: int
    status: CommitmentStatusValue
    evidence_span_id: UUID | None = None
    event_id: UUID | None = None
    extraction_batch_id: UUID | None = None


class CommitmentStatusRow(CommitmentStatusCreate):
    pass


class SceneStateCreate(BaseModel):
    playthrough_id: UUID
    valid_from_seq: int
    location_entity_id: UUID | None = None
    present_entity_ids: list[UUID]
    extraction_batch_id: UUID


class SceneStateRow(SceneStateCreate):
    pass
