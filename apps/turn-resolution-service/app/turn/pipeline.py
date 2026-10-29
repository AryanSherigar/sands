"""Turn resolution pipeline.

The only file that knows step order — steps in app/turn/steps/ never call
each other directly (CLAUDE.md). Newbie mode: request_receiver, state_loader,
context_retrieval (after reading the recent window from TurnLog), ai_orchestrator, state_writer, response_streamer.
state_writer commits the TurnLog (with its accepted_delta, built here by
accepted_delta_builder) and the memory_outbox delivery row in one transaction;
memory_delivery then tries to deliver it, best effort, before the done event.
Master mode additionally runs, between state_loader and
context_retrieval: minigame_result_resolver (only when the incoming request's
action_kind is "minigame_result" — resolves the pending minigame's outcome
into a state mutation + narrator instruction and clears _pending_minigame,
see docs/specs/master-mode-minigames.spec.md §2), then condition_evaluator
(active conditions + Effect C, applied before the AI narrates — see
docs/specs/master-mode-turn-pipeline.spec.md), carries the AI's validated
tool-call mutations + tool-call log through to state_writer, and runs
end_condition_evaluator immediately after state_writer (see docs/specs/master-mode-end-conditions.spec.md). For scenarios with ≥1
map, also runs map_state_sync right before state_writer, folding any
current_location_id change's discovery update into the same persisted write
(see docs/specs/master-mode-maps.spec.md). Immediately after map_state_sync
(same slot, still before state_writer), runs minigame_trigger_evaluator: for
a solo playthrough with no minigame already pending, evaluates
scenario_minigames in priority order against the final working_state and, on
the first match, stamps the play-time payload into
working_state["_pending_minigame"]. When a fresh trigger was just stamped this
turn, end_condition_evaluator is skipped entirely (minigame wins over an
end condition matching the same turn) and a minigame SSE event is yielded
after turn_summary_event, before playthrough_ended_event/done_event (see
docs/specs/master-mode-minigames.spec.md §2).

After the narration loop completes and before state_writer, if the incoming
request's action_mode is "see", scene_image_generator generates a scene
image (grounded in the current location entity from scenario_snapshot in
master mode, and the prior scene image generated for that same location in
this playthrough, for visual consistency — newbie mode falls back to
narration text alone). On success, a scene_image SSE event is yielded and
the image URL/location/prompt are persisted onto the turn's TurnLog row via
state_writer; on any failure this step returns None and the turn proceeds
exactly as if action_mode were not "see" (a missing image never degrades a
turn).

Immediately after the scene_image step (same slot, still before
state_writer), if the incoming request's voice_output_requested flag is
set, narration_audio_generator synthesizes this turn's narration as speech
via Gemini TTS, using the raw speaker-tag-annotated narration text
(ai_orchestrator's "narration_raw" events, accumulated separately from the
client-facing "narration" chunks). Generation is gated on that per-turn
flag rather than run unconditionally, so a player who hasn't opted into
voice output never incurs TTS cost. On success, a narration_audio SSE event
is yielded and the audio URL is persisted onto the turn's TurnLog row via
state_writer; on any failure (or when the flag isn't set) this step
contributes nothing and the turn proceeds exactly as before this feature
existed.

Before any of that, run_turn looks up the request's client_action_id: a retry
of a turn that already committed is replayed from its TurnLog row by
turn_replay, without the gating checks, the quota reservation or the narrator.

A narrative action over the size cap is truncated by request_receiver; the
turn then opens its stream with an input_truncated event
(docs/specs/turn-input-limit.spec.md).

Quotas (docs/specs/rate-limiting.spec.md): the turn's own daily quota is
reserved right after state_loader, before the SSE response exists, so an
exhausted quota is a real HTTP 429; it is refunded if narration fails. The
scene image and narration audio steps each reserve their own quota first and,
when it is spent, are skipped with a quota_notice event in their slot.
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import structlog
from app.config import settings
from app.db.connection import SessionFactory
from app.db.models.participant import Participant
from app.db.models.turn_log import TurnLog
from app.exceptions.base import BaseAppException
from app.exceptions.fantasy_exceptions import FantasyActionError
from app.exceptions.rate_limit_exceptions import RateLimitExceededError
from app.exceptions.turn_exceptions import (
    NarrationGenerationError,
    OptimisticLockError,
    StateWriteError,
)
from app.models.auth import CurrentUser
from app.models.check_event import (
    CheckEventPayload,
    CheckResolvedPayload,
    RuleCheckEventPayload,
    RuleCheckResolvedPayload,
)
from app.models.client_effect import FiredEffect
from app.models.minigame_event import MinigameEventPayload
from app.models.sensory_cue import FiredCue
from app.models.tool_call import MasterModeTurnResult, ProposedCheck
from app.models.turn import LoadedState, TurnContext, TurnRequest, TurnRequestInput
from app.models.turn_metrics import (
    CHECK_RESULT_FAILED,
    CHECK_RESULT_PASSED,
    CHECK_RESULT_TIMEOUT,
    CheckOutcome,
)
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.repositories.turn_metrics_repo import TurnMetricsRepo
from app.services.input_limit_event_recorder import get_input_limit_event_recorder
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService
from app.session import notification_manager, spectator_manager
from app.turn import accepted_delta_builder, speaker_voice_pool
from app.turn.fantasy_rules import protects_transition
from app.turn.recent_turns import to_recent_turn
from app.turn.steps import (
    ai_orchestrator,
    check_result_resolver,
    condition_evaluator,
    context_retrieval,
    end_condition_evaluator,
    escalation_applier,
    fantasy_action_resolver,
    map_state_sync,
    memory_degraded,
    memory_delivery,
    minigame_result_resolver,
    minigame_trigger_evaluator,
    movement_resolver,
    narration_audio_generator,
    request_receiver,
    response_streamer,
    rule_check_resolver,
    rule_check_trigger_evaluator,
    scene_image_generator,
    state_loader,
    state_update_builder,
    state_validator,
    state_writer,
    turn_replay,
    turn_summary_builder,
)
from app.turn.steps.end_condition_evaluator import MatchedOutcome
from app.turn.steps.minigame_trigger_evaluator import MatchedMinigameTrigger
from app.turn.steps.state_writer import (
    MemoryCommit,
    NarrationAudioResult,
    SceneImageResult,
)
from app.turn.tools import is_enabled
from app.turn.turn_metrics_collector import (
    STEP_REQUEST_RECEIVER,
    STEP_STATE_LOADER,
    IntakeMetrics,
    TurnMetricsCollector,
)
from app.turn.turn_order import expected_participant
from app.turn.turn_quota import ExtraReservation, TurnQuota
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

logger = structlog.get_logger()

STATE_UPDATE_TOOLS = ("status_hud", "rule_sheet")
EVENT_SSE_STREAM_OPENED = "sse_stream_opened"
EVENT_SSE_STREAM_CLOSED = "sse_stream_closed"
EVENT_SSE_STREAM_ERROR = "sse_stream_error"
EVENT_PLAYTHROUGH_ENDING_WRITE_FAILED = "playthrough_ending_write_failed"
EVENT_TURN_REPLAY_COUNT_FAILED = "turn_replay_count_failed"
EVENT_INPUT_TRUNCATED = "input_truncated"
CHECK_KIND_DICE = "dice"
CHECK_KIND_MINIGAME = "minigame"
MINIGAME_OUTCOME_RESULTS = {
    "win": CHECK_RESULT_PASSED,
    "lose": CHECK_RESULT_FAILED,
    "timeout": CHECK_RESULT_TIMEOUT,
}

_DEGRADED_WRITE_MESSAGE = (
    "Your turn couldn't be saved. Please try submitting your action again."
)
_DEGRADED_REJECTED_MESSAGE = (
    "That answer couldn't be applied. Please try submitting it again."
)
_DEGRADED_CONCURRENCY_MESSAGE = "Another turn was processed while yours was generating. Please submit your action again."


async def run_turn(
    turn_input: TurnRequestInput,
    session_factory: SessionFactory,
    current_user: CurrentUser,
    quota_service: QuotaService | None = None,
) -> EventSourceResponse:
    """Validate, generate narration, persist, and stream a single turn."""
    metrics = TurnMetricsCollector(is_enabled=settings.is_alpha_mode)
    async with session_factory() as session:
        completed_turn = await _find_replay(turn_input, session, current_user)
        if completed_turn is None:
            turn_request, loaded_state = await _receive_and_load(
                turn_input,
                PlaythroughRepo(session),
                ParticipantRepo(session),
                current_user,
                metrics,
            )
    if completed_turn is not None:
        return await response_streamer.build_sse_response(
            turn_replay.replay_events(completed_turn)
        )
    if turn_request.action_kind == "fantasy_action":
        _resolve_fantasy_intake(turn_request, loaded_state)
    turn_quota = TurnQuota(quota_service, current_user.user_id)
    await turn_quota.reserve_turn()
    await _record_input_truncation(turn_request, current_user)
    deps = _TurnDeps(session_factory, turn_quota, metrics)
    events = _run_turn_events(turn_request, loaded_state, deps)
    return await response_streamer.build_sse_response(events)


async def _find_replay(
    turn_input: TurnRequestInput, session: AsyncSession, current_user: CurrentUser
) -> TurnLog | None:
    await state_loader.assert_alpha_scenario(
        turn_input.playthrough_id, PlaythroughRepo(session)
    )
    completed_turn = await request_receiver.find_completed_turn(
        turn_input, TurnLogRepo(session), ParticipantRepo(session), current_user
    )
    if completed_turn is not None:
        session.expunge(completed_turn)
        await _count_replay(session, completed_turn.turn_id)
    return completed_turn


async def _receive_and_load(
    turn_input: TurnRequestInput,
    playthrough_repo: PlaythroughRepo,
    participant_repo: ParticipantRepo,
    current_user: CurrentUser,
    metrics: TurnMetricsCollector,
) -> tuple[TurnRequest, LoadedState]:
    with metrics.time_step(STEP_REQUEST_RECEIVER):
        turn_request = await request_receiver.receive_request(
            turn_input, playthrough_repo, participant_repo, current_user
        )
    with metrics.time_step(STEP_STATE_LOADER):
        loaded_state = await state_loader.load_state(
            turn_request.playthrough_id, playthrough_repo
        )
    return turn_request, loaded_state


async def _record_input_truncation(
    turn_request: TurnRequest, current_user: CurrentUser
) -> None:
    truncation = turn_request.input_truncation
    if truncation is None:
        return
    logger.info(
        EVENT_INPUT_TRUNCATED,
        playthrough_id=str(turn_request.playthrough_id),
        original_length=truncation.original_length,
        max_length=truncation.max_length,
    )
    await get_input_limit_event_recorder().record_truncated(
        current_user.user_id, truncation
    )


async def _count_replay(session: AsyncSession, turn_id: uuid.UUID) -> None:
    """Count a replayed client_action_id on the turn's metrics row. A replay
    never creates a row, and a failure here never blocks the replay."""
    if not settings.is_alpha_mode:
        return
    try:
        await TurnMetricsRepo(session).increment_replay_count(turn_id)
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        logger.warning(EVENT_TURN_REPLAY_COUNT_FAILED, turn_id=str(turn_id))


def _with_emit_time(
    payload: CheckEventPayload | RuleCheckEventPayload,
) -> CheckEventPayload | RuleCheckEventPayload:
    if isinstance(payload, RuleCheckEventPayload):
        return payload.model_copy(
            update={"server_time_ms": rule_check_trigger_evaluator.current_time_ms()}
        )
    return payload


def _has_state_update(loaded_state: LoadedState) -> bool:
    snapshot = loaded_state.scenario_snapshot
    return any(is_enabled(snapshot, tool) for tool in STATE_UPDATE_TOOLS)


def _format_ai_event(
    event_type: str, data: str, chunks: list[str], raw_chunks: list[str]
) -> ServerSentEvent | None:
    """Format AI stream event and accumulate narration chunks.

    "narration_raw" (the speaker-tag-annotated text behind each "narration"
    chunk, see ai_orchestrator.py) is accumulated into raw_chunks for the
    narration-audio step below but never becomes an SSE event -- returning
    None here is what makes it structurally impossible for raw
    [NARRATOR]/[NPC: ...] tag markup to leak onto the wire, even if the
    tag-stripping itself has a bug.
    """
    if event_type == "mood":
        return response_streamer.mood_event(data)
    if event_type == "narration":
        chunks.append(data)
        return response_streamer.narration_event(data)
    if event_type == "narration_raw":
        raw_chunks.append(data)
    return None


async def _load_turn_context(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    session_factory: SessionFactory,
) -> TurnContext:
    async with session_factory() as session:
        turn_logs = await TurnLogRepo(session).list_recent(
            turn_request.playthrough_id, settings.recent_window_turns
        )
        participant_names = await ParticipantRepo(session).map_display_names(
            turn_request.playthrough_id
        )
        recent_turns = [to_recent_turn(turn_log) for turn_log in turn_logs]
    memory = await context_retrieval.retrieve_context(
        turn_request, loaded_state, recent_turns, participant_names
    )
    return TurnContext(
        memory=memory, recent_turns=recent_turns, participant_names=participant_names
    )


@dataclass
class _PostGeneration:
    """What the master-mode checks after narration hand to the commit and the
    tail events. Everything is empty for a newbie turn."""

    working_state: dict[str, object] | None = None
    tool_calls: list[dict[str, object]] | None = None
    matched_trigger: MatchedMinigameTrigger | None = None
    proposed_check_payload: CheckEventPayload | RuleCheckEventPayload | None = None
    mutated_paths: set[str] = field(default_factory=set)


@dataclass
class _Media:
    """The optional scene image and narration audio of a turn, with the SSE
    events announcing them."""

    scene_image: SceneImageResult | None
    narration_audio: NarrationAudioResult | None
    events: list[ServerSentEvent]


async def _narration_events(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    context: TurnContext,
    active_instructions: list[str],
    result_sink: MasterModeTurnResult,
    chunks: list[str],
    raw_chunks: list[str],
) -> AsyncIterator[ServerSentEvent]:
    """Stream the narrator's events, collecting its text into the given lists.
    Raises NarrationGenerationError when narration fails."""
    async for event_type, data in ai_orchestrator.generate_narration(
        turn_request, loaded_state, context, active_instructions, result_sink
    ):
        sse_event = _format_ai_event(event_type, data, chunks, raw_chunks)
        if event_type != "narration_raw":
            await spectator_manager.publish(
                turn_request.playthrough_id, event_type, data
            )
        if sse_event:
            yield sse_event


async def _post_generation(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    result_sink: MasterModeTurnResult,
    participant_count: int,
    is_master_mode: bool,
) -> _PostGeneration:
    if not is_master_mode:
        return _PostGeneration()
    (
        working_state,
        tool_calls,
        matched_trigger,
        proposed_check_payload,
        mutated_paths,
    ) = await _evaluate_master_mode_post_generation(
        turn_request, loaded_state, result_sink, participant_count
    )
    return _PostGeneration(
        working_state=working_state,
        tool_calls=tool_calls,
        matched_trigger=matched_trigger,
        proposed_check_payload=proposed_check_payload,
        mutated_paths=mutated_paths,
    )


async def _generate_media(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    working_state: dict[str, object] | None,
    chunks: list[str],
    raw_chunks: list[str],
    session_factory: SessionFactory,
    turn_quota: TurnQuota,
    authored_image_url: str | None = None,
) -> _Media:
    if authored_image_url:
        scene_image, scene_image_event = await _authored_scene_image(
            turn_request, authored_image_url
        )
    else:
        scene_image, scene_image_event = await _maybe_generate_scene_image(
            turn_request,
            loaded_state,
            working_state,
            chunks,
            session_factory,
            turn_quota,
        )
    narration_audio, narration_audio_event = await _maybe_generate_narration_audio(
        turn_request, loaded_state, raw_chunks, turn_quota
    )
    announced = (scene_image_event, narration_audio_event)
    return _Media(
        scene_image=scene_image,
        narration_audio=narration_audio,
        events=[event for event in announced if event is not None],
    )


async def _persist_turn(
    write_arguments: tuple[object, ...],
    write_options: dict[str, object],
    playthrough_id: str,
) -> tuple[dict[str, object] | None, ServerSentEvent | None]:
    """Commit the turn. On a failed write returns no state and the degraded
    event that takes the place of `done`."""
    try:
        updated_state = await state_writer.write_turn(*write_arguments, **write_options)
    except OptimisticLockError:
        logger.warning(
            EVENT_SSE_STREAM_CLOSED,
            playthrough_id=playthrough_id,
            outcome="degraded",
            reason="optimistic_lock_failed",
        )
        return None, response_streamer.degraded_event(_DEGRADED_CONCURRENCY_MESSAGE)
    except StateWriteError:
        logger.warning(
            EVENT_SSE_STREAM_CLOSED, playthrough_id=playthrough_id, outcome="degraded"
        )
        return None, response_streamer.degraded_event(_DEGRADED_WRITE_MESSAGE)
    return updated_state, None


async def _post_write_events(
    scope: "_TurnScope", outcome: "_TurnOutcome"
) -> AsyncIterator[ServerSentEvent]:
    matched_outcome = await _ending_for_turn(scope, outcome)
    await _after_write(
        scope.turn_request,
        scope.loaded_state,
        scope.participants,
        outcome.is_registered_with_memory,
    )
    for event in _completion_events(scope, outcome, matched_outcome):
        yield event
    degraded_event = await _memory_degraded_event(
        scope.deps.session_factory,
        outcome.is_registered_with_memory,
        scope.turn_request.playthrough_id,
        scope.loaded_state.turn_count + 1,
        scope.context.memory.reasons,
    )
    if degraded_event is not None:
        yield degraded_event
    logger.info(
        EVENT_SSE_STREAM_CLOSED,
        playthrough_id=str(scope.turn_request.playthrough_id),
        outcome="done",
    )
    yield response_streamer.done_event(scope.turn_id)


async def _ending_for_turn(
    scope: "_TurnScope", outcome: "_TurnOutcome"
) -> MatchedOutcome | None:
    post = outcome.post_generation
    matched_outcome = None
    if (
        scope.is_master_mode
        and not post.matched_trigger
        and not post.proposed_check_payload
    ):
        matched_outcome = await _evaluate_and_finalize_ending(
            scope.turn_request,
            scope.loaded_state,
            outcome.updated_state,
            scope.deps.session_factory,
            outcome.is_registered_with_memory,
        )
    return matched_outcome


def _completion_events(
    scope: "_TurnScope", outcome: "_TurnOutcome", matched_outcome: MatchedOutcome | None
) -> list[ServerSentEvent]:
    events = []
    post = outcome.post_generation
    if scope.is_master_mode:
        events.append(
            _build_turn_summary_event(
                scope.loaded_state, outcome.updated_state, post.tool_calls or []
            )
        )
    if post.matched_trigger:
        events.append(
            response_streamer.minigame_event(
                MinigameEventPayload(**post.matched_trigger.payload)
            )
        )
    if post.proposed_check_payload:
        events.append(
            response_streamer.check_event(_with_emit_time(post.proposed_check_payload))
        )
    if matched_outcome:
        events.append(
            response_streamer.playthrough_ended_event(
                matched_outcome.outcome_tag,
                matched_outcome.outcome_title,
                matched_outcome.outcome_text,
            )
        )
    return events


@dataclass(frozen=True)
class _TurnDeps:
    session_factory: SessionFactory
    turn_quota: TurnQuota
    metrics: TurnMetricsCollector


@dataclass
class _Narration:
    """The narrator's text as collected while streaming, and whether it failed."""

    chunks: list[str] = field(default_factory=list)
    raw_chunks: list[str] = field(default_factory=list)
    has_failed: bool = False


