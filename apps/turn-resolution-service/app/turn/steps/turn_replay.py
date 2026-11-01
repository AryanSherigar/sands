"""Replays a completed turn's stored result for a retried client_action_id.

A TurnLog row holds the narration and media URLs only, so the replay emits
narration, scene image, narration audio and done. Mood, turn_summary, check,
minigame and ending events are not stored and are not replayed; the client
restores that state by refetching the playthrough.
"""

from collections.abc import AsyncIterator

import structlog
from app.db.models.turn_log import TurnLog
from app.turn.steps import response_streamer
from sse_starlette.sse import ServerSentEvent

logger = structlog.get_logger()

EVENT_TURN_REPLAYED = "turn_replayed"


async def replay_events(turn_log: TurnLog) -> AsyncIterator[ServerSentEvent]:
    logger.info(
        EVENT_TURN_REPLAYED,
        playthrough_id=str(turn_log.playthrough_id),
        turn_number=turn_log.turn_number,
    )
    if turn_log.narration_text:
        yield response_streamer.narration_event(turn_log.narration_text)
    if turn_log.image_url:
        yield response_streamer.scene_image_event(turn_log.image_url)
    if turn_log.audio_url:
        yield response_streamer.narration_audio_event(turn_log.audio_url)
    yield response_streamer.done_event(turn_log.turn_id)
