"""Persists a completed turn: TurnLog row, updated state, conditional play_count.

Commits explicitly on success rather than relying on a request-scoped
dependency's post-yield commit: this pipeline is consumed from inside a
long-lived SSE generator, and FastAPI resolves `Depends(...)` cleanup as soon
as the endpoint function returns the response object — before the generator
body (and therefore this write) has actually run (the same class of ordering
bug documented in docs/adr/010 for BackgroundTasks). Committing here is what
guarantees "done" is never emitted for a turn that isn't actually durable.
"""

import time
import uuid
from dataclasses import dataclass

import structlog
from app.config import settings
from app.db.models.turn_log import TurnLog
from app.exceptions.turn_exceptions import OptimisticLockError, StateWriteError
from app.models.accepted_delta import AcceptedDelta
from app.models.token_usage import TokenUsage
from app.models.turn import LoadedState, TurnRequest
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.repositories.turn_metrics_repo import TurnMetricsRepo
from app.turn.turn_metrics_collector import TurnMetricsCollector
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

EVENT_TURN_STEP_COMPLETED = "turn_step_completed"
EVENT_TURN_STATE_WRITE_FAILED = "turn_state_write_failed"
EVENT_TURN_METRICS_FAILED = "turn_metrics_failed"
STEP_NAME = "state_writer"


@dataclass(frozen=True)
class SceneImageResult:
    """A scene image generated for this turn's 'see' action, bundled to keep
    write_turn's parameter list from growing per-field (CLAUDE.md 30-line/
    single-responsibility guidance)."""

    image_url: str
    location_id: str | None
    scene_image_prompt: str | None


@dataclass(frozen=True)
class NarrationAudioResult:
    """This turn's generated narration audio, bundled for the same reason
    as SceneImageResult above."""

    audio_url: str


@dataclass(frozen=True)
class MemoryCommit:
    """What this turn hands to memory, committed with the turn itself.

    accepted_delta is always stored on the TurnLog row. outbox_repo is None
    when the playthrough has no pinned memory_publish_revision (a legacy
    playthrough), in which case no outbox row is written.
    """

    accepted_delta: AcceptedDelta
    outbox_repo: MemoryOutboxRepo | None


@dataclass(frozen=True)
class _TurnWrite:
    """Everything one write attempt persists, so retries re-run it unchanged."""

    turn_request: TurnRequest
    scenario_id: uuid.UUID
    is_playtest: bool
    new_turn_count: int
    expected_turn_count: int
    narrative_turn_count: int
    narration_text: str
    updated_state: dict[str, object]
    tool_calls: list[dict[str, object]]
    scene_image: SceneImageResult | None
    narration_audio: NarrationAudioResult | None
    memory_commit: MemoryCommit
    token_usage: TokenUsage | None = None
    turn_metrics: TurnMetricsCollector | None = None
    turn_id: uuid.UUID | None = None


async def write_turn(
    turn_request: TurnRequest,
    loaded_state: LoadedState,
    narration_text: str,
    playthrough_repo: PlaythroughRepo,
    turn_log_repo: TurnLogRepo,
    scenario_repo: ScenarioRepo,
    memory_commit: MemoryCommit,
    working_state: dict[str, object] | None = None,
    tool_calls: list[dict[str, object]] | None = None,
    mutated_paths: set[str] | None = None,
    scene_image: SceneImageResult | None = None,
    narration_audio: NarrationAudioResult | None = None,
    token_usage: TokenUsage | None = None,
    turn_metrics: TurnMetricsCollector | None = None,
    turn_id: uuid.UUID | None = None,
) -> dict[str, object]:
    """Persist a completed turn, retrying transient failures.

    working_state (master mode only) is the state as of after condition_
    evaluator's Effect C mutations and the AI's validated tool-call
    mutations — the base state written for this turn, instead of
    loaded_state.state directly. mutated_paths (master mode) is persisted as
    `_last_changed_fields`, read by next turn's condition_evaluator to scope
    which conditions/invariants need re-evaluating. scene_image (when the
    turn generated one, "see" mode only) is persisted onto the TurnLog row
    for scrollback/spectator display and future grounding lookups.

    memory_commit's outbox row (when enabled) shares the turn's transaction, and
    so does turn_metrics' row, inside a SAVEPOINT: a failed metrics write is
    logged and dropped, never retried and never allowed to fail the turn.
    Returns the full updated state, for end-condition evaluation.
    """
    start = time.monotonic()
    base_state = working_state if working_state is not None else loaded_state.state
    updated_state = base_state
    if mutated_paths:
        updated_state = dict(updated_state)
        updated_state["_last_changed_fields"] = sorted(mutated_paths)

    write = _TurnWrite(
        turn_request=turn_request,
        scenario_id=loaded_state.scenario_id,
        is_playtest=loaded_state.is_playtest,
        new_turn_count=loaded_state.turn_count + 1,
        expected_turn_count=loaded_state.turn_count,
        narrative_turn_count=(
            loaded_state.narrative_turn_count
            if loaded_state.narrative_turn_count is not None
            else loaded_state.turn_count
        )
        + 1,
        narration_text=narration_text,
        updated_state=updated_state,
        tool_calls=tool_calls or [],
        scene_image=scene_image,
        narration_audio=narration_audio,
        memory_commit=memory_commit,
        token_usage=token_usage,
        turn_metrics=turn_metrics,
        turn_id=turn_id,
    )
    retry_count = await _persist_with_retry(
        write, playthrough_repo, turn_log_repo, scenario_repo
    )
    logger.info(
        EVENT_TURN_STEP_COMPLETED,
        step_name=STEP_NAME,
        duration_ms=(time.monotonic() - start) * 1000,
        retry_count=retry_count,
    )
    return updated_state


