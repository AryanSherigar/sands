"""Narrates one exchange of a strategy-mode scene.

The simulation service owns the scene, its transcript and its outcome; this
service fetches the package, voices the leader, and posts the exchange and a
bounded decision back. It keeps no scene state of its own.
"""

import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import structlog
from app.config import settings
from app.exceptions.base import BaseAppException
from app.exceptions.scene_exceptions import SceneKindMismatchError, SceneNotOpenError
from app.exceptions.turn_exceptions import LlmContentBlockedError, LlmUnavailableError
from app.integrations import openai_compatible_client, simulation_client
from app.models.scene import SceneMessageKind, SceneMessageRequest
from app.models.token_usage import TokenUsage
from app.services import scene_prompt
from app.services.scene_decision import parse_decision
from sse_starlette.sse import ServerSentEvent
from strategy_contracts.scene import (
    ScenePackage,
    SceneStatus,
    SceneType,
    SubmissionStatus,
)
from strategy_contracts.scene_exchange import (
    InternalScenePackage,
    SceneAction,
    SceneDecision,
    SceneExchangeResult,
    SceneExchangeSubmission,
    SceneExchangeView,
)

logger = structlog.get_logger()

EVENT_SCENE_STREAM_OPENED = "scene_stream_opened"
EVENT_SCENE_STREAM_DEGRADED = "scene_stream_degraded"
EVENT_SCENE_MODEL_USAGE = "scene_model_usage"
FINAL_SCENE_STATUSES = (SceneStatus.RESOLVED, SceneStatus.DEFAULTED)
DEGRADED_MESSAGE = "The scene could not continue. Your message was not recorded."
DEGRADED_ENDED_MESSAGE = (
    "The scene could not continue and has ended. The talks were counted as refused."
)
EVENT_SCENE_FAILURE_REPORT_FAILED = "scene_failure_report_failed"
NARRATION_FAILURES = (LlmUnavailableError, LlmContentBlockedError)


@dataclass
class SceneUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0

    def add(self, sink: TokenUsage) -> None:
        self.prompt_tokens += sink.prompt_tokens
        self.completion_tokens += sink.completion_tokens
        self.cached_tokens += sink.cached_tokens


@dataclass(frozen=True)
class PreparedExchange:
    scene_id: uuid.UUID
    user_id: uuid.UUID
    package: ScenePackage
    transcript: list[SceneExchangeView]
    player_text: str
    kind: SceneMessageKind = SceneMessageKind.MESSAGE
    current_draft: str = ""

    @property
    def sequence(self) -> int:
        return len(self.transcript) + 1


def _require_matching_kind(
    fetched: InternalScenePackage, kind: SceneMessageKind
) -> None:
    """Letters take open, scribe and seal; every other scene takes plain messages."""
    if fetched.package.scene_type is not SceneType.LETTER:
        if kind is not SceneMessageKind.MESSAGE:
            raise SceneKindMismatchError()
        return
    is_unopened = not fetched.transcript
    if kind is SceneMessageKind.MESSAGE or (
        is_unopened and kind is not SceneMessageKind.OPEN
    ):
        raise SceneKindMismatchError()


async def prepare_exchange(
    scene_id: uuid.UUID, user_id: uuid.UUID, request: SceneMessageRequest
) -> PreparedExchange:
    """Fetch the package before the stream opens, so a closed scene is a real HTTP error."""
    fetched = await simulation_client.fetch_scene_package(scene_id, user_id)
    if fetched.status in FINAL_SCENE_STATUSES or fetched.exchanges_remaining <= 0:
        raise SceneNotOpenError()
    scene_prompt.profile_for(fetched.package.scene_type)
    _require_matching_kind(fetched, request.kind)
    return PreparedExchange(
        scene_id=scene_id,
        user_id=user_id,
        package=fetched.package,
        transcript=fetched.transcript,
        player_text=request.text,
        kind=request.kind,
        current_draft=request.current_draft,
    )


async def collect_chunks(
    system: str,
    contents: list,
    max_output_tokens: int,
    usage: SceneUsage,
) -> AsyncIterator[str]:
    sink = TokenUsage()
    try:
        async for chunk in openai_compatible_client.stream_chat(
            system_instruction=system,
            contents=contents,
            timeout_seconds=settings.scene_model_timeout_seconds,
            max_output_tokens=max_output_tokens
            + settings.scene_reasoning_headroom_tokens,
            usage_sink=sink,
        ):
            yield chunk
    finally:
        usage.add(sink)