@dataclass
class _TurnScope:
    """Everything the phases of one turn share once intake and context are ready."""

    turn_request: TurnRequest
    loaded_state: LoadedState
    intake: "MasterModeIntake"
    context: TurnContext
    result_sink: MasterModeTurnResult
    participants: list[Participant]
    is_master_mode: bool
    deps: _TurnDeps
    narration: _Narration = field(default_factory=_Narration)
    turn_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class _TurnOutcome:
    """What `_finish_turn` hands back once the turn is committed. `updated_state`
    stays None when the commit failed and a degraded event was yielded."""

    post_generation: _PostGeneration = field(default_factory=_PostGeneration)
    is_registered_with_memory: bool = False
    updated_state: dict[str, object] | None = None


async def _intake_for_turn(
    is_master_mode: bool,
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    playthrough_repo: PlaythroughRepo,
) -> "MasterModeIntake":
    if not is_master_mode:
        return MasterModeIntake.without_intake(loaded_state)
    return await _prepare_master_mode_turn(turn_request, loaded_state, playthrough_repo)


async def _build_turn_scope(
    turn_request: TurnRequest,
    intake: "MasterModeIntake",
    participants: list[Participant],
    is_master_mode: bool,
    deps: _TurnDeps,
) -> _TurnScope:
    loaded_state = intake.loaded_state
    context = await _load_turn_context(turn_request, loaded_state, deps.session_factory)
    deps.metrics.record_memory(context.memory)
    return _TurnScope(
        turn_request=turn_request,
        loaded_state=loaded_state,
        intake=intake,
        context=context,
        result_sink=MasterModeTurnResult(
            final_state=loaded_state.state,
            movement_destination_id=intake.movement_destination_id,
        ),
        participants=participants,
        is_master_mode=is_master_mode,
        deps=deps,
    )


