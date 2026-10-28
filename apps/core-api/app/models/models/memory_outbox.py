"""Payload shapes stored on memory_outbox rows and delivered to the memory service."""

from uuid import UUID

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


class RegisterParticipant(BaseModel):
    """One playthrough participant and the name extraction should attribute actions to."""

    participant_id: UUID
    display_name: str


class RegisterPayload(BaseModel):
    """Payload of a register_playthrough outbox row."""

    scenario_id: UUID
    publish_revision: int = Field(ge=0)
    player_entity: RegisterPlayerEntity | None = None
    setup_facts: list[RegisterSetupFact] = Field(default_factory=list)
    participants: list[RegisterParticipant] = Field(default_factory=list)
    tracked_fields: list[str] = Field(default_factory=list)


class ParticipantsPayload(BaseModel):
    """Payload of a participants outbox row: every participant known at that point."""

    participants: list[RegisterParticipant]