def _handle_write_error(
    exc: SQLAlchemyError,
    attempt: int,
    max_attempts: int,
    playthrough_id: str,
) -> None:
    if attempt == max_attempts - 1:
        logger.error(
            EVENT_TURN_STATE_WRITE_FAILED,
            playthrough_id=playthrough_id,
            retry_count=attempt,
        )
        raise StateWriteError() from exc


async def _persist_with_retry(
    write: _TurnWrite,
    playthrough_repo: PlaythroughRepo,
    turn_log_repo: TurnLogRepo,
    scenario_repo: ScenarioRepo,
) -> int:
    max_attempts = settings.state_write_max_retries + 1
    for attempt in range(max_attempts):
        try:
            await _write_once(write, playthrough_repo, turn_log_repo, scenario_repo)
            return attempt
        except OptimisticLockError:
            await playthrough_repo.session.rollback()
            raise
        except SQLAlchemyError as exc:
            await playthrough_repo.session.rollback()
            _handle_write_error(
                exc, attempt, max_attempts, str(write.turn_request.playthrough_id)
            )
    return max_attempts - 1


async def _write_once(
    write: _TurnWrite,
    playthrough_repo: PlaythroughRepo,
    turn_log_repo: TurnLogRepo,
    scenario_repo: ScenarioRepo,
) -> None:
    await playthrough_repo.update_state(
        write.turn_request.playthrough_id,
        write.updated_state,
        write.new_turn_count,
        write.expected_turn_count,
    )
    await _insert_turn_records(write, turn_log_repo)
    should_increment_play_count = (
        write.narrative_turn_count == settings.play_count_increment_turn_threshold
        and not write.is_playtest
        and (
            write.expected_turn_count < settings.play_count_increment_turn_threshold
            or write.updated_state.get("_combat_play_count_deferred") is True
        )
    )
    if should_increment_play_count:
        await scenario_repo.increment_play_count(write.scenario_id)
    await playthrough_repo.session.commit()


async def _insert_turn_records(write: _TurnWrite, turn_log_repo: TurnLogRepo) -> None:
    """Insert the TurnLog row and, when enabled, its memory outbox row."""
    scene_image, narration_audio = write.scene_image, write.narration_audio
    turn_log = await turn_log_repo.create(
        playthrough_id=write.turn_request.playthrough_id,
        turn_number=write.new_turn_count,
        participant_id=write.turn_request.participant_id,
        action_text=write.turn_request.action_text,
        action_mode=write.turn_request.action_mode,
        narration_text=write.narration_text,
        tool_calls=write.tool_calls,
        image_url=scene_image.image_url if scene_image else None,
        location_id=scene_image.location_id if scene_image else None,
        scene_image_prompt=scene_image.scene_image_prompt if scene_image else None,
        audio_url=narration_audio.audio_url if narration_audio else None,
        accepted_delta=write.memory_commit.accepted_delta.model_dump(mode="json"),
        client_action_id=write.turn_request.client_action_id,
        prompt_tokens=write.token_usage.prompt_tokens if write.token_usage else None,
        completion_tokens=write.token_usage.completion_tokens
        if write.token_usage
        else None,
        model_name=write.token_usage.model_name if write.token_usage else None,
        turn_id=write.turn_id,
    )
    outbox_repo = write.memory_commit.outbox_repo
    if outbox_repo is not None:
        await outbox_repo.add_turn_row(
            write.turn_request.playthrough_id, write.new_turn_count, turn_log.turn_id
        )
    await _insert_turn_metrics(write, turn_log, turn_log_repo.session)


async def _insert_turn_metrics(
    write: _TurnWrite, turn_log: TurnLog, session: AsyncSession
) -> None:
    collector = write.turn_metrics
    if collector is None or not collector.is_enabled:
        return
    # NOTE: Broad on purpose; metrics must never fail or roll back a turn.
    try:
        record = collector.build_record(write.updated_state)
        async with session.begin_nested():
            await TurnMetricsRepo(session).create(
                turn_log.turn_id, turn_log.playthrough_id, turn_log.turn_number, record
            )
    except Exception:
        logger.error(
            EVENT_TURN_METRICS_FAILED,
            playthrough_id=str(turn_log.playthrough_id),
            turn_number=turn_log.turn_number,
            exc_info=True,
        )
