"""Orchestrates extraction inside a sweep: due batches, queue drain, one batch lifecycle."""

import time
from dataclasses import replace
from functools import lru_cache
from uuid import UUID

import structlog
from app.config import Settings, get_settings
from app.db.pool import get_pool
from app.exceptions.extraction_exceptions import (
    ExtractionConfigError,
    ExtractionInvalidOutputError,
    ExtractionPermanentError,
    ExtractionRateLimitedError,
    ExtractionTransientError,
)
from app.integrations.extraction_client import (
    ExtractionBackend,
    build_extraction_client,
)
from app.integrations.extraction_queue import ExtractionQueue
from app.models.extraction import (
    ExtractionResult,
    ExtractionStepStatus,
    ExtractionUsage,
    ValidatedPlan,
)
from app.models.jobs import ExtractionBatchRow
from app.repositories import extraction_batch_repo, playthrough_repo
from app.services.enrichment_service import (
    build_template_input,
    create_enrichment_batches,
    finalize_enrichment,
)
from app.services.extraction_apply import SCOPE_PURGED, apply_batch
from app.services.extraction_batches import (
    create_due_playthrough_batches,
    list_ready_batches,
)
from app.services.extraction_input import (
    BuiltInput,
    build_playthrough_input,
    load_batch_rows,
    load_system_prompt,
    seed_entity_ids_for,
    with_alias_context,
)
from app.services.extraction_runtime import ExtractionStepResult, RunState
from app.services.extraction_validator import validate_output
from app.services.retrieval_service import RetrievalService, get_retrieval_service
from app.services.stage_timer import StageTimer
from app.services.supersession_resolver import (
    PreparedResolution,
    prepare_resolution,
    resolve_with_judge,
)
from app.services.supersession_rules import merge_claims
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

EVENT_BATCH_UNEXPECTED = "extraction_batch_unexpected_error"
EVENT_BATCH_FAILED = "extraction_batch_failed"
EVENT_BATCH_TIMED = "extraction_batch_timed"
STAGE_BUILD = "build"
STAGE_LLM = "llm"
STAGE_VALIDATE_STORE = "validate_store"
STAGE_APPLY = "apply"
ERROR_MAX_ATTEMPTS = "max_attempts_exceeded"
RECOVERABLE_ERRORS = (
    ExtractionTransientError,
    ExtractionInvalidOutputError,
    ExtractionPermanentError,
)

logger = structlog.get_logger()