async def _stream_narration(scope: _TurnScope) -> AsyncIterator[ServerSentEvent]:
    """Stream narration events. On a narrator failure, refunds the turn and
    sets `narration.has_failed` instead of raising."""
    scope.deps.metrics.start_generation()
    try:
        async for sse_event in _narration_events(
            scope.turn_request,
            scope.loaded_state,
            scope.context,
            scope.intake.active_instructions,
            scope.result_sink,
            scope.narration.chunks,
            scope.narration.raw_chunks,
        ):
            _note_narration_progress(scope)
            yield sse_event
        scope.deps.metrics.finish_generation()
    except NarrationGenerationError:
        logger.warning(
            EVENT_SSE_STREAM_ERROR,
            playthrough_id=str(scope.turn_request.playthrough_id),
            outcome="error",
        )
        await scope.deps.turn_quota.refund_turn()
        scope.narration.has_failed = True


def _note_narration_progress(scope: _TurnScope) -> None:
    if scope.narration.chunks:
        scope.deps.metrics.mark_first_token()


async def _scope_media(scope: _TurnScope, post_generation: _PostGeneration) -> _Media:
    return await _generate_media(
        scope.turn_request,
        scope.loaded_state,
        post_generation.working_state,
        scope.narration.chunks,
        scope.narration.raw_chunks,
        scope.deps.session_factory,
        scope.deps.turn_quota,
        scope.intake.authored_image_url,
    )


