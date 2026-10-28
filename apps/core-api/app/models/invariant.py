"""Pydantic request and response schemas for master-mode Rule Invariants."""

import uuid

from app.models.ui_metadata import UiMetadata
from pydantic import BaseModel, ConfigDict, Field


class InvariantCreate(BaseModel):
    """Payload to create a mechanically-enforced world-rule invariant."""

    label: str
    invariant_expression: dict[str, object]
    applies_to: str  # "global" | "player" | an entity_id (validated at service layer)
    narrator_text: str
    metadata: UiMetadata = None


class InvariantUpdate(BaseModel):
    """Payload to update an existing rule invariant."""

    label: str | None = None
    invariant_expression: dict[str, object] | None = None
    applies_to: str | None = None
    narrator_text: str | None = None
    metadata: UiMetadata = None


class InvariantResponse(BaseModel):
    """Response model for a single rule invariant."""

    model_config = ConfigDict(from_attributes=True)

    invariant_id: uuid.UUID
    scenario_id: uuid.UUID
    label: str
    invariant_expression: dict[str, object]
    applies_to: str
    narrator_text: str
    metadata_: dict[str, object] | None = Field(
        default=None, serialization_alias="metadata"
    )


class InvariantListResponse(BaseModel):
    """Response model for listing a scenario's rule invariants."""

    items: list[InvariantResponse]
