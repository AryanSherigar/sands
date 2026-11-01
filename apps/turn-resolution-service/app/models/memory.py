"""Wire models for the greenfield memory service's POST /v1/retrieve.

Mirrors apps/memory/app/models/retrieve.py. The limits below are that
contract's request limits, kept here as named constants because TRS must cut
its own text to fit before sending.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MAX_RECENT_TEXT_CHARS = 12000
MAX_LAST_UTTERANCE_CHARS = 4000
MAX_ACTION_TEXT_CHARS = 4000
MAX_ID_LIST_LENGTH = 500
MAX_SCENE_ENTITY_IDS = 100
MAX_PARTICIPANT_NAMES = 50
MAX_PARTICIPANT_NAME_CHARS = 100

REASON_RETRIEVAL_FAILED = "retrieval_failed"
REASON_TEMPLATE_MISSING = "template_missing"
REASON_MEMORY_DISABLED = "memory_disabled"

ActionMode = Literal["say", "do", "story", "see"]


class RetrieveRequest(BaseModel):
    model_config = {"extra": "forbid"}

    playthrough_id: UUID
    sequence: int = Field(ge=0)
    action_text: str
    action_mode: ActionMode
    actor_participant_id: UUID
    recent_text: str
    last_actor_utterance: str = ""
    scene_authored_entity_ids: list[UUID] = Field(default_factory=list)
    interlocutor_authored_entity_id: UUID | None = None
    revealed_fact_ids: list[UUID] = Field(default_factory=list)
    active_conditional_fact_ids: list[UUID] = Field(default_factory=list)
    participant_names: dict[UUID, str] = Field(default_factory=dict)
    recent_window_turns: int | None = Field(default=None, ge=0)


class MemoryItem(BaseModel):
    kind: Literal["span", "fact", "commitment", "event"]
    item_id: UUID
    source_kind: str
    authority: Literal["authored", "accepted", "extracted"]
    assertion: Literal["occurred", "stated", "attempted", "believed"] | None
    sequence: int
    speaker: str | None
    text: str
    entity_ids: list[UUID]
    branches: list[str] = Field(default_factory=list)


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
    degraded_reasons: list[str] = Field(default_factory=list)
    embedding_model: str
    skipped_branches: list[str] = Field(default_factory=list)


class MemoryContext(BaseModel):
    """What the narrator prompt gets from memory this turn.

    `response` is None when retrieval failed; `reasons` then holds
    `retrieval_failed` (memory's own degraded reasons are carried otherwise).
    """

    response: RetrieveResponse | None = None
    reasons: list[str] = Field(default_factory=list)
    retrieval_ms: int | None = None

    @property
    def items(self) -> list[MemoryItem]:
        return self.response.items if self.response else []

    @property
    def should_inline_lore_fallback(self) -> bool:
        return any(
            reason in self.reasons
            for reason in (
                REASON_RETRIEVAL_FAILED,
                REASON_TEMPLATE_MISSING,
                REASON_MEMORY_DISABLED,
            )
        )