async def _commit_turn(
    scope: _TurnScope, post_generation: _PostGeneration, media: _Media
) -> tuple[bool, dict[str, object] | None, ServerSentEvent | None]:
    async with scope.deps.session_factory() as session:
        playthrough_repo = PlaythroughRepo(session)
        memory_commit = _build_memory_commit(
            scope.loaded_state,
            post_generation.working_state,
            post_generation.tool_calls,
            scope.intake.effects,
            playthrough_repo,
        )
        write_arguments = (
            scope.turn_request,
            scope.loaded_state,
            "".join(scope.narration.chunks),
            playthrough_repo,
            TurnLogRepo(session),
            ScenarioRepo(session),
            memory_commit,
        )
        updated_state, degraded_event = await _persist_turn(
            write_arguments,
            _write_options(scope, post_generation, media),
            str(scope.turn_request.playthrough_id),
        )
    return memory_commit.outbox_repo is not None, updated_state, degraded_event


def _write_options(
    scope: _TurnScope, post_generation: _PostGeneration, media: _Media
) -> dict[str, object]:
    return {
        "working_state": post_generation.working_state,
        "tool_calls": post_generation.tool_calls,
        "mutated_paths": (scope.intake.mutated_paths | post_generation.mutated_paths)
        or None,
        "scene_image": media.scene_image,
        "narration_audio": media.narration_audio,
        "token_usage": scope.result_sink.token_usage if scope.result_sink else None,
        "turn_metrics": scope.deps.metrics,
        "turn_id": scope.turn_id,
    }


async def _finish_turn(
    scope: _TurnScope, outcome: _TurnOutcome
) -> AsyncIterator[ServerSentEvent]:
    """Run the post-narration checks and media, then commit the turn."""
    post_generation = await _post_generation(
        scope.turn_request,
        scope.loaded_state,
        scope.result_sink,
        len(scope.participants),
        scope.is_master_mode,
    )
    scope.deps.metrics.record_tool_calls(scope.result_sink.tool_calls)
    media = await _scope_media(scope, post_generation)
    for media_event in media.events:
        yield media_event
    is_registered, updated_state, degraded_event = await _commit_turn(
        scope, post_generation, media
    )
    outcome.post_generation = post_generation
    outcome.is_registered_with_memory = is_registered
    if degraded_event is not None or updated_state is None:
        yield degraded_event or response_streamer.degraded_event(
            _DEGRADED_WRITE_MESSAGE
        )
        return
    outcome.updated_state = updated_state


async def _tail_events(
    scope: _TurnScope, outcome: _TurnOutcome
) -> AsyncIterator[ServerSentEvent]:
    if outcome.updated_state is None:
        return
    async for tail_event in _post_write_events(scope, outcome):
        yield tail_event


async def _narrate_and_commit_events(
    scope: _TurnScope,
) -> AsyncIterator[ServerSentEvent]:
    async for narration_event in _stream_narration(scope):
        yield narration_event
    if scope.narration.has_failed:
        return
    outcome = _TurnOutcome()
    async for finish_event in _finish_turn(scope, outcome):
        yield finish_event
    async for tail_event in _tail_events(scope, outcome):
        yield tail_event


async def _rejected_turn_event(
    turn_request: TurnRequest, deps: _TurnDeps, error: BaseAppException
) -> ServerSentEvent:
    """The stream is already open, so a rejected request cannot become an HTTP
    error; it ends as `degraded` and the turn's quota is given back."""
    logger.warning(
        EVENT_SSE_STREAM_ERROR,
        playthrough_id=str(turn_request.playthrough_id),
        outcome="rejected",
        error_code=type(error).__name__,
    )
    await deps.turn_quota.refund_turn()
    return response_streamer.degraded_event(_DEGRADED_REJECTED_MESSAGE)


async def _run_turn_events(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    deps: _TurnDeps,
) -> AsyncIterator[ServerSentEvent]:
    logger.info(
        EVENT_SSE_STREAM_OPENED, playthrough_id=str(turn_request.playthrough_id)
    )
    if turn_request.input_truncation is not None:
        yield response_streamer.input_truncated_event(
            turn_request.input_truncation.original_length,
            turn_request.input_truncation.max_length,
        )
    is_master_mode = loaded_state.scenario_snapshot.get("mode") == "master"
    try:
        intake, participants = await _load_intake(
            turn_request, loaded_state, is_master_mode, deps
        )
    except BaseAppException as error:
        yield await _rejected_turn_event(turn_request, deps, error)
        return
    for event in _intake_events(intake):
        yield event
    scope = await _build_turn_scope(
        turn_request, intake, participants, is_master_mode, deps
    )
    async for event in _narrate_and_commit_events(scope):
        yield event


def _build_memory_commit(
    loaded_state: LoadedState,
    working_state: dict[str, object] | None,
    tool_calls: list[dict[str, object]] | None,
    intake_effects: accepted_delta_builder.IntakeEffects,
    playthrough_repo: PlaythroughRepo,
) -> MemoryCommit:
    """The accepted delta for this turn plus, unless the playthrough predates
    memory registration (no pinned revision), the repo that writes its outbox
    row in the turn's transaction."""
    accepted_delta = accepted_delta_builder.build_accepted_delta(
        loaded_state.state, working_state, tool_calls, intake_effects
    )
    is_registered_with_memory = loaded_state.memory_publish_revision is not None
    outbox_repo = (
        MemoryOutboxRepo(playthrough_repo.session)
        if is_registered_with_memory
        else None
    )
    return MemoryCommit(accepted_delta=accepted_delta, outbox_repo=outbox_repo)


async def _evaluate_and_finalize_ending(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    updated_state: dict[str, object],
    session_factory: SessionFactory,
    is_registered_with_memory: bool,
) -> MatchedOutcome | None:
    """Evaluate end conditions against the just-written state and, on a
    match, persist the ending — suppressed (returns None) if persisting it
    fails, since the turn itself is already durable at this point."""
    matched_outcome = end_condition_evaluator.evaluate_end_conditions(
        loaded_state, updated_state
    )
    if not matched_outcome:
        return None
    async with session_factory() as session:
        ending_persisted = await _finalize_ending(
            turn_request.playthrough_id,
            matched_outcome,
            PlaythroughRepo(session),
            MemoryOutboxRepo(session) if is_registered_with_memory else None,
            loaded_state.turn_count + 1,
        )
    if ending_persisted:
        await notification_manager.notify_playthrough_ended(
            turn_request.playthrough_id, matched_outcome.outcome_title
        )
    return matched_outcome if ending_persisted else None


