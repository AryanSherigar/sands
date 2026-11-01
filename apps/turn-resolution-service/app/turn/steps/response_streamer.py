"""Formats turn pipeline events as Server-Sent Events for the client.

Pure formatting only — this step never calls state_writer or any other step
directly; pipeline.py is the sole sequencer (CLAUDE.md).
"""

import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

from app.config import settings
from app.models.check_event import (
    CheckEventPayload,
    CheckResolvedPayload,
    RuleCheckEventPayload,
    RuleCheckResolvedPayload,
)
from app.models.client_effect import FiredEffect
from app.models.minigame_event import MinigameEventPayload
from app.models.sensory_cue import FiredCue
from app.models.turn_summary import TurnSummaryPayload
from sse_starlette.sse import EventSourceResponse, ServerSentEvent


def narration_event(chunk: str) -> ServerSentEvent:
    """Format one narration chunk as an SSE event."""
    return ServerSentEvent(event="narration", data=chunk)


def mood_event(mood: str) -> ServerSentEvent:
    """Format a mood transition event as an SSE event."""
    return ServerSentEvent(event="mood", data=mood)


def playthrough_ended_event(
    outcome_tag: str, outcome_title: str, outcome_text: str
) -> ServerSentEvent:
    """Format the end-of-playthrough outcome as an SSE event, emitted once,
    before the terminal done event, on the turn that matched an end condition."""
    return ServerSentEvent(
        event="playthrough_ended",
        data=json.dumps(
            {
                "outcome_tag": outcome_tag,
                "outcome_title": outcome_title,
                "outcome_text": outcome_text,
            }
        ),
    )


def turn_summary_event(payload: TurnSummaryPayload) -> ServerSentEvent:
    """Format the master-mode end-of-turn state-delta event as an SSE event,
    emitted after state_writer/end_condition_evaluator, before the terminal
    done event — the frontend defers showing it until that turn's narration
    finishes streaming, regardless of when it arrives."""
    return ServerSentEvent(event="turn_summary", data=payload.model_dump_json())


def minigame_event(payload: MinigameEventPayload) -> ServerSentEvent:
    """Format the triggered minigame's play-time config as an SSE event,
    emitted after turn_summary_event, before playthrough_ended_event/
    done_event. payload never carries win_mutation/lose_mutation/
    tiered_outcomes/timeout_mutation/narrator_instruction_template — those
    stay server-side only (§3.6's "Always" boundary)."""
    return ServerSentEvent(event="minigame", data=payload.model_dump_json())


def check_event(
    payload: CheckEventPayload | RuleCheckEventPayload,
) -> ServerSentEvent:
    """Format a newly-proposed check as an SSE event, emitted after
    turn_summary_event, before playthrough_ended_event/done_event — same
    position as minigame_event. No roll yet; the client shows a roll/decline
    prompt gating the next action."""
    return ServerSentEvent(event="check", data=payload.model_dump_json())


def check_resolved_event(
    payload: CheckResolvedPayload | RuleCheckResolvedPayload,
) -> ServerSentEvent:
    """Format the resolved check outcome as an SSE event, emitted immediately
    after the early roll commit (attempt) or right after accepting a decline
    — before narration even starts, so the client can show the roll
    decoupled from narration latency."""
    return ServerSentEvent(event="check_resolved", data=payload.model_dump_json())


def sensory_cue_event(cue: FiredCue) -> ServerSentEvent:
    """Format one fired cue, emitted after check_resolved and before the first
    narration chunk so the client can cut the ambience before the text arrives.
    Not replayed on turn replay and not relayed to spectators."""
    return ServerSentEvent(event="sensory_cue", data=cue.model_dump_json())


def client_effect_event(effect: FiredEffect) -> ServerSentEvent:
    """An effect the client plays once after the turn commits. Emitted with the
    intake events; not replayed on turn replay and not relayed to spectators."""
    return ServerSentEvent(event="client_effect", data=effect.model_dump_json())


def state_update_event(payload: dict[str, object]) -> ServerSentEvent:
    """Format the visible-state snapshot, emitted after any sensory_cue and
    before the first narration chunk. Not replayed, not relayed to spectators."""
    return ServerSentEvent(event="state_update", data=json.dumps(payload))


def scene_image_event(url: str) -> ServerSentEvent:
    """Format a generated 'see'-action scene image URL as an SSE event,
    emitted once (best-effort — only when generation succeeded) after
    narration finishes streaming, before state persistence."""
    return ServerSentEvent(event="scene_image", data=url)


def narration_audio_event(url: str) -> ServerSentEvent:
    """Format a generated narration audio URL as an SSE event, emitted once
    (best-effort -- only when generation succeeded, and only when the turn
    requested it) after narration finishes streaming, before state
    persistence."""
    return ServerSentEvent(event="narration_audio", data=url)


def quota_notice_event(
    feature: str, code: str, detail: str, reset_at: datetime | None
) -> ServerSentEvent:
    """Format a skipped optional extra (scene image, voice narration) whose
    daily quota is spent, emitted in that extra's slot so the client can say
    why it's missing; the turn itself still completes normally."""
    payload = {
        "feature": feature,
        "code": code,
        "detail": detail,
        "reset_at": reset_at.isoformat() if reset_at else None,
    }
    return ServerSentEvent(event="quota_notice", data=json.dumps(payload))


def input_truncated_event(original_length: int, max_length: int) -> ServerSentEvent:
    """Tell the player their action was cut to the cap; emitted before any
    narration so the notice precedes the turn it applies to."""
    payload = {"original_length": original_length, "max_length": max_length}
    return ServerSentEvent(event="input_truncated", data=json.dumps(payload))


def memory_degraded_event(reasons: list[str]) -> ServerSentEvent:
    """Non-blocking notice that story memory is behind; emitted before done."""
    return ServerSentEvent(
        event="memory_degraded", data=json.dumps({"reasons": reasons})
    )


def done_event(turn_id: uuid.UUID | None = None) -> ServerSentEvent:
    """Format the terminal success event, emitted only once the turn is persisted.
    Carries the stored turn's id so the client can address it (e.g. to flag it)."""
    data = json.dumps({"turn_id": str(turn_id)}) if turn_id else ""
    return ServerSentEvent(event="done", data=data)


def degraded_event(message: str) -> ServerSentEvent:
    """Format a graceful-degradation event, emitted in place of done on failure."""
    return ServerSentEvent(event="degraded", data=message)


async def build_sse_response(
    events: AsyncIterator[ServerSentEvent],
) -> EventSourceResponse:
    """Wrap an already-formatted event stream in an EventSourceResponse.

    Events are forwarded as they arrive — never buffered — per CLAUDE.md's
    SSE streaming rule.
    """
    return EventSourceResponse(events, ping=settings.sse_ping_interval_seconds)
