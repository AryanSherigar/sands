"""Pydantic request and response schemas for Scenarios."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from app.models.content_tags import validate_content_tags
from app.models.lore_document import LoreDocument
from app.models.world_data_documents import validate_world_data_documents
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

try:
    from strategy_contracts.scenario import StrategyScenario
except (ImportError, ModuleNotFoundError):
    StrategyScenario = None  # type: ignore[assignment,misc]

MAX_MOOD_TAGS = 12
MAX_MOOD_TAG_LENGTH = 40
MoodTag = Annotated[str, StringConstraints(max_length=MAX_MOOD_TAG_LENGTH)]
VISIBILITY_PATTERN = "^(public|private)$"
PLAYER_MODE_PATTERN = "^(written|player_created)$"
SCENARIO_MODE_PATTERN = "^(newbie|master|strategy)$"
STRATEGY_MODE = "strategy"

# NOTE: Reserved for Maps (docs/specs/master-mode-maps.spec.md): system-provisioned
# and system-maintained at playthrough creation/turn time, never authored by
# a creator directly, regardless of whether the scenario has any maps yet —
# reserving them unconditionally avoids an order-of-operations bug where a
# creator defines the field before adding a map.
RESERVED_STATE_SCHEMA_KEYS: frozenset[str] = frozenset(
    {"current_location_id", "discovered_location_ids"}
)


def _reject_reserved_state_keys(
    state_schema: dict[str, object] | None,
) -> dict[str, object] | None:
    if state_schema is None:
        return state_schema
    conflicts = RESERVED_STATE_SCHEMA_KEYS & state_schema.keys()
    if conflicts:
        raise ValueError(
            f"state_schema cannot define reserved key(s): {sorted(conflicts)}"
        )
    return state_schema


def _validate_strategy_document(
    document: dict[str, object],
) -> dict[str, object]:
    if not document:
        return document
    if StrategyScenario is not None:
        return StrategyScenario.model_validate(document).model_dump(mode="json")
    return document


def _validate_mode_document_pair(mode: str, document: dict[str, object]) -> None:
    if mode == STRATEGY_MODE and not document:
        raise ValueError("strategy_document is required for strategy mode")
    if mode != STRATEGY_MODE and document:
        raise ValueError("strategy_document is only valid for strategy mode")


class ScenarioCreate(BaseModel):
    """Payload to create a new draft scenario."""

    title: str = Field(..., max_length=255)
    mode: str = Field(default="newbie", pattern=SCENARIO_MODE_PATTERN)
    complexity_tier: str = Field(
        default="newbie", pattern="^(newbie|intermediate|master)$"
    )
    visibility: str = Field(default="private", pattern=VISIBILITY_PATTERN)
    mood_tags: list[MoodTag] = Field(default_factory=list, max_length=MAX_MOOD_TAGS)
    narrator_persona_document: LoreDocument | None = None
    player_mode: str = Field(default="written", pattern=PLAYER_MODE_PATTERN)
    logline: str | None = Field(default=None, max_length=150)
    player_count_support: str = Field(
        default="solo", pattern="^(solo|multiplayer|both)$"
    )
    estimated_playtime: str | None = Field(default=None, max_length=50)
    cover_image_url: str | None = Field(default=None, max_length=1024)
    content_tag: str | None = Field(default=None, max_length=100)
    content_tags: list[str] = Field(default_factory=list)
    genre_tags: list[str] = Field(default_factory=list)
    narrator_persona: str | None = None
    world_data: dict[str, object] = Field(default_factory=dict)
    strategy_document: dict[str, object] = Field(default_factory=dict)
    setup_schema: list[object] = Field(default_factory=list)
    state_schema: dict[str, object] = Field(default_factory=dict)
    end_conditions: list[object] = Field(default_factory=list)
    checkpoints: list[object] = Field(default_factory=list)
    rules: dict[str, object] = Field(default_factory=dict)
    opening_scene: str | None = None
    narration_font: str | None = Field(default=None, max_length=50)
    narrator_voice_name: str | None = Field(default=None, max_length=100)
    action_chips: list[str] = Field(default_factory=list)
    setup_archetypes: list[object] = Field(default_factory=list)

    _validate_state_schema = field_validator("state_schema")(
        _reject_reserved_state_keys
    )
    _validate_content_tags = field_validator("content_tags")(validate_content_tags)
    _validate_world_data = field_validator("world_data")(validate_world_data_documents)
    _validate_strategy_document = field_validator("strategy_document")(
        _validate_strategy_document
    )

    @model_validator(mode="after")
    def validate_strategy_mode(self) -> "ScenarioCreate":
        _validate_mode_document_pair(self.mode, self.strategy_document)
        return self


class ScenarioUpdate(BaseModel):
    """Payload to update scenario fields."""

    title: str | None = Field(default=None, max_length=255)
    mode: str | None = Field(default=None, pattern=SCENARIO_MODE_PATTERN)
    status: str | None = Field(default=None, pattern="^(draft|archived)$")
    logline: str | None = Field(default=None, max_length=150)
    complexity_tier: str | None = Field(
        default=None, pattern="^(newbie|intermediate|master)$"
    )
    player_count_support: str | None = Field(
        default=None, pattern="^(solo|multiplayer|both)$"
    )
    estimated_playtime: str | None = Field(default=None, max_length=50)
    cover_image_url: str | None = Field(default=None, max_length=1024)
    content_tag: str | None = Field(default=None, max_length=100)
    content_tags: list[str] | None = None
    genre_tags: list[str] | None = None
    narrator_persona: str | None = None
    world_data: dict[str, object] | None = None
    strategy_document: dict[str, object] | None = None
    setup_schema: list[object] | None = None
    state_schema: dict[str, object] | None = None
    end_conditions: list[object] | None = None
    checkpoints: list[object] | None = None
    rules: dict[str, object] | None = None
    opening_scene: str | None = None
    narration_font: str | None = Field(default=None, max_length=50)
    narrator_voice_name: str | None = Field(default=None, max_length=100)
    action_chips: list[str] | None = None
    setup_archetypes: list[object] | None = None
    visibility: str | None = Field(default=None, pattern=VISIBILITY_PATTERN)
    mood_tags: list[MoodTag] | None = Field(default=None, max_length=MAX_MOOD_TAGS)
    narrator_persona_document: LoreDocument | None = None
    player_mode: str | None = Field(default=None, pattern=PLAYER_MODE_PATTERN)
    guide_seen_features: list[str] | None = None
    expected_content_edited_at: datetime | None = None

    _validate_state_schema = field_validator("state_schema")(
        _reject_reserved_state_keys
    )
    _validate_content_tags = field_validator("content_tags")(validate_content_tags)
    _validate_world_data = field_validator("world_data")(validate_world_data_documents)
    _validate_strategy_document = field_validator("strategy_document")(
        _validate_strategy_document
    )


class ScenarioResponse(BaseModel):
    """Detailed response model for a single scenario."""

    model_config = ConfigDict(from_attributes=True)

    scenario_id: uuid.UUID
    creator_id: uuid.UUID
    visibility: str = "public"
    creator_display_name: str | None = None
    is_bookmarked: bool = False
    can_review: bool = False
    creator_avatar_url: str | None = None
    creator_bio: str | None = None
    creator_other_scenarios_count: int = 0
    has_maps: bool = False
    has_minigames: bool = False
    title: str
    logline: str | None = None
    mode: str
    status: str
    genre_tags: list[str] = Field(default_factory=list)
    complexity_tier: str
    player_count_support: str
    estimated_playtime: str | None = None
    cover_image_url: str | None = None
    content_tag: str | None = None
    content_tags: list[str] = Field(default_factory=list)
    publish_error: str | None = None
    published_at: datetime | None = None
    play_count: int = 0
    rating_avg: Decimal = Field(default=Decimal("0.00"))
    narrator_persona: str | None = None
    narrator_persona_document: LoreDocument | None = None
    mood_tags: list[str] = Field(default_factory=list)
    player_mode: str = "written"
    guide_seen_features: list[str] = Field(default_factory=list)
    world_data: dict[str, object] = Field(default_factory=dict)
    strategy_document: dict[str, object] = Field(default_factory=dict)
    setup_schema: list[object] = Field(default_factory=list)
    state_schema: dict[str, object] = Field(default_factory=dict)
    end_conditions: list[object] = Field(default_factory=list)
    checkpoints: list[object] = Field(default_factory=list)
    rules: dict[str, object] = Field(default_factory=dict)
    opening_scene: str | None = None
    narration_font: str | None = None
    narrator_voice_name: str | None = None
    action_chips: list[str] = Field(default_factory=list)
    setup_archetypes: list[object] = Field(default_factory=list)
    enabled_tools: list[str] = Field(default_factory=list)
    current_version: int = 1
    content_edited_at: datetime
    created_at: datetime
    updated_at: datetime


class ScenarioSummaryResponse(BaseModel):
    """Summary model used for discovery feed and scenario listing cards."""

    model_config = ConfigDict(from_attributes=True)

    scenario_id: uuid.UUID
    creator_id: uuid.UUID
    title: str
    logline: str | None = None
    mode: str
    status: str
    genre_tags: list[str] = Field(default_factory=list)
    complexity_tier: str
    player_count_support: str
    estimated_playtime: str | None = None
    cover_image_url: str | None = None
    content_tag: str | None = None
    playtime_bucket: str | None = None
    is_mature: bool = False
    creator_display_name: str | None = None
    is_bookmarked: bool = False
    play_count: int = 0
    rating_avg: Decimal = Field(default=Decimal("0.00"))
    created_at: datetime
    updated_at: datetime


class ScenarioListResponse(BaseModel):
    """Paginated response for scenario listing."""

    items: list[ScenarioSummaryResponse]
    next_cursor: str | None = None
    total_count: int


class MyScenarioSummary(ScenarioSummaryResponse):
    """Creator-only list row: the summary plus Studio-list fields."""

    review_count: int = 0
    has_unpublished_changes: bool = False
    publish_error: str | None = None
    content_edited_at: datetime


class ScenarioStatusCounts(BaseModel):
    """Per-tab scenario counts for the creator's Studio list."""

    all: int = 0
    drafts: int = 0
    published: int = 0
    archived: int = 0


class MyScenarioListResponse(BaseModel):
    """Paginated Studio list with per-tab counts."""

    items: list[MyScenarioSummary]
    next_cursor: str | None = None
    total_count: int
    status_counts: ScenarioStatusCounts