async def _evaluate_master_mode_post_generation(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    result_sink: MasterModeTurnResult,
    participant_count: int,
) -> tuple[
    dict[str, object],
    list[dict[str, object]],
    MatchedMinigameTrigger | None,
    CheckEventPayload | RuleCheckEventPayload | None,
    set[str],
]:
    """Fold the AI's mutations with map discovery, then evaluate a minigame
    trigger or a proposed check against the result (minigame wins if both
    would fire the same turn, see module docstring)."""
    escalation_applier.apply_escalation(
        loaded_state.state, loaded_state.scenario_snapshot, result_sink
    )
    movement_resolver.enforce_code_movement(
        result_sink.final_state, result_sink.movement_destination_id
    )
    movement_resolver.log_movement_source(
        result_sink.movement_destination_id, result_sink.mutated_paths
    )
    working_state = result_sink.final_state
    tool_calls = [tc.model_dump() for tc in result_sink.tool_calls]
    if turn_request.fantasy_action is not None:
        tool_calls.append(
            {
                "tool_name": "_fantasy_action",
                "arguments": {"action_id": turn_request.fantasy_action.action_id},
                "result": {},
                "is_valid": True,
            }
        )
    mutated_paths = set(result_sink.mutated_paths)
    if loaded_state.scenario_snapshot.get("maps"):
        mutated_paths |= map_state_sync.sync_discovered_locations(
            loaded_state.state, working_state
        )

    matched_trigger = minigame_trigger_evaluator.evaluate_trigger(
        loaded_state.scenario_snapshot.get("scenario_minigames", []) or [],
        working_state,
        participant_count,
        settings.minigame_iframe_handshake_timeout_seconds,
    )
    proposed_check_payload: CheckEventPayload | RuleCheckEventPayload | None = None
    if matched_trigger:
        mutated_paths |= await _stamp_pending_minigame(working_state, matched_trigger)
    elif result_sink.proposed_check:
        proposed_check_payload = _stamp_pending_check(
            working_state, turn_request, result_sink.proposed_check
        )
        mutated_paths |= {check_result_resolver.STATE_KEY_PENDING_CHECK}

    rule_check = rule_check_trigger_evaluator.evaluate_rule_check_triggers(
        loaded_state.scenario_snapshot,
        working_state,
        participant_count=participant_count,
        can_open=not matched_trigger and not result_sink.proposed_check,
        now_ms=rule_check_trigger_evaluator.current_time_ms(),
    )
    mutated_paths |= rule_check.mutated_paths
    proposed_check_payload = proposed_check_payload or rule_check.payload

    return (
        working_state,
        tool_calls,
        matched_trigger,
        proposed_check_payload,
        mutated_paths,
    )


@dataclass(frozen=True)
class MasterModeIntake:
    """What the pre-narration pass produced for a master-mode turn."""

    loaded_state: LoadedState
    active_instructions: list[str]
    mutated_paths: set[str]
    check_resolved_sse_event: ServerSentEvent | None
    effects: accepted_delta_builder.IntakeEffects
    fired_cues: list[FiredCue] = field(default_factory=list)
    metrics: IntakeMetrics = field(default_factory=IntakeMetrics)
    movement_destination_id: str | None = None
    fired_effects: list[FiredEffect] = field(default_factory=list)
    authored_image_url: str | None = None

    @classmethod
    def without_intake(cls, loaded_state: LoadedState) -> "MasterModeIntake":
        return cls(
            loaded_state,
            [],
            set(),
            None,
            accepted_delta_builder.IntakeEffects(loaded_state.state),
        )


async def _prepare_master_mode_turn(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    playthrough_repo: PlaythroughRepo,
) -> MasterModeIntake:
    """Early check-roll persistence (only for a check_resolution attempt)
    plus the minigame/check-resolution/condition-evaluator intake pass,
    combined so _run_turn_events branches on is_master_mode only once."""
    turn_start_state = loaded_state.state
    loaded_state, check_event, check_resolved = await _resolve_checks_early(
        turn_request, loaded_state, playthrough_repo
    )
    check_outcomes = _collect_check_outcomes(turn_request, loaded_state, check_resolved)
    evaluation = _evaluate_master_mode_intake(turn_request, loaded_state)
    effects = accepted_delta_builder.IntakeEffects(
        turn_start_state, evaluation.effect_sources, check_resolved
    )
    return MasterModeIntake(
        evaluation.loaded_state,
        evaluation.instructions,
        evaluation.mutated_paths,
        check_event,
        effects,
        evaluation.fired_cues,
        IntakeMetrics(
            evaluation.fired_condition_ids,
            check_outcomes,
            evaluation.condition_evaluator_ms,
        ),
        evaluation.movement_destination_id,
        evaluation.fired_effects,
        evaluation.authored_image_url,
    )


async def _resolve_checks_early(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    playthrough_repo: PlaythroughRepo,
) -> tuple[LoadedState, ServerSentEvent | None, CheckResolvedPayload | None]:
    if turn_request.action_kind == "check_resolution":
        return await _resolve_pending_check_early(
            turn_request, loaded_state, playthrough_repo
        )
    if turn_request.action_kind == "check_report":
        loaded_state, check_event = await _resolve_rule_check_early(
            turn_request, loaded_state, playthrough_repo
        )
        return loaded_state, check_event, None
    return loaded_state, None, None


def _collect_check_outcomes(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    check_resolved: CheckResolvedPayload | None,
) -> list[CheckOutcome]:
    """The check this turn resolved, as metrics rows. A declined dice check has
    no pass/fail result and is not recorded."""
    if check_resolved is not None and check_resolved.is_success is not None:
        result = (
            CHECK_RESULT_PASSED if check_resolved.is_success else CHECK_RESULT_FAILED
        )
        return [
            CheckOutcome(
                check_id=check_resolved.check_id, kind=CHECK_KIND_DICE, result=result
            )
        ]
    if turn_request.action_kind == "check_report":
        return _rule_check_outcomes(loaded_state)
    if turn_request.action_kind == "minigame_result":
        return _minigame_outcomes(turn_request)
    return []


def _minigame_outcomes(turn_request: TurnRequest) -> list[CheckOutcome]:
    minigame_result = turn_request.minigame_result
    if minigame_result is None:
        return []
    result = MINIGAME_OUTCOME_RESULTS.get(minigame_result.outcome_tag)
    if result is None:
        return []
    return [
        CheckOutcome(
            check_id=minigame_result.minigame_id,
            kind=CHECK_KIND_MINIGAME,
            result=result,
            composure_score=minigame_result.score,
        )
    ]


def _rule_check_outcomes(loaded_state: LoadedState) -> list[CheckOutcome]:
    pending = loaded_state.state.get(check_result_resolver.STATE_KEY_PENDING_CHECK)
    if not isinstance(pending, dict) or pending.get("resolved") is None:
        return []
    return [
        rule_check_resolver.summarize_outcome(
            pending,
            loaded_state.scenario_snapshot,
            now_ms=rule_check_trigger_evaluator.current_time_ms(),
        )
    ]


