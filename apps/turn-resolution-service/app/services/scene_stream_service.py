"""Chooses the narrator for a prepared scene exchange."""

from collections.abc import AsyncIterator

from app.services.judgment_scene_service import stream_judgment_message
from app.services.letter_scene_service import stream_letter_message
from app.services.scene_service import (
    PreparedExchange,
    SceneUsage,
    stream_scene_message,
)
from sse_starlette.sse import ServerSentEvent
from strategy_contracts.scene import SceneType


def stream_prepared_message(
    prepared: PreparedExchange, usage: SceneUsage | None = None
) -> AsyncIterator[ServerSentEvent]:
    if prepared.package.scene_type is SceneType.LETTER:
        return stream_letter_message(prepared, usage)
    if prepared.package.scene_type is SceneType.JUDGMENT:
        return stream_judgment_message(prepared, usage)
    return stream_scene_message(prepared, usage)