class ExtractionService:
    def __init__(
        self,
        pool: AsyncConnectionPool,
        settings: Settings,
        client: ExtractionBackend | None,
        queue: ExtractionQueue,
        retrieval: RetrievalService,
    ) -> None:
        self._pool = pool
        self._settings = settings
        self._client = client
        self._queue = queue
        self._retrieval = retrieval
        self._state = RunState()

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def process(
        self, playthrough_id: UUID | None, deadline_monotonic: float
    ) -> ExtractionStepResult:
        """Never raises for provider failures; they end up in the step status and batches.
        Template enrichment runs only in unscoped sweeps."""
        if self._client is None:
            return ExtractionStepResult("unconfigured", RunState().counts, [])
        self._state = RunState()
        await self._prepare_batches(playthrough_id)
        is_cut_short = await self._drain(deadline_monotonic)
        if playthrough_id is None:
            await self._finalize_enrichment()
        self._state.counts.playthroughs_touched = len(self._state.touched_scopes)
        return ExtractionStepResult(
            self._resolve_step(is_cut_short), self._state.counts, self._state.errors
        )

    async def _finalize_enrichment(self) -> None:
        async with self._pool.connection() as connection:
            await finalize_enrichment(connection)

    async def _prepare_batches(self, playthrough_id: UUID | None) -> None:
        await self._queue.recover_stalled_jobs()
        async with self._pool.connection() as connection:
            await extraction_batch_repo.release_expired_leases(connection)
            created = await create_due_playthrough_batches(
                connection, self._settings, playthrough_id
            )
            if playthrough_id is None:
                enrichment = await create_enrichment_batches(connection, self._settings)
                self._state.counts.enrichment_batches = enrichment
            ready = await list_ready_batches(connection, self._settings, playthrough_id)
        self._state.counts.batches_created = created
        self._state.batches_seen = len(ready)
        for batch in ready:
            await self._queue.defer(batch.batch_id, batch.scope_id)

    async def _drain(self, deadline_monotonic: float) -> bool:
        if self._state.batches_seen == 0:
            return False
        remaining = deadline_monotonic - time.monotonic()
        return await self._queue.drain(self._handle_batch, remaining)

    def _resolve_step(self, is_cut_short: bool) -> ExtractionStepStatus:
        if self._state.stop_step is not None:
            return self._state.stop_step
        if is_cut_short:
            return "deadline_reached"
        if self._state.batches_seen == 0:
            return "idle"
        return "completed"

    async def _handle_batch(self, batch_id: UUID) -> None:
        # NOTE: the job boundary must never raise; an unexpected error leaves the
        # batch `running`, and lease expiry returns it to pending on a later sweep.
        try:
            await self._process_batch(batch_id)
        except Exception as error:  # noqa: BLE001
            logger.error(
                EVENT_BATCH_UNEXPECTED,
                batch_id=str(batch_id),
                error_class=type(error).__name__,
            )

    async def _claim(self, batch_id: UUID) -> ExtractionBatchRow | None:
        async with self._pool.connection() as connection:
            batch = await extraction_batch_repo.get_batch(connection, batch_id)
            if batch is None or batch.status not in ("pending", "extracted"):
                return None
            if batch.validated_plan is not None:
                return await self._reuse_stored_plan(connection, batch)
            return await extraction_batch_repo.claim_pending_batch(
                connection,
                batch.scope_kind,
                batch.scope_id,
                self._settings.extraction_lease_seconds,
            )

    async def _reuse_stored_plan(
        self, connection: object, batch: ExtractionBatchRow
    ) -> ExtractionBatchRow | None:
        if batch.status == "extracted":
            return batch
        return await extraction_batch_repo.mark_batch_extracted(
            connection, batch.batch_id
        )  # type: ignore[arg-type]

    async def _process_batch(self, batch_id: UUID) -> None:
        batch = await self._claim(batch_id)
        if batch is None:
            return
        self._state.touched_scopes.add(batch.scope_id)
        timer = StageTimer()
        await self._run_batch(batch, timer)
        logger.info(
            EVENT_BATCH_TIMED,
            batch_id=str(batch.batch_id),
            scope_kind=batch.scope_kind,
            stage_ms=timer.stage_ms,
        )

    async def _run_batch(self, batch: ExtractionBatchRow, timer: StageTimer) -> None:
        if batch.validated_plan is None:
            if batch.attempt_count > self._settings.extraction_max_attempts:
                await self._fail(batch, ERROR_MAX_ATTEMPTS, is_terminal=True)
                return
            extracted = await self._extract(batch, timer)
        else:
            extracted = batch
        if extracted is not None:
            with timer.measure(STAGE_APPLY):
                await self._apply(extracted)

    async def _is_blocked_by_failed_template_batch(
        self, batch: ExtractionBatchRow
    ) -> bool:
        if batch.scope_kind != "template":
            return False
        async with self._pool.connection() as connection:
            return await extraction_batch_repo.has_failed_batch(
                connection, "template", batch.scope_id
            )

    async def _extract(
        self, batch: ExtractionBatchRow, timer: StageTimer
    ) -> ExtractionBatchRow | None:
        if await self._is_blocked_by_failed_template_batch(batch):
            async with self._pool.connection() as connection:
                await extraction_batch_repo.release_batch(connection, batch.batch_id)
            return None
        with timer.measure(STAGE_BUILD):
            built = await self._build_input(batch)
        if built is None:
            return None
        try:
            with timer.measure(STAGE_LLM):
                result = await self._call_model(batch, built)
        except ExtractionRateLimitedError as error:
            await self._release(batch, "rate_limited", error.code)
            return None
        except ExtractionConfigError as error:
            await self._release(batch, "aborted", error.code)
            return None
        except RECOVERABLE_ERRORS as error:
            await self._fail(batch, error.code or "extraction_error")
            return None
        with timer.measure(STAGE_VALIDATE_STORE):
            return await self._store_plan(batch, built, result)

    async def _call_model(
        self, batch: ExtractionBatchRow, built: BuiltInput
    ) -> ExtractionResult:
        assert self._client is not None
        system_prompt = load_system_prompt(batch.prompt_version)
        return await self._client.extract(system_prompt, built.user_content)

    async def _build_input(self, batch: ExtractionBatchRow) -> BuiltInput | None:
        async with self._pool.connection() as connection:
            if batch.scope_kind == "template":
                built = await build_template_input(connection, batch, self._settings)
            else:
                built = await self._build_playthrough_input(connection, batch)
            if built is None:
                await extraction_batch_repo.mark_batch_applied_with_note(
                    connection, batch.batch_id, SCOPE_PURGED
                )
                return None
            await extraction_batch_repo.set_input_hash(
                connection, batch.batch_id, built.input_hash
            )
            return built

    async def _build_playthrough_input(
        self, connection: AsyncConnection, batch: ExtractionBatchRow
    ) -> BuiltInput | None:
        playthrough = await playthrough_repo.get_playthrough(connection, batch.scope_id)
        if playthrough is None:
            return None
        rows = await load_batch_rows(connection, batch)
        seeds = await seed_entity_ids_for(connection, batch, playthrough, rows)
        context = await self._retrieval.extraction_context(
            batch.scope_id, seeds, batch.from_seq - 1
        )
        return await build_playthrough_input(
            connection, batch, playthrough, context, rows, self._settings
        )

    async def _validate_and_prepare(
        self, batch: ExtractionBatchRow, built: BuiltInput, result: ExtractionResult
    ) -> tuple[ValidatedPlan, PreparedResolution | None]:
        async with self._pool.connection() as connection:
            validation = await with_alias_context(
                connection, built.scopes, built.validation, result.output
            )
            validation = replace(
                validation,
                is_negated_predicate_rejected=(
                    self._settings.extraction_reject_negated_predicates
                ),
            )
            plan = validate_output(result.output, validation)
            prepared = await prepare_resolution(
                connection, batch, built, plan, self._settings
            )
        return plan, prepared

    async def _resolve_supersessions(
        self, plan: ValidatedPlan, prepared: PreparedResolution | None
    ) -> tuple[ValidatedPlan, ExtractionUsage]:
        assert self._client is not None
        if prepared is None:
            return plan, ExtractionUsage(input_tokens=0, output_tokens=0)
        resolution = await resolve_with_judge(self._client, prepared, self._settings)
        resolved = plan.model_copy(
            update={
                "supersessions": merge_claims(plan.supersessions, resolution.claims),
                "dropped": {**plan.dropped, **resolution.drops},
            }
        )
        usage = ExtractionUsage(
            input_tokens=resolution.input_tokens,
            output_tokens=resolution.output_tokens,
        )
        return resolved, usage

    async def _store_plan(
        self, batch: ExtractionBatchRow, built: BuiltInput, result: ExtractionResult
    ) -> ExtractionBatchRow | None:
        plan, prepared = await self._validate_and_prepare(batch, built, result)
        plan, judge_usage = await self._resolve_supersessions(plan, prepared)
        input_tokens = result.usage.input_tokens + judge_usage.input_tokens
        output_tokens = result.usage.output_tokens + judge_usage.output_tokens
        async with self._pool.connection() as connection:
            stored = await extraction_batch_repo.record_batch_output(
                connection,
                batch.batch_id,
                result.raw_output,
                plan.model_dump(mode="json"),
                input_tokens,
                output_tokens,
            )
        self._state.counts.input_tokens += input_tokens
        self._state.counts.output_tokens += output_tokens
        self._state.add_drops(plan.dropped)
        return stored

    async def _apply(self, batch: ExtractionBatchRow) -> None:
        outcome = await apply_batch(
            self._pool, batch, self._settings.extraction_max_attempts
        )
        if outcome.is_applied:
            self._state.counts.batches_applied += 1
            self._state.counts.items_applied += outcome.items_applied
        if outcome.is_failed:
            self._state.counts.batches_failed += 1

    async def _release(
        self, batch: ExtractionBatchRow, step: ExtractionStepStatus, code: str | None
    ) -> None:
        async with self._pool.connection() as connection:
            await extraction_batch_repo.release_batch(connection, batch.batch_id)
        self._state.stop(step, code or "extraction_error")

    async def _fail(
        self, batch: ExtractionBatchRow, code: str, *, is_terminal: bool | None = None
    ) -> None:
        limit = self._settings.extraction_max_attempts
        terminal = batch.attempt_count >= limit if is_terminal is None else is_terminal
        async with self._pool.connection() as connection:
            await extraction_batch_repo.mark_batch_failed(
                connection, batch.batch_id, code, terminal
            )
        logger.warning(
            EVENT_BATCH_FAILED,
            batch_id=str(batch.batch_id),
            code=code,
            is_terminal=terminal,
        )
        if terminal:
            self._state.counts.batches_failed += 1


@lru_cache
def _get_queue() -> ExtractionQueue:
    settings = get_settings()
    return ExtractionQueue(
        settings.extraction_worker_count, settings.extraction_stalled_seconds
    )


def get_extraction_queue() -> ExtractionQueue:
    return _get_queue()


@lru_cache
def _get_client() -> ExtractionBackend | None:
    return build_extraction_client(get_settings())


def get_extraction_service() -> ExtractionService:
    return ExtractionService(
        get_pool(),
        get_settings(),
        _get_client(),
        get_extraction_queue(),
        get_retrieval_service(),
    )
