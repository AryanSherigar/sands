"""Narrates the judgment scene: the hall's opening, the court's replies and the sentence.

The simulation owns the scene and decides its outcome. This service only writes prose; the
verdict and nuance are the player's own structured choice and never come from model text.
"""

import json
from collections.abc import AsyncIterator

import structlog
from app.exceptions.base import BaseAppException
from app.integrations import simulation_client
from app.models.scene import SceneMessageKind
from app.services import judgment_prompt, scene_service
from app.services.scene_service import NARRATION_FAILURES, PreparedExchange, SceneUsage
from sse_starlette.sse import ServerSentEvent
from strategy_contracts.scene import SceneStatus, SubmissionStatus
from strategy_contracts.scene_exchange import (
    SceneAction,
    SceneDecision,
    SceneExchangeSubmission,
)

logger = structlog.get_logger()

JUDGMENT_DEGRADED_MESSAGE = "The court could not be heard. Try again."
JUDGMENT_DEGRADED_ENDED_MESSAGE = (
    "The court could not be convened and the case has been set aside."
)
PRONOUNCED_FALLBACK_TEXT = (
    "The sentence is pronounced, and the hall receives it in silence."
)
DEFAULT_DECREE_TEXT = "I pronounce my judgment."


async def _degraded(
    prepared: PreparedExchange, error: BaseAppException, is_countable: bool
) -> ServerSentEvent:
    return await scene_service.degraded_event(
        prepared,
        error,
        JUDGMENT_DEGRADED_MESSAGE,
        JUDGMENT_DEGRADED_ENDED_MESSAGE,
        is_countable,
    )


def _open_done_event(prepared: PreparedExchange) -> ServerSentEvent:
    body = {
        "sequence": max(1, len(prepared.transcript)),
        "exchanges_remaining": prepared.package.exchange_cap
        - max(1, len(prepared.transcript)),
        "scene_status": SceneStatus.OPENED.value,
    }
    return ServerSentEvent(event="done", data=json.dumps(body))


async def _open(
    prepared: PreparedExchange, usage: SceneUsage
) -> AsyncIterator[ServerSentEvent]:
    if prepared.transcript:
        yield ServerSentEvent(
            event="narration", data=prepared.transcript[0].leader_text
        )
        yield _open_done_event(prepared)
        return
    package = prepared.package
    system = judgment_prompt.build_judgment_system_instruction(package)
    contents = judgment_prompt.build_judgment_open_contents(package)
    tableau: list[str] = []
    try:
        async for event in scene_service.stream_narration(
            system, contents, usage, tableau
        ):
            yield event
        await simulation_client.store_opening_text(
            prepared.scene_id, prepared.user_id, "".join(tableau).strip()
        )
    except BaseAppException as error:
        yield await _degraded(prepared, error, is_countable=True)
        return
    yield _open_done_event(prepared)


async def _submit_and_report(
    prepared: PreparedExchange,
    leader_text: str,
    player_text: str,
    decision: SceneDecision,
) -> AsyncIterator[ServerSentEvent]:
    try:
        result = await simulation_client.submit_exchange(
            prepared.scene_id,
            prepared.user_id,
            SceneExchangeSubmission(
                sequence=prepared.sequence,
                player_text=player_text,
                leader_text=leader_text,
                decision=decision,
            ),
        )
    except BaseAppException as error:
        yield await _degraded(prepared, error, is_countable=True)
        return
    if result.status is SubmissionStatus.REJECTED:
        logger.warning(scene_service.EVENT_SCENE_STREAM_DEGRADED, reason=result.reason)
        yield ServerSentEvent(event="degraded", data=JUDGMENT_DEGRADED_MESSAGE)
        return
    for event in scene_service.result_events(prepared, result):
        yield event


async def _speak(
    prepared: PreparedExchange, usage: SceneUsage
) -> AsyncIterator[ServerSentEvent]:
    package = prepared.package
    system = judgment_prompt.build_judgment_system_instruction(package)
    contents = judgment_prompt.build_judgment_reply_contents(
        package, prepared.transcript, prepared.player_text
    )
    reply: list[str] = []
    try:
        async for event in scene_service.stream_narration(
            system, contents, usage, reply
        ):
            yield event
    except BaseAppException as error:
        yield await _degraded(prepared, error, is_countable=True)
        return
    decision = SceneDecision(action=SceneAction.CONTINUE_TALK)
    async for event in _submit_and_report(
        prepared, "".join(reply).strip(), prepared.player_text, decision
    ):
        yield event


async def _stream_closing(
    prepared: PreparedExchange, usage: SceneUsage, closing: list[str]
) -> AsyncIterator[ServerSentEvent]:
    package = prepared.package
    system = judgment_prompt.build_judgment_system_instruction(package)
    contents = judgment_prompt.build_judgment_closing_contents(
        package,
        prepared.transcript,
        prepared.verdict or "",
        prepared.nuance,
        prepared.player_text,
    )
    try:
        async for event in scene_service.stream_narration(
            system, contents, usage, closing
        ):
            yield event
    except NARRATION_FAILURES:
        logger.warning(scene_service.EVENT_SCENE_STREAM_DEGRADED, kind="closing")


async def _pronounce(
    prepared: PreparedExchange, usage: SceneUsage
) -> AsyncIterator[ServerSentEvent]:
    closing: list[str] = []
    async for event in _stream_closing(prepared, usage, closing):
        yield event
    leader_text = "".join(closing).strip()
    if not leader_text:
        leader_text = PRONOUNCED_FALLBACK_TEXT
        yield ServerSentEvent(event="narration", data=leader_text)
    decision = SceneDecision(
        action=SceneAction.CHOOSE_OPTION,
        option_id=prepared.verdict,
        nuance_id=prepared.nuance,
    )
    player_text = prepared.player_text or DEFAULT_DECREE_TEXT
    async for event in _submit_and_report(prepared, leader_text, player_text, decision):
        yield event


HANDLERS = {
    SceneMessageKind.OPEN: _open,
    SceneMessageKind.MESSAGE: _speak,
    SceneMessageKind.PRONOUNCE: _pronounce,
}


async def stream_judgment_message(
    prepared: PreparedExchange, usage: SceneUsage | None = None
) -> AsyncIterator[ServerSentEvent]:
    """Stream one judgment action (open, speak or pronounce) and log its token usage."""
    tally = usage if usage is not None else SceneUsage()
    try:
        async for event in HANDLERS[prepared.kind](prepared, tally):
            yield event
    finally:
        scene_service.log_usage(prepared, tally)
