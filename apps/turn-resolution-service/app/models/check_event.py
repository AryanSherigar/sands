"""Play-time dice-check SSE payload and resolution-submission shapes.

Mirrors the frontend types in shared/types/check.types.ts (CheckEventPayload,
CheckResolutionPayload, CheckResolvedPayload) — see
docs/specs/master-mode-checks.spec.md. Follows the same server-authoritative
boundary as minigame_event.py: the roll is computed and validated server-side,
never client-supplied.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_ENTRY_TEXT_LENGTH = 16


class CheckEventPayload(BaseModel):
    """Announces a newly-proposed check to the client — no roll yet."""

    check_id: str
    check_type: str
    difficulty_class: int
    reasoning: str | None = None


class CheckResolutionInput(BaseModel):
    """A player's roll/decline submission, as TurnRequestInput.check_resolution."""

    check_id: str
    resolution: Literal["attempt", "decline"]


class CheckResolvedPayload(BaseModel):
    """The resolved outcome, emitted immediately after the early roll commit
    (attempt) or as soon as the decline is accepted — before narration."""

    check_id: str
    check_type: str
    difficulty_class: int
    resolved_roll: int | None
    is_success: bool | None


class CheckReportInput(BaseModel):
    """A player's answer to a rule check (timed prompt), as
    TurnRequestInput.check_report. The server decides lateness and the result;
    the client only says which option it chose, or that its timer ran out."""

    check_id: str
    choice_id: str | None = None
    timed_out: bool = False
    was_hidden: bool = False
    is_untimed: bool = False
    entry_text: str | None = Field(default=None, max_length=MAX_ENTRY_TEXT_LENGTH)

    @field_validator("entry_text")
    @classmethod
    def _entry_text_is_printable(cls, value: str | None) -> str | None:
        if value is not None and not value.isprintable():
            raise ValueError("entry_text must be printable")
        return value


class RuleCheckOption(BaseModel):
    """The public face of one option: results and mutations stay server-side."""

    id: str
    label: str


class RuleCheckVariant(BaseModel):
    """One recall variant as shown to the player; the id encodes the original
    index, and which variant is correct never leaves the server."""

    id: str
    text: str


class RuleCheckEventPayload(BaseModel):
    """Announces an opened rule check to the client (the `check` SSE event for
    kind != dice). Never carries results, mutations or timeout outcomes."""

    check_id: str
    kind: str
    prompt: str
    options: list[RuleCheckOption]
    variants: list[RuleCheckVariant] = []
    window_ms: int
    issued_at: int
    hidden_grace_ms: int = 0
    reopen_count: int = 0
    is_armed: bool = False
    told_label: str | None = None
    wall_label: str | None = None
    wall_minute_of_day: int | None = None
    # Set only on the SSE event, at the moment it is sent: the window is stamped
    # before media generation and the commit, so the client needs the server
    # clock now to measure how much of it is really left.
    server_time_ms: int | None = None


class RuleCheckResolvedPayload(BaseModel):
    """A rule check resolved; the result itself may sit in a hidden state field,
    so only the check id and kind are announced."""

    check_id: str
    kind: str


class RuleCheckArmInput(BaseModel):
    """The client saying the narration that set a rule check up has been read,
    so the server can start the prompt's clock."""

    playthrough_id: uuid.UUID
    participant_id: uuid.UUID
    check_id: str


class RuleCheckArmedPayload(BaseModel):
    """The armed window: `issued_at` is the server-stamped start, and
    `server_time_ms` lets the client measure how much of it is left."""

    check_id: str
    issued_at: int
    window_ms: int
    server_time_ms: int
