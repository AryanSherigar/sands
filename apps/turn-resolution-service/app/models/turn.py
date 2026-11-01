"""Pydantic request/response and internal step-boundary shapes for turn resolution."""

import uuid
from typing import Literal

from app.config import settings
from app.models.check_event import CheckReportInput, CheckResolutionInput
from app.models.fantasy import FantasyActionInput
from app.models.memory import MemoryContext
from app.models.minigame_event import MinigameResultInput
from pydantic import BaseModel, Field, model_validator


class ActionTextLimitResult(BaseModel):
    """Outcome of capping a player's action text."""

    text: str
    original_length: int
    is_truncated: bool


class InputTruncation(BaseModel):
    """Records that a turn's action text was cut, for the client notice."""

    original_length: int
    max_length: int


class TurnRequestInput(BaseModel):
    """Raw input to the turn pipeline."""

    playthrough_id: uuid.UUID
    participant_id: uuid.UUID
    client_action_id: uuid.UUID
    action_text: str = Field(max_length=settings.turn_action_hard_max_chars)
    action_kind: Literal[
        "narrative",
        "minigame_result",
        "check_resolution",
        "check_report",
        "fantasy_action",
    ] = "narrative"
    action_mode: Literal["say", "do", "story", "see"] = "do"
    minigame_result: MinigameResultInput | None = None
    check_resolution: CheckResolutionInput | None = None
    check_report: CheckReportInput | None = None
    voice_output_requested: bool = False
    fantasy_action: FantasyActionInput | None = None

    @model_validator(mode="after")
    def validate_fantasy_action(self) -> "TurnRequestInput":
        if (self.action_kind == "fantasy_action") != (self.fantasy_action is not None):
            raise ValueError("fantasy_action must match action_kind")
        return self


class TurnRequest(TurnRequestInput):
    """Validated turn request, produced by request_receiver."""

    turn_count: int
    input_truncation: InputTruncation | None = None


class LoadedState(BaseModel):
    """Scenario snapshot and playthrough state, produced by state_loader."""

    scenario_id: uuid.UUID
    scenario_snapshot: dict[str, object]
    state: dict[str, object]
    turn_count: int
    narrative_turn_count: int | None = None
    checkpoint: str | None
    is_playtest: bool = False
    memory_publish_revision: int | None = None


class RecentTurn(BaseModel):
    """One committed turn of the recent window, read from TurnLog."""

    turn_number: int
    participant_id: uuid.UUID | None
    action_mode: str
    action_text: str
    narration_text: str


class TurnContext(BaseModel):
    """Everything around the action that the narrator prompt is assembled from."""

    memory: MemoryContext = Field(default_factory=MemoryContext)
    recent_turns: list[RecentTurn] = Field(default_factory=list)
    participant_names: dict[uuid.UUID, str] = Field(default_factory=dict)