@dataclass(frozen=True)
class _IntakeEvaluation:
    loaded_state: LoadedState
    instructions: list[str]
    mutated_paths: set[str]
    effect_sources: dict[str, str]
    fired_cues: list[FiredCue]
    fired_condition_ids: list[str]
    condition_evaluator_ms: int
    movement_destination_id: str | None = None
    fired_effects: list[FiredEffect] = field(default_factory=list)
    authored_image_url: str | None = None


def _resolve_fantasy_intake(
    turn_request: TurnRequest, loaded_state: LoadedState
) -> fantasy_action_resolver.FantasyActionResolution:
    action = turn_request.fantasy_action
    if action is None:
        raise FantasyActionError("Fantasy action is missing.")
    resolution = fantasy_action_resolver.resolve_action(
        action.action_id, loaded_state.state, loaded_state.scenario_snapshot
    )
    validated = state_validator.validate_applied_change(
        "player", resolution.state, loaded_state.scenario_snapshot
    )
    if not validated.is_valid or validated.updated_state is None:
        raise FantasyActionError(
            validated.error_message or "The action could not be applied."
        )
    if protects_transition(
        resolution.state,
        validated.updated_state,
        loaded_state.scenario_snapshot.get("fantasy_mechanics"),
    ):
        raise FantasyActionError("Fantasy state does not match the authored schema.")
    return fantasy_action_resolver.FantasyActionResolution(
        validated.updated_state, resolution.mutated_paths, resolution.instruction
    )


def _apply_fantasy_intake(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    instructions: list[str],
    paths: set[str],
    sources: dict[str, str],
) -> LoadedState:
    if turn_request.action_kind != "fantasy_action":
        return loaded_state
    resolution = _resolve_fantasy_intake(turn_request, loaded_state)
    instructions.append(resolution.instruction)
    paths.update(resolution.mutated_paths)
    sources.update(dict.fromkeys(resolution.mutated_paths, "fantasy_action"))
    return loaded_state.model_copy(update={"state": resolution.state})


def _evaluate_master_mode_intake(
    turn_request: TurnRequest, loaded_state: LoadedState
) -> _IntakeEvaluation:
    """Run minigame_result_resolver/check_result_resolver (only for the
    matching action_kind), then condition_evaluator, in the pipeline slot
    between state_loader and context_retrieval — the resolver runs first so
    condition_evaluator's own Effect C pass sees its mutation already
    applied."""
    active_instructions: list[str] = []
    mutated_paths: set[str] = set()
    effect_sources: dict[str, str] = {}

    loaded_state = _apply_fantasy_intake(
        turn_request, loaded_state, active_instructions, mutated_paths, effect_sources
    )

    if turn_request.action_kind == "minigame_result" and turn_request.minigame_result:
        resolution = _resolve_minigame_intake(turn_request, loaded_state)
        loaded_state = loaded_state.model_copy(update={"state": resolution.state})
        active_instructions.append(resolution.instruction)
        mutated_paths |= resolution.mutated_paths
        effect_sources.update(
            dict.fromkeys(
                resolution.mutated_paths, accepted_delta_builder.EFFECT_SOURCE_MINIGAME
            )
        )

    if turn_request.action_kind == "check_resolution" and turn_request.check_resolution:
        loaded_state, instruction = _resolve_check_intake(turn_request, loaded_state)
        active_instructions.append(instruction)
        mutated_paths |= {check_result_resolver.STATE_KEY_PENDING_CHECK}

    if turn_request.action_kind == "check_report":
        loaded_state, rule_instruction, rule_paths = _resolve_rule_check_intake(
            loaded_state
        )
        active_instructions.append(rule_instruction)
        mutated_paths |= rule_paths
        effect_sources.update(
            dict.fromkeys(rule_paths, accepted_delta_builder.EFFECT_SOURCE_RULE_CHECK)
        )

    movement = _resolve_typed_movement(turn_request, loaded_state)
    loaded_state = loaded_state.model_copy(update={"state": movement.state})
    mutated_paths |= movement.mutated_paths
    effect_sources.update(
        dict.fromkeys(
            movement.mutated_paths, accepted_delta_builder.EFFECT_SOURCE_MOVEMENT
        )
    )

    evaluation = condition_evaluator.evaluate_conditions(loaded_state)
    loaded_state = loaded_state.model_copy(update={"state": evaluation.state})
    active_instructions += evaluation.active_instructions
    mutated_paths |= evaluation.mutated_paths
    for path in evaluation.mutated_paths:
        effect_sources.setdefault(path, accepted_delta_builder.EFFECT_SOURCE_CONDITION)
    return _IntakeEvaluation(
        loaded_state,
        active_instructions,
        mutated_paths,
        effect_sources,
        evaluation.fired_cues,
        evaluation.fired_condition_ids,
        round(evaluation.duration_ms),
        movement.destination_id,
        evaluation.fired_effects,
        evaluation.authored_image_url,
    )


def _resolve_typed_movement(
    turn_request: TurnRequest, loaded_state: LoadedState
) -> movement_resolver.MovementResolution:
    if turn_request.action_kind != "narrative":
        return movement_resolver.MovementResolution(loaded_state.state)
    return movement_resolver.resolve_movement(
        turn_request.action_text,
        turn_request.action_mode,
        loaded_state.state,
        loaded_state.scenario_snapshot,
    )


def _resolve_minigame_intake(
    turn_request: TurnRequest, loaded_state: LoadedState
) -> minigame_result_resolver.MinigameResolution:
    minigame_result = turn_request.minigame_result
    assert minigame_result is not None  # guaranteed by the caller's gating
    return minigame_result_resolver.resolve_result(
        loaded_state.scenario_snapshot.get("scenario_minigames", []) or [],
        loaded_state.state,
        loaded_state.scenario_snapshot,
        minigame_result.minigame_id,
        minigame_result.outcome_tag,
        minigame_result.score,
    )


def _resolve_check_intake(
    turn_request: TurnRequest, loaded_state: LoadedState
) -> tuple[LoadedState, str]:
    """Pure — the roll (if any) was already computed and durably persisted
    by _resolve_pending_check_early before this runs; this only builds the
    in-memory turn state + narrator instruction from it."""
    check_resolution_input = turn_request.check_resolution
    assert check_resolution_input is not None  # guaranteed by request_receiver gating
    pending_check = loaded_state.state.get(
        check_result_resolver.STATE_KEY_PENDING_CHECK, {}
    )
    check_type = str(pending_check.get("check_type", ""))
    if check_resolution_input.resolution == "decline":
        resolution = check_result_resolver.resolve_decline(
            loaded_state.state, check_type
        )
    else:
        resolution = check_result_resolver.resolve_attempt(
            loaded_state.state,
            check_type,
            int(pending_check.get("difficulty_class", 10)),
            int(pending_check.get("resolved_roll", 0)),
        )
    return loaded_state.model_copy(
        update={"state": resolution.state}
    ), resolution.instruction


def _resolve_rule_check_intake(
    loaded_state: LoadedState,
) -> tuple[LoadedState, str, set[str]]:
    """Pure: the answer was already judged and durably stamped by
    _resolve_rule_check_early; this writes its result into state."""
    resolution = rule_check_resolver.resolve_report(
        loaded_state.state, loaded_state.scenario_snapshot
    )
    return (
        loaded_state.model_copy(update={"state": resolution.state}),
        resolution.instruction,
        resolution.mutated_paths,
    )


