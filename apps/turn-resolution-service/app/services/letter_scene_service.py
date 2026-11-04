"""Narrates the letter scene: the sender's letter, the player's scribe, and the sealed reply.

The simulation owns the scene and decides its outcome; this service only writes
prose and proposes one of the offered replies.
"""

import json
from collections.abc import AsyncIterator

import structlog
from app.config import settings
from app.exceptions.base import BaseAppException
from app.integrations import simulation_client
from app.models.scene import SceneMessageKind
from app.services import letter_prompt, scene_prompt, scene_service
from app.services.scene_decision import parse_decision
from app.services.scene_service import (
    NARRATION_FAILURES,
    PreparedExchange,
    SceneUsage,
)
from sse_starlette.sse import ServerSentEvent
from strategy_contracts.scene import SceneStatus, SubmissionStatus
from strategy_contracts.scene_exchange import (
    SceneAction,
    SceneDecision,
    SceneExchangeSubmission,
)

logger = structlog.get_logger()

LETTER_DEGRADED_MESSAGE = "The letter could not be written. Try again."
LETTER_DEGRADED_ENDED_MESSAGE = (
    "The letter could not be completed and has been set aside."
)
LETTER_STORED_STATUS = SceneStatus.OPENED


def _done_event(prepared: PreparedExchange, remaining: int) -> ServerSentEvent:
    body = {
        "sequence": prepared.sequence,
        "exchanges_remaining": remaining,
        "scene_status": LETTER_STORED_STATUS.value,
    }
    return ServerSentEvent(event="done", data=json.dumps(body))


async def _degrade(
    prepared: PreparedExchange, error: BaseAppException, is_countable: bool
) -> ServerSentEvent:
    return await scene_service.degraded_event(
        prepared,
        error,
        LETTER_DEGRADED_MESSAGE,
        LETTER_DEGRADED_ENDED_MESSAGE,
        is_countable,
    )


async def _open(
    prepared: PreparedExchange, usage: SceneUsage
) -> AsyncIterator[ServerSentEvent]:
    package = prepared.package
    if prepared.transcript:
        stored = prepared.transcript[0].leader_text
        yield ServerSentEvent(event="narration", data=stored)
        yield _done_event(
            prepared, len(prepared.transcript) and package.exchange_cap - 1
        )
        return
    system = scene_prompt.build_system_instruction(package)
    contents = letter_prompt.build_letter_open_contents(package)
    letter: list[str] = []
    try:
        async for event in scene_service.stream_narration(
            system, contents, usage, letter
        ):
            yield event
        await simulation_client.store_letter_body(
            prepared.scene_id, prepared.user_id, "".join(letter).strip()
        )
    except BaseAppException as error:
        yield await _degrade(prepared, error, is_countable=True)
        return
    yield _done_event(prepared, package.exchange_cap - 1)


async def _scribe(
    prepared: PreparedExchange, usage: SceneUsage
) -> AsyncIterator[ServerSentEvent]:
    package = prepared.package
    system = letter_prompt.build_scribe_system_instruction(package)
    contents = letter_prompt.build_letter_scribe_contents(
        package, prepared.transcript, prepared.player_text, prepared.current_draft
    )
    try:
        async for event in scene_service.stream_narration(system, contents, usage, []):
            yield event
    except BaseAppException as error:
        yield await _degrade(prepared, error, is_countable=False)
        return
    yield _done_event(prepared, package.exchange_cap - len(prepared.transcript))


async def _decide(
    prepared: PreparedExchange, system: str, acknowledgement: str, usage: SceneUsage
) -> SceneDecision:
    contents = letter_prompt.build_letter_decision_contents(
        prepared.package, prepared.transcript, prepared.player_text, acknowledgement
    )
    try:
        text = "".join(
            [
                chunk
                async for chunk in scene_service.collect_chunks(
                    system, contents, settings.scene_decision_max_output_tokens, usage
                )
            ]
        )
    except NARRATION_FAILURES:
        return SceneDecision(action=SceneAction.CONTINUE_TALK)
    return parse_decision(text)


async def _seal(
    prepared: PreparedExchange, usage: SceneUsage
) -> AsyncIterator[ServerSentEvent]:
    package = prepared.package
    system = scene_prompt.build_system_instruction(package)
    contents = letter_prompt.build_letter_ack_contents(
        package, prepared.transcript, prepared.player_text
    )
    acknowledgement: list[str] = []
    try:
        async for event in scene_service.stream_narration(
            system, contents, usage, acknowledgement
        ):
            yield event
        leader_text = "".join(acknowledgement).strip()
        decision = await _decide(prepared, system, leader_text, usage)
        result = await simulation_client.submit_exchange(
            prepared.scene_id,
            prepared.user_id,
            SceneExchangeSubmission(
                sequence=prepared.sequence,
                player_text=prepared.player_text,
                leader_text=leader_text,
                decision=decision,
                tone_grade=decision.tone_grade,
            ),
        )
    except BaseAppException as error:
        yield await _degrade(prepared, error, is_countable=True)
        return
    if result.status is SubmissionStatus.REJECTED:
        logger.warning(scene_service.EVENT_SCENE_STREAM_DEGRADED, reason=result.reason)
        yield ServerSentEvent(event="degraded", data=LETTER_DEGRADED_MESSAGE)
        return
    for event in scene_service.result_events(prepared, result, decision.tone_grade):
        yield event


HANDLERS = {
    SceneMessageKind.OPEN: _open,
    SceneMessageKind.SCRIBE: _scribe,
    SceneMessageKind.SEAL: _seal,
}


async def stream_letter_message(
    prepared: PreparedExchange, usage: SceneUsage | None = None
) -> AsyncIterator[ServerSentEvent]:
    """Stream one letter action (open, scribe or seal) and log its token usage."""
    tally = usage if usage is not None else SceneUsage()
    try:
        async for event in HANDLERS[prepared.kind](prepared, tally):
            yield event
    finally:
        scene_service.log_usage(prepared, tally)
