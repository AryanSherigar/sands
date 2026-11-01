"""Wire contract for POST /v1/retrieve and retrieval-related types."""

from typing import Literal
from uuid import UUID

from app.models.common import Authority
from pydantic import BaseModel, Field, field_validator

RetrievalBranch = Literal["exact", "bm25", "vector", "graph"]
DegradedReason = Literal["extraction_failed", "indexing_lag", "template_missing"]

MAX_ACTION_TEXT_CHARS = 4000
MAX_RECENT_TEXT_CHARS = 12000
MAX_LAST_UTTERANCE_CHARS = 4000
MAX_ID_LIST_LENGTH = 500
MAX_SCENE_ENTITY_IDS = 100
MIN_RECALL_BUDGET_TOKENS = 200
MAX_RECALL_BUDGET_TOKENS = 4000
MAX_PARTICIPANT_NAMES = 50
MAX_PARTICIPANT_NAME_CHARS = 100


class RetrieveRequest(BaseModel):
    model_config = {"extra": "forbid"}

    playthrough_id: UUID
    sequence: int = Field(ge=0)
    action_text: str = Field(max_length=MAX_ACTION_TEXT_CHARS)
    action_mode: Literal["say", "do", "story", "see"]
    actor_participant_id: UUID
    recent_text: str = Field(max_length=MAX_RECENT_TEXT_CHARS)
    last_actor_utterance: str = Field(default="", max_length=MAX_LAST_UTTERANCE_CHARS)
    scene_authored_entity_ids: list[UUID] = Field(
        default_factory=list, max_length=MAX_SCENE_ENTITY_IDS
    )
    interlocutor_authored_entity_id: UUID | None = None
    revealed_fact_ids: list[UUID] = Field(
        default_factory=list, max_length=MAX_ID_LIST_LENGTH
    )
    active_conditional_fact_ids: list[UUID] = Field(
        default_factory=list, max_length=MAX_ID_LIST_LENGTH
    )
    participant_names: dict[UUID, str] = Field(default_factory=dict)
    recent_window_turns: int | None = Field(default=None, ge=0)
    recall_budget_tokens: int | None = Field(
        default=None,
        ge=MIN_RECALL_BUDGET_TOKENS,
        le=MAX_RECALL_BUDGET_TOKENS,
    )

    @field_validator("participant_names")
    @classmethod
    def validate_participant_names(cls, value: dict[UUID, str]) -> dict[UUID, str]:
        if len(value) > MAX_PARTICIPANT_NAMES:
            raise ValueError(
                f"participant_names exceeds maximum of {MAX_PARTICIPANT_NAMES}"
            )
        for name in value.values():
            if len(name) > MAX_PARTICIPANT_NAME_CHARS:
                raise ValueError(
                    f"participant name exceeds maximum length of "
                    f"{MAX_PARTICIPANT_NAME_CHARS}"
                )
        return value


class MemoryItem(BaseModel):
    kind: Literal["span", "fact", "commitment", "event"]
    item_id: UUID
    source_kind: str
    authority: Authority
    assertion: Literal["occurred", "stated", "attempted", "believed"] | None
    sequence: int
    speaker: str | None
    text: str
    entity_ids: list[UUID]
    branches: list[RetrievalBranch]


class ActiveEntity(BaseModel):
    entity_id: UUID
    authored_entity_id: UUID | None
    name: str
    provenance: Literal["authored", "extracted"]
    brief: str | None = None


class SceneAtSequence(BaseModel):
    valid_from_seq: int
    location_entity_id: UUID | None
    present_entity_ids: list[UUID]


class Watermarks(BaseModel):
    ingested_seq: int
    indexed_seq: int
    extracted_seq: int
    latest_seq_seen: int


class RetrieveResponse(BaseModel):
    items: list[MemoryItem]
    active_entities: list[ActiveEntity]
    scene: SceneAtSequence | None
    watermarks: Watermarks
    degraded_reasons: list[DegradedReason]
    embedding_model: str
    skipped_branches: list[RetrievalBranch] = Field(default_factory=list)


class ExtractionContext(BaseModel):
    lines: list[str]
    items: list[MemoryItem] = Field(default_factory=list)
    entity_ids: list[UUID]
    token_count: int
    truncated: bool