async def _resolve_rule_check_early(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    playthrough_repo: PlaythroughRepo,
) -> tuple[LoadedState, ServerSentEvent | None]:
    """Judge the report on the server and commit the judgment before any Gemini
    call, then announce `check_resolved` (id and kind only)."""
    report = turn_request.check_report
    pending = loaded_state.state.get(check_result_resolver.STATE_KEY_PENDING_CHECK)
    if report is None or not isinstance(pending, dict):
        return loaded_state, None
    stamped_state = await rule_check_resolver.ensure_report_persisted(
        turn_request.playthrough_id,
        loaded_state.state,
        report,
        now_ms=rule_check_trigger_evaluator.current_time_ms(),
        playthrough_repo=playthrough_repo,
        expected_turn_count=loaded_state.turn_count,
    )
    payload = RuleCheckResolvedPayload(
        check_id=str(pending.get("check_id", "")), kind=str(pending.get("kind", ""))
    )
    return (
        loaded_state.model_copy(update={"state": stamped_state}),
        response_streamer.check_resolved_event(payload),
    )


async def _resolve_pending_check_early(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    playthrough_repo: PlaythroughRepo,
) -> tuple[LoadedState, ServerSentEvent | None, CheckResolvedPayload | None]:
    """Attempt: persist the roll (its own commit) before any Gemini call, so
    a dropped connection can't cause a reroll on retry. Decline: no roll, no
    early commit needed. Either way, build the check_resolved SSE event from
    the pending check's data captured before condition_evaluator's later
    pass or the resolver's own pop removes it from state."""
    check_resolution_input = turn_request.check_resolution
    if check_resolution_input is None:
        return loaded_state, None, None
    pending_check = loaded_state.state.get(
        check_result_resolver.STATE_KEY_PENDING_CHECK
    )
    if not isinstance(pending_check, dict):
        return loaded_state, None, None

    resolved_roll: int | None = None
    if check_resolution_input.resolution == "attempt":
        (
            updated_state,
            resolved_roll,
        ) = await check_result_resolver.ensure_roll_persisted(
            turn_request.playthrough_id,
            loaded_state.state,
            playthrough_repo,
            loaded_state.turn_count,
        )
        loaded_state = loaded_state.model_copy(update={"state": updated_state})

    payload = _check_resolved_payload(pending_check, resolved_roll)
    return loaded_state, response_streamer.check_resolved_event(payload), payload


def _check_resolved_payload(
    pending_check: dict[str, object], resolved_roll: int | None
) -> CheckResolvedPayload:
    difficulty_class = int(pending_check.get("difficulty_class", 10))
    return CheckResolvedPayload(
        check_id=str(pending_check.get("check_id", "")),
        check_type=str(pending_check.get("check_type", "")),
        difficulty_class=difficulty_class,
        resolved_roll=resolved_roll,
        is_success=(resolved_roll >= difficulty_class)
        if resolved_roll is not None
        else None,
    )


async def _generate_turn_scene_image(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    working_state: dict[str, object] | None,
    narration_text: str,
    session_factory: SessionFactory,
) -> SceneImageResult | None:
    """Generate this 'see' action turn's scene image, grounded in the current
    location (master mode) and the prior image generated for that same
    location in this playthrough, if any."""
    state = working_state if working_state is not None else loaded_state.state
    current_location_id = state.get("current_location_id")
    location = scene_image_generator.find_location_entity(
        loaded_state.scenario_snapshot, current_location_id
    )
    prior_prompt = await _prior_scene_prompt(
        session_factory, turn_request.playthrough_id, current_location_id
    )

    result = await scene_image_generator.generate_scene_image(
        narration_text,
        location,
        prior_prompt,
        settings.image_generation_timeout_seconds,
    )
    if not result:
        return None
    image_url, composed_prompt = result
    location_id = str(current_location_id) if current_location_id else None
    return SceneImageResult(image_url, location_id, composed_prompt)


async def _authored_scene_image(
    turn_request: TurnRequest, image_url: str
) -> tuple[SceneImageResult, ServerSentEvent]:
    """An image the scenario authored for this moment: no generation and no
    quota, so it is shown in alpha mode too."""
    await spectator_manager.publish(
        turn_request.playthrough_id, "scene_image", image_url
    )
    return (
        SceneImageResult(image_url, None, None),
        response_streamer.scene_image_event(image_url),
    )


async def _maybe_generate_scene_image(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    working_state: dict[str, object] | None,
    chunks: list[str],
    session_factory: SessionFactory,
    turn_quota: TurnQuota,
) -> tuple[SceneImageResult | None, ServerSentEvent | None]:
    """Generate this 'see'-action turn's scene image, publish it to
    spectators, and return both the result (for state_writer) and the SSE
    event to yield -- (None, None) when action_mode isn't "see" or
    generation failed, (None, quota_notice) when the image quota is spent."""
    if settings.is_alpha_mode or turn_request.action_mode != "see":
        return None, None
    extra = await turn_quota.reserve_extra(QuotaFeature.SCENE_IMAGE)
    if not extra.is_allowed:
        return None, _quota_notice(QuotaFeature.SCENE_IMAGE, extra)
    scene_image = await _generate_turn_scene_image(
        turn_request, loaded_state, working_state, "".join(chunks), session_factory
    )
    if not scene_image:
        await extra.refund()
        return None, None
    await spectator_manager.publish(
        turn_request.playthrough_id, "scene_image", scene_image.image_url
    )
    sse_event = response_streamer.scene_image_event(scene_image.image_url)
    return scene_image, sse_event


async def _maybe_generate_narration_audio(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    raw_chunks: list[str],
    turn_quota: TurnQuota,
) -> tuple[NarrationAudioResult | None, ServerSentEvent | None]:
    """Generate this turn's narration audio when requested, publish it to
    spectators, and return both the result (for state_writer) and the SSE
    event to yield -- (None, None) when the flag wasn't set or generation
    failed, so a turn with voice output off never incurs TTS cost, and
    (None, quota_notice) when the voice narration quota is spent."""
    if settings.is_alpha_mode or not turn_request.voice_output_requested:
        return None, None
    extra = await turn_quota.reserve_extra(QuotaFeature.TTS_NARRATION)
    if not extra.is_allowed:
        return None, _quota_notice(QuotaFeature.TTS_NARRATION, extra)
    narration_audio = await _generate_turn_narration_audio(
        "".join(raw_chunks), loaded_state
    )
    if not narration_audio:
        await extra.refund()
        return None, None
    await spectator_manager.publish(
        turn_request.playthrough_id, "narration_audio", narration_audio.audio_url
    )
    sse_event = response_streamer.narration_audio_event(narration_audio.audio_url)
    return narration_audio, sse_event


def _quota_notice(feature: QuotaFeature, extra: ExtraReservation) -> ServerSentEvent:
    denial = extra.denial
    reset_at = denial.reset_at if isinstance(denial, RateLimitExceededError) else None
    return response_streamer.quota_notice_event(
        feature.value, denial.code, denial.message, reset_at
    )


async def _generate_turn_narration_audio(
    raw_tagged_text: str, loaded_state: LoadedState
) -> NarrationAudioResult | None:
    """Generate this turn's narration audio, using the scenario's
    author-chosen narrator voice (falling back to the configured default
    when unset) plus a deterministically-assigned NPC voice, if any."""
    narrator_voice = (
        loaded_state.scenario_snapshot.get("narrator_voice_name")
        or settings.text_to_speech_default_voice
    )
    return await narration_audio_generator.generate_narration_audio(
        raw_tagged_text,
        str(narrator_voice),
        speaker_voice_pool.NPC_VOICE_POOL,
        settings.text_to_speech_timeout_seconds,
    )


