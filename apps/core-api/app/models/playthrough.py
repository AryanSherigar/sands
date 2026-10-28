"""Pydantic request and response schemas for Playthroughs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from strategy_contracts.scenario import PlayerRulerCustomization


class PlaythroughCreate(BaseModel):
    """Payload to start a new playthrough of a published scenario. Unknown
    fields are refused so a playtest-only field such as state_overrides can
    never be silently dropped here."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: uuid.UUID
    setup_values: dict[str, object] = Field(default_factory=dict)
    faction_id: str | None = None
    player_ruler: PlayerRulerCustomization | None = None


class PlaytestCreate(BaseModel):
    """Optional payload to start a playtest; setup_values is validated against
    the scenario's setup_schema exactly as a real playthrough's would be.

    state_overrides presets tracked values (dotted path to value) so a creator
    can reach an ending or rule on the next turn; it exists only here."""

    setup_values: dict[str, object] = Field(default_factory=dict)
    state_overrides: dict[str, object] = Field(default_factory=dict)


class PlaythroughCharacterUpdate(BaseModel):
    """Payload to edit character setup values on an active playthrough.

    Merged into the existing state.setup dict rather than replacing it, so
    callers only need to send the fields they are editing.
    """

    setup_values: dict[str, object] = Field(default_factory=dict)


class ParticipantSummary(BaseModel):
    """Lightweight participant info for frontend turn-order derivation."""

    model_config = ConfigDict(from_attributes=True)

    participant_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    turn_order_position: int


class RuleSheetItem(BaseModel):
    """One revealed rule on the clipboard: never carries an unrevealed rule."""

    key: str
    number: int
    text: str
    status: str
    source_style: str


class PlaythroughResponse(BaseModel):
    """Response model for a created or fetched playthrough."""

    model_config = ConfigDict(from_attributes=True)

    playthrough_id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_title: str
    created_by: uuid.UUID
    state: dict[str, object]
    checkpoint: str | None = None
    turn_count: int
    status: str
    # NOTE: Set once a master playthrough has ended. The client refetches this
    # response after every turn, so it must carry the ending the stream sent.
    ended_outcome_tag: str | None = None
    ended_outcome_title: str | None = None
    ended_outcome_text: str | None = None
    is_playtest: bool = False
    scenario_version: int
    scenario_snapshot: dict[str, object]
    # NOTE: The server clock when this response was built, so a reloaded client
    # derives the time left on a timed prompt from the server's issued_at.
    server_time_ms: int
    # NOTE: The clipboard, derived from the pinned sheet rules and the hidden
    # `rule_status`; [] unless the `rule_sheet` tool is on.
    rule_sheet: list[RuleSheetItem] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    # NOTE: The requesting user's own participant_id — needed to submit turns
    # (POST /v1/turn requires it) and absent from the RFC's original schema.
    participant_id: uuid.UUID
    participants: list[ParticipantSummary] = Field(default_factory=list)
    # NOTE: Master-mode-only; [] for newbie or a master playthrough with no
    # scenario_conditions currently true.
    active_conditions: list[str] = Field(default_factory=list)
