"""Pydantic request and response schemas for master-mode active Conditions
(ScenarioCondition), including Effect C direct state mutation."""

import uuid
from collections.abc import Sequence

from app.models.client_effect import validate_condition_metadata
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_MUTATIONS_PER_LIST = 16

# NOTE: Single definition of the cue vocabulary; the frontend mirrors it in
# shared/constants/sensory-cues.ts and tests/test_frontend_constants_drift.py
# fails when the two differ.
SENSORY_CUE_IDS = (
    "phone_ring",
    "heavy_knock",
    "light_buzz",
    "distant_footsteps",
    "sudden_silence",
    "radio_static",
    "elevator_chime",
    "lamp_click",
    "keyboard_typing",
    "paper_rustle",
)
_SENSORY_CUE_PATTERN = "^(" + "|".join(SENSORY_CUE_IDS) + ")$"
MAX_SILENCE_DURATION_MS = 5000
DEFAULT_SILENCE_DURATION_MS = 800


class StateMutation(BaseModel):
    """Effect C: a direct state mutation applied pre-turn by TRS when this
    condition's expression is true (master-mode-turn-pipeline.spec.md)."""

    path: str
    op: str = Field(..., pattern="^(set|increment|decrement)$")
    value: object


def effective_mutations(
    legacy_single: dict[str, object] | None,
    listed: Sequence[dict[str, object]] | None,
) -> list[dict[str, object]]:
    """Read rule used everywhere: the list wins, else the legacy single."""
    if listed:
        return list(listed)
    return [legacy_single] if legacy_single else []


def _reject_both_mutation_shapes(
    single: StateMutation | None, listed: Sequence[StateMutation] | None
) -> None:
    if single is not None and listed:
        raise ValueError("Provide either the single mutation or the list, not both")


class ConditionCreate(BaseModel):
    """Payload to create an active condition on a master-mode scenario."""

    label: str = Field(..., max_length=255)
    condition_expression: dict[str, object] = Field(default_factory=dict)
    narrator_instruction: str
    metadata: dict[str, object] = Field(default_factory=dict)
    state_mutation: StateMutation | None = None
    state_mutations: list[StateMutation] = Field(
        default_factory=list, max_length=MAX_MUTATIONS_PER_LIST
    )
    is_one_shot: bool = False
    sensory_cue: str | None = Field(default=None, pattern=_SENSORY_CUE_PATTERN)
    cut_ambient: bool = True
    silence_duration_ms: int = Field(
        default=DEFAULT_SILENCE_DURATION_MS, ge=0, le=MAX_SILENCE_DURATION_MS
    )

    @field_validator("metadata")
    @classmethod
    def _validate_metadata_effects(
        cls, value: dict[str, object] | None
    ) -> dict[str, object] | None:
        return validate_condition_metadata(value) if value else value

    @model_validator(mode="after")
    def _validate_mutation_shapes(self) -> "ConditionCreate":
        _reject_both_mutation_shapes(self.state_mutation, self.state_mutations)
        return self


class ConditionUpdate(BaseModel):
    """Payload to update an existing active condition."""

    label: str | None = Field(default=None, max_length=255)
    condition_expression: dict[str, object] | None = None
    narrator_instruction: str | None = None
    metadata: dict[str, object] | None = None
    state_mutation: StateMutation | None = None
    state_mutations: list[StateMutation] | None = Field(
        default=None, max_length=MAX_MUTATIONS_PER_LIST
    )
    is_one_shot: bool | None = None
    sensory_cue: str | None = Field(default=None, pattern=_SENSORY_CUE_PATTERN)
    cut_ambient: bool | None = None
    silence_duration_ms: int | None = Field(
        default=None, ge=0, le=MAX_SILENCE_DURATION_MS
    )

    @field_validator("metadata")
    @classmethod
    def _validate_metadata_effects(
        cls, value: dict[str, object] | None
    ) -> dict[str, object] | None:
        return validate_condition_metadata(value) if value else value

    @model_validator(mode="after")
    def _validate_mutation_shapes(self) -> "ConditionUpdate":
        _reject_both_mutation_shapes(self.state_mutation, self.state_mutations)
        return self


class ConditionResponse(BaseModel):
    """Response model for a single active condition."""

    model_config = ConfigDict(from_attributes=True)

    condition_id: uuid.UUID
    scenario_id: uuid.UUID
    label: str
    condition_expression: dict[str, object] = Field(default_factory=dict)
    condition_version: str = "1.0"
    narrator_instruction: str
    # NOTE: Field name matches the ORM attribute (metadata_, mapped to the DB
    # column "metadata") so from_attributes validation reads it directly;
    # serialization_alias renames it back to "metadata" in the JSON response.
    metadata_: dict[str, object] = Field(
        default_factory=dict, serialization_alias="metadata"
    )
    state_mutation: dict[str, object] | None = None
    state_mutations: list[StateMutation] = Field(default_factory=list)
    is_one_shot: bool = False
    sensory_cue: str | None = None
    cut_ambient: bool = True
    silence_duration_ms: int = DEFAULT_SILENCE_DURATION_MS

    @model_validator(mode="after")
    def _expose_both_mutation_shapes(self) -> "ConditionResponse":
        """The list is canonical; `state_mutation` is the deprecated first
        element."""
        listed = [m.model_dump(mode="json") for m in self.state_mutations]
        effective = effective_mutations(self.state_mutation, listed)
        self.state_mutations = [StateMutation(**m) for m in effective]
        self.state_mutation = effective[0] if effective else None
        return self


class ConditionListResponse(BaseModel):
    """Response model for listing a scenario's active conditions."""

    items: list[ConditionResponse]