async def _decide(
    prepared: PreparedExchange, system: str, leader_text: str, usage: SceneUsage
) -> SceneDecision:
    contents = scene_prompt.build_decision_contents(
        prepared.transcript,
        prepared.player_text,
        leader_text,
        prepared.package.exchange_cap,
        prepared.package.scene_type,
    )
    try:
        text = "".join(
            [
                chunk
                async for chunk in collect_chunks(
                    system,
                    contents,
                    settings.scene_decision_max_output_tokens,
                    usage,
                )
            ]
        )
    except (LlmUnavailableError, LlmContentBlockedError):
        return SceneDecision(action=SceneAction.CONTINUE_TALK)
    return parse_decision(text)


def result_events(
    prepared: PreparedExchange, result: SceneExchangeResult
) -> list[ServerSentEvent]:
    events: list[ServerSentEvent] = []
    if result.pending_proposal is not None:
        events.append(
            ServerSentEvent(
                event="proposal", data=result.pending_proposal.model_dump_json()
            )
        )
    if result.scene_status in FINAL_SCENE_STATUSES:
        events.append(
            ServerSentEvent(
                event="scene_ended",
                data=json.dumps({"scene_status": result.scene_status.value}),
            )
        )
    done = {
        "sequence": prepared.sequence,
        "exchanges_remaining": result.exchanges_remaining,
        "scene_status": result.scene_status.value,
    }
    return [*events, ServerSentEvent(event="done", data=json.dumps(done))]


async def report_failure(prepared: PreparedExchange) -> bool:
    """Report a narration failure; True when the simulation ended the scene by default."""
    try:
        result = await simulation_client.report_scene_failure(
            prepared.scene_id, prepared.user_id
        )
    except BaseAppException as error:
        logger.warning(
            EVENT_SCENE_FAILURE_REPORT_FAILED, error_type=type(error).__name__
        )
        return False
    return result.scene_status in FINAL_SCENE_STATUSES


def log_usage(prepared: PreparedExchange, usage: SceneUsage) -> None:
    logger.info(
        EVENT_SCENE_MODEL_USAGE,
        scene_type=prepared.package.scene_type.value,
        sequence=prepared.sequence,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cached_tokens=usage.cached_tokens,
    )


async def stream_scene_message(
    prepared: PreparedExchange, usage: SceneUsage | None = None
) -> AsyncIterator[ServerSentEvent]:
    """Stream the leader's reply, then record the exchange and report its result."""
    tally = usage if usage is not None else SceneUsage()
    try:
        async for event in _narrate(prepared, tally):
            yield event
    finally:
        log_usage(prepared, tally)


async def _narrate(
    prepared: PreparedExchange, usage: SceneUsage
) -> AsyncIterator[ServerSentEvent]:
    logger.info(EVENT_SCENE_STREAM_OPENED, sequence=prepared.sequence)
    system = scene_prompt.build_system_instruction(prepared.package)
    contents = scene_prompt.build_reply_contents(
        prepared.transcript,
        prepared.player_text,
        prepared.package.exchange_cap,
        prepared.package.scene_type,
    )
    reply: list[str] = []
    try:
        async for chunk in collect_chunks(
            system, contents, settings.scene_reply_max_output_tokens, usage
        ):
            reply.append(chunk)
            yield ServerSentEvent(event="narration", data=chunk)
        leader_text = "".join(reply).strip()
        if not leader_text:
            raise LlmUnavailableError()
        decision = await _decide(prepared, system, leader_text, usage)
        result = await simulation_client.submit_exchange(
            prepared.scene_id,
            prepared.user_id,
            SceneExchangeSubmission(
                sequence=prepared.sequence,
                player_text=prepared.player_text,
                leader_text=leader_text,
                decision=decision,
            ),
        )
    except BaseAppException as error:
        logger.warning(EVENT_SCENE_STREAM_DEGRADED, error_type=type(error).__name__)
        has_ended = isinstance(error, NARRATION_FAILURES) and await report_failure(
            prepared
        )
        yield ServerSentEvent(
            event="degraded",
            data=DEGRADED_ENDED_MESSAGE if has_ended else DEGRADED_MESSAGE,
        )
        return
    if result.status is SubmissionStatus.REJECTED:
        logger.warning(EVENT_SCENE_STREAM_DEGRADED, reason=result.reason)
        yield ServerSentEvent(event="degraded", data=DEGRADED_MESSAGE)
        return
    for event in result_events(prepared, result):
        yield event
