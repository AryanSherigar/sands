"""Job and index rows: memory_extraction_batch, memory_embedding, memory_embedding_model, memory_embedding_failure."""

from datetime import datetime
from uuid import UUID

from app.models.common import EmbeddingTargetKind, ExtractionBatchStatus, ScopeKind
from pgvector import Vector
from pydantic import BaseModel, field_validator


class ExtractionBatchCreate(BaseModel):
    scope_kind: ScopeKind
    scope_id: UUID
    from_seq: int
    to_seq: int
    status: ExtractionBatchStatus
    model: str
    prompt_version: str
    input_hash: str


class ExtractionBatchRow(ExtractionBatchCreate):
    batch_id: UUID
    attempt_count: int
    lease_expires_at: datetime | None
    raw_output: dict[str, object] | None
    validated_plan: dict[str, object] | None
    error: str | None
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime
    updated_at: datetime


class EmbeddingCreate(BaseModel):
    """Repositories bind `embedding` as `pgvector.Vector(embedding)`; a bare list binds as an array."""

    target_kind: EmbeddingTargetKind
    target_id: UUID
    scope_kind: ScopeKind
    scope_id: UUID
    model: str
    model_version: str
    dim: int
    embedding: list[float]
    content_hash: str

    @field_validator("embedding", mode="before")
    @classmethod
    def convert_pgvector(cls, value: object) -> object:
        if isinstance(value, Vector):
            return value.to_list()
        return value


class EmbeddingRow(EmbeddingCreate):
    created_at: datetime


class EmbeddingModelCreate(BaseModel):
    model: str
    model_version: str
    dim: int
    is_active: bool


class EmbeddingModelRow(EmbeddingModelCreate):
    pass


class EmbeddingFailureRow(BaseModel):
    target_kind: EmbeddingTargetKind
    target_id: UUID
    model: str
    model_version: str
    attempt_count: int
    last_error: str | None
    updated_at: datetime


class SpanClaimRow(BaseModel):
    span_id: UUID
    scope_kind: ScopeKind
    scope_id: UUID
    text: str


class FactClaimRow(BaseModel):
    fact_id: UUID
    scope_kind: ScopeKind
    scope_id: UUID
    subject_name: str
    predicate: str
    object_text: str | None