async def _stamp_pending_minigame(
    working_state: dict[str, object], matched_trigger: MatchedMinigameTrigger
) -> set[str]:
    """Mutate working_state in place with the matched trigger's payload."""
    working_state[minigame_trigger_evaluator.STATE_KEY_PENDING_MINIGAME] = (
        matched_trigger.payload
    )
    return {minigame_trigger_evaluator.STATE_KEY_PENDING_MINIGAME}


def _stamp_pending_check(
    working_state: dict[str, object],
    turn_request: TurnRequest,
    proposed_check: ProposedCheck,
) -> CheckEventPayload:
    """Mutate working_state in place with the model's proposed check,
    generating the server-side check_id/ownership nonce — mirrors
    _stamp_pending_minigame."""
    check_id = str(uuid.uuid4())
    working_state[check_result_resolver.STATE_KEY_PENDING_CHECK] = {
        "check_id": check_id,
        "check_type": proposed_check.check_type,
        "difficulty_class": proposed_check.difficulty_class,
        "reasoning": proposed_check.reasoning,
        "proposing_participant_id": str(turn_request.participant_id),
        "resolved_roll": None,
    }
    return CheckEventPayload(
        check_id=check_id,
        check_type=proposed_check.check_type,
        difficulty_class=proposed_check.difficulty_class,
        reasoning=proposed_check.reasoning,
    )


def _build_turn_summary_event(
    loaded_state: LoadedState,
    updated_state: dict[str, object],
    tool_calls: list[dict[str, object]],
) -> ServerSentEvent:
    """Compose the turn_summary event from this turn's tool calls plus the
    full set of currently-active conditions (not just ones that changed this
    turn) against the final, post-write state."""
    conditions = loaded_state.scenario_snapshot.get("scenario_conditions", []) or []
    state_schema = loaded_state.scenario_snapshot.get("state_schema")
    active_conditions = condition_evaluator.list_active_condition_labels(
        conditions,
        updated_state,
        state_schema if isinstance(state_schema, dict) else None,
    )
    payload = turn_summary_builder.build_turn_summary(
        tool_calls,
        loaded_state.state,
        updated_state,
        loaded_state.scenario_snapshot,
        active_conditions,
    )
    return response_streamer.turn_summary_event(payload)


async def _persist_ending(
    playthrough_id: uuid.UUID,
    matched_outcome: MatchedOutcome,
    playthrough_repo: PlaythroughRepo,
    memory_outbox_repo: MemoryOutboxRepo | None,
    turn_number: int,
) -> None:
    await playthrough_repo.mark_ended(
        playthrough_id,
        matched_outcome.outcome_tag,
        matched_outcome.outcome_title,
        matched_outcome.outcome_text,
        outcome_id=matched_outcome.outcome_id,
        should_commit=False,
    )
    if memory_outbox_repo is not None:
        await memory_outbox_repo.add_flush_row(playthrough_id, turn_number)
    await playthrough_repo.session.commit()


def _log_ending_write_failed(playthrough_id: uuid.UUID, exc: SQLAlchemyError) -> None:
    logger.warning(
        EVENT_PLAYTHROUGH_ENDING_WRITE_FAILED,
        playthrough_id=str(playthrough_id),
        error=str(exc),
    )


async def _finalize_ending(
    playthrough_id: uuid.UUID,
    matched_outcome: MatchedOutcome,
    playthrough_repo: PlaythroughRepo,
    memory_outbox_repo: MemoryOutboxRepo | None,
    turn_number: int,
) -> bool:
    """Persist the matched outcome and broadcast it to other participants.

    Returns whether the outcome was persisted. The turn itself was already
    committed by state_writer before this runs, so a failure here degrades
    only the ending status, not the turn — caller must suppress
    playthrough_ended_event on False rather than fail the whole turn. The
    memory flush row shares the ending's transaction: both commit or neither.
    """
    try:
        await _persist_ending(
            playthrough_id,
            matched_outcome,
            playthrough_repo,
            memory_outbox_repo,
            turn_number,
        )
    except SQLAlchemyError as exc:
        await playthrough_repo.session.rollback()
        _log_ending_write_failed(playthrough_id, exc)
        return False
    return True


async def _after_write(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    participants: list[Participant],
    is_registered_with_memory: bool,
) -> None:
    """Deliver to memory, then fire the multiplayer notification and spectator relay."""
    new_turn_count = loaded_state.turn_count + 1
    if is_registered_with_memory:
        await memory_delivery.deliver_after_commit(turn_request.playthrough_id)
    narrative_count = loaded_state.narrative_turn_count
    await _notify_next_participant(
        turn_request.playthrough_id,
        new_turn_count if narrative_count is None else narrative_count + 1,
        participants,
    )
    await spectator_manager.publish(turn_request.playthrough_id, "done", "")


async def _notify_next_participant(
    playthrough_id: uuid.UUID,
    new_turn_count: int,
    participants: list[Participant],
) -> None:
    """Push a 'your_turn' notification to whoever acts next, in multiplayer
    only. participants is fetched once, near the top of _run_turn_events —
    also the source of participant_count for the minigame solo-only gate."""
    if len(participants) <= 1:
        return
    next_participant = expected_participant(participants, new_turn_count)
    await notification_manager.notify_next_turn(
        playthrough_id, next_participant.participant_id
    )


async def _memory_degraded_event(
    session_factory: SessionFactory,
    is_registered_with_memory: bool,
    playthrough_id: uuid.UUID,
    turn_number: int,
    retrieval_reasons: list[str],
) -> ServerSentEvent | None:
    if not is_registered_with_memory:
        return None
    async with session_factory() as session:
        return await memory_degraded.build_memory_degraded_event(
            MemoryOutboxRepo(session), playthrough_id, turn_number, retrieval_reasons
        )


async def _prior_scene_prompt(
    session_factory: SessionFactory,
    playthrough_id: uuid.UUID,
    current_location_id: object,
) -> str | None:
    if not current_location_id:
        return None
    async with session_factory() as session:
        prior = await TurnLogRepo(session).find_latest_by_location(
            playthrough_id, str(current_location_id)
        )
        return prior.scene_image_prompt if prior else None


async def _load_intake(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    is_master_mode: bool,
    deps: _TurnDeps,
) -> tuple["MasterModeIntake", list[Participant]]:
    async with deps.session_factory() as session:
        participants = await ParticipantRepo(session).list_by_playthrough(
            turn_request.playthrough_id
        )
        session.expunge_all()
        intake = await _intake_for_turn(
            is_master_mode, turn_request, loaded_state, PlaythroughRepo(session)
        )
    deps.metrics.record_intake(intake.metrics)
    return intake, participants


def _intake_events(intake: "MasterModeIntake") -> list[ServerSentEvent]:
    events = []
    if intake.check_resolved_sse_event:
        events.append(intake.check_resolved_sse_event)
    events.extend(response_streamer.sensory_cue_event(cue) for cue in intake.fired_cues)
    events.extend(
        response_streamer.client_effect_event(effect) for effect in intake.fired_effects
    )
    if _has_state_update(intake.loaded_state):
        events.append(
            response_streamer.state_update_event(
                state_update_builder.build_state_update(
                    intake.loaded_state.scenario_snapshot, intake.loaded_state.state
                )
            )
        )
    return events
