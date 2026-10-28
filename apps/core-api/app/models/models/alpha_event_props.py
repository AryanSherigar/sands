"""Closed registry of alpha client events and their allowed props.

This registry is the privacy control for client events: every prop is a number,
a boolean, a fixed choice or a short code from a restricted alphabet, so no
free text, name, email or nested object can be stored.
"""

import uuid
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SAFE_CODE_MAX_LENGTH = 120
SAFE_CODE_PATTERN = r"^[A-Za-z0-9_./:\-]{1,120}$"
MAX_DURATION_MS = 86_400_000
MAX_COUNT = 100_000
MAX_TURN_NUMBER = 10_000
MIN_TENSION_RATING = 1
MAX_TENSION_RATING = 5

SafeCode = Annotated[str, StringConstraints(pattern=SAFE_CODE_PATTERN)]
DurationMs = Annotated[int, Field(ge=0, le=MAX_DURATION_MS)]
Count = Annotated[int, Field(ge=0, le=MAX_COUNT)]
TurnNumber = Annotated[int, Field(ge=0, le=MAX_TURN_NUMBER)]


class AlphaEventName(StrEnum):
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    DEVICE_INFO = "device_info"
    TURN_PERCEIVED_LATENCY = "turn_perceived_latency"
    STREAM_STALL = "stream_stall"
    STREAM_RECONNECT = "stream_reconnect"
    AUDIO_BLOCKED = "audio_blocked"
    UI_USED = "ui_used"
    CLIENT_ERROR = "client_error"
    TURN_RETRY = "turn_retry"
    TENSION_RATING = "tension_rating"


class _Props(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionProps(_Props):
    visible_ms: DurationMs = 0
    hidden_ms: DurationMs = 0
    turns_in_session: Count | None = None
    sfx_played_count: Count = 0
    audio_blocked_count: Count = 0


class DeviceInfoProps(_Props):
    device_class: Literal["phone", "tablet", "desktop"]
    viewport_bucket: SafeCode
    browser_family: SafeCode
    is_reduce_effects_on: bool
    is_audio_muted: bool


class TurnPerceivedLatencyProps(_Props):
    turn_number: TurnNumber
    first_token_ms: DurationMs | None = None
    total_ms: DurationMs


class StreamProblemProps(_Props):
    turn_number: TurnNumber
    stalled_ms: DurationMs


class AudioBlockedProps(_Props):
    reason: Literal["autoplay_policy", "muted", "error"]


class UiUsedProps(_Props):
    feature: Literal["rule_sheet", "hud", "map", "phone"]
    count: Annotated[int, Field(ge=1, le=MAX_COUNT)]


class ClientErrorProps(_Props):
    kind: SafeCode
    route: SafeCode
    message_code: SafeCode


class TurnRetryProps(_Props):
    kind: Literal["after_error", "check_report_resend"]
    turn_number: TurnNumber
    client_action_id: uuid.UUID


class TensionRatingProps(_Props):
    turn_number: TurnNumber
    rating: Annotated[int, Field(ge=MIN_TENSION_RATING, le=MAX_TENSION_RATING)]


EVENT_PROPS_MODELS: dict[AlphaEventName, type[_Props]] = {
    AlphaEventName.SESSION_START: SessionProps,
    AlphaEventName.SESSION_END: SessionProps,
    AlphaEventName.DEVICE_INFO: DeviceInfoProps,
    AlphaEventName.TURN_PERCEIVED_LATENCY: TurnPerceivedLatencyProps,
    AlphaEventName.STREAM_STALL: StreamProblemProps,
    AlphaEventName.STREAM_RECONNECT: StreamProblemProps,
    AlphaEventName.AUDIO_BLOCKED: AudioBlockedProps,
    AlphaEventName.UI_USED: UiUsedProps,
    AlphaEventName.CLIENT_ERROR: ClientErrorProps,
    AlphaEventName.TURN_RETRY: TurnRetryProps,
    AlphaEventName.TENSION_RATING: TensionRatingProps,
}
