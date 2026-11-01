"""Transactional apply of a stored validated plan, with the purge guard."""

from dataclasses import dataclass

import psycopg
import structlog
from app.models.extraction import ValidatedPlan
from app.models.jobs import ExtractionBatchRow
from app.repositories import (
    extraction_batch_repo,
    playthrough_repo,
    span_repo,
    template_repo,
)
from app.services.extraction_applier import ApplyInput, apply_plan
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

SCOPE_PURGED = "scope_purged"
EVENT_APPLY_FAILED = "extraction_apply_failed"
EVENT_APPLY_DISCARDED = "extraction_apply_discarded"

logger = structlog.get_logger()


@dataclass(frozen=True)
class ApplyOutcome:
    items_applied: int = 0
    is_applied: bool = False
    is_purged: bool = False
    is_failed: bool = False


def _evidence_labels(plan: ValidatedPlan) -> list[str]:
    labelled = [
        *plan.new_entities,
        *plan.facts,
        *plan.supersessions,
        *plan.new_commitments,
        *plan.commitment_updates,
    ]
    labels = [label for item in labelled for label in item.evidence]
    if plan.scene is not None:
        labels.extend(plan.scene.evidence)
    return list(dict.fromkeys(labels))


async def _scope_exists(connection: AsyncConnection, batch: ExtractionBatchRow) -> bool:
    """NOTE: the share lock makes a concurrent purge wait for this apply to commit."""
    if batch.scope_kind == "playthrough":
        return await playthrough_repo.lock_playthrough_for_share(
            connection, batch.scope_id
        )
    return await template_repo.lock_template_for_share(connection, batch.scope_id)


async def _apply_in_transaction(
    connection: AsyncConnection, batch: ExtractionBatchRow
) -> ApplyOutcome:
    if not await _scope_exists(connection, batch):
        await extraction_batch_repo.mark_batch_applied_with_note(
            connection, batch.batch_id, SCOPE_PURGED
        )
        return ApplyOutcome(is_purged=True)
    plan = ValidatedPlan.model_validate(batch.validated_plan)
    spans = await span_repo.list_spans_by_labels(
        connection, batch.scope_kind, batch.scope_id, _evidence_labels(plan)
    )
    by_label = {span.label: span for span in spans}
    items = await apply_plan(connection, ApplyInput(batch, plan, by_label))
    if batch.scope_kind == "playthrough":
        await playthrough_repo.advance_watermarks(
            connection, batch.scope_id, extracted_seq=batch.to_seq
        )
    await extraction_batch_repo.mark_batch_applied(connection, batch.batch_id)
    return ApplyOutcome(items_applied=items, is_applied=True)


async def apply_batch(
    pool: AsyncConnectionPool, batch: ExtractionBatchRow, max_attempts: int
) -> ApplyOutcome:
    """Applies the stored plan in one transaction. A failure leaves the batch
    `extracted` for the next sweep (or `failed` at the attempt limit); the model is
    never called again."""
    try:
        async with pool.connection() as connection, connection.transaction():
            return await _apply_in_transaction(connection, batch)
    except (psycopg.Error, ValueError, KeyError, RuntimeError, AssertionError) as error:
        logger.error(
            EVENT_APPLY_FAILED,
            batch_id=str(batch.batch_id),
            error_class=type(error).__name__,
        )
    async with pool.connection() as connection:
        await extraction_batch_repo.record_apply_failure(
            connection, batch.batch_id, max_attempts
        )
    return ApplyOutcome(is_failed=True)
