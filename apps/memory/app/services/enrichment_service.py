"""Newbie template enrichment: chunked extraction over lore and card spans."""

from uuid import UUID

import structlog
from app.config import Settings
from app.models.evidence import SpanRow
from app.models.facts import EntityRow
from app.models.jobs import ExtractionBatchCreate, ExtractionBatchRow
from app.models.templates import TemplateRow
from app.repositories import (
    entity_repo,
    extraction_batch_repo,
    span_repo,
    template_repo,
)
from app.services.extraction_input import (
    BuiltInput,
    render_roster,
    render_user_content,
)
from app.services.extraction_validator import ValidationContext
from app.services.ingest_common import TEMPLATE_SCOPE, sha256_hex
from psycopg import AsyncConnection

ENRICHMENT_OVER_CAP = "enrichment_over_cap"
ENRICHMENT_BATCH_FAILED = "enrichment_batch_failed"
EVENT_ENRICHMENT_STARTED = "enrichment_started"
EVENT_ENRICHMENT_FINISHED = "enrichment_finished"
NO_CONTEXT = "(none)"

logger = structlog.get_logger()


def chunk_spans(spans: list[SpanRow], chunk_tokens: int) -> list[list[SpanRow]]:
    """Greedy, in order. A span larger than the chunk budget forms its own chunk."""
    chunks: list[list[SpanRow]] = []
    current: list[SpanRow] = []
    used = 0
    for span in spans:
        if current and used + span.token_count > chunk_tokens:
            chunks.append(current)
            current, used = [], 0
        current.append(span)
        used += span.token_count
    if current:
        chunks.append(current)
    return chunks


def _placeholder_hash(template_id: UUID, chunk_number: int) -> str:
    return sha256_hex(f"{template_id}:{chunk_number}:unbuilt")


def _chunk_batch(
    template_id: UUID, chunk_number: int, settings: Settings
) -> ExtractionBatchCreate:
    return ExtractionBatchCreate(
        scope_kind=TEMPLATE_SCOPE,
        scope_id=template_id,
        from_seq=chunk_number,
        to_seq=chunk_number,
        status="pending",
        model=settings.extraction_model_name,
        prompt_version=settings.extraction_prompt_version,
        input_hash=_placeholder_hash(template_id, chunk_number),
    )


async def _start_template(
    connection: AsyncConnection, template: TemplateRow, settings: Settings
) -> int:
    spans = await span_repo.list_template_spans_in_order(
        connection, template.template_id
    )
    if sum(span.token_count for span in spans) > settings.enrichment_max_input_tokens:
        await template_repo.set_enrichment_status(
            connection, template.template_id, "failed", ENRICHMENT_OVER_CAP
        )
        logger.warning(ENRICHMENT_OVER_CAP, template_id=str(template.template_id))
        return 0
    chunks = chunk_spans(spans, settings.enrichment_chunk_tokens)
    for number in range(1, len(chunks) + 1):
        await extraction_batch_repo.create_batch(
            connection, _chunk_batch(template.template_id, number, settings)
        )
    status = "running" if chunks else "ready"
    await template_repo.set_enrichment_status(
        connection, template.template_id, status, None
    )
    logger.info(
        EVENT_ENRICHMENT_STARTED,
        template_id=str(template.template_id),
        chunks=len(chunks),
    )
    return len(chunks)


async def create_enrichment_batches(
    connection: AsyncConnection, settings: Settings
) -> int:
    """Master templates are never enriched: the direct write sets them `not_needed`."""
    pending = await template_repo.list_templates_by_enrichment_status(
        connection, ["pending"]
    )
    created = 0
    for template in pending:
        created += await _start_template(connection, template, settings)
    return created


async def finalize_enrichment(connection: AsyncConnection) -> None:
    running = await template_repo.list_templates_by_enrichment_status(
        connection, ["running"]
    )
    for template in running:
        batches = await extraction_batch_repo.list_batches(
            connection, TEMPLATE_SCOPE, template.template_id, None
        )
        await _settle_template(connection, template, batches)


async def _settle_template(
    connection: AsyncConnection,
    template: TemplateRow,
    batches: list[ExtractionBatchRow],
) -> None:
    if any(batch.status == "failed" for batch in batches):
        await template_repo.set_enrichment_status(
            connection, template.template_id, "failed", ENRICHMENT_BATCH_FAILED
        )
    elif batches and all(batch.status == "applied" for batch in batches):
        await template_repo.set_enrichment_status(
            connection, template.template_id, "ready", None
        )
    else:
        return
    logger.info(EVENT_ENRICHMENT_FINISHED, template_id=str(template.template_id))


def _render_source_text(spans: list[SpanRow]) -> str:
    lines = [f"{span.label} {span.text}" for span in spans]
    return "### Lore and story cards (no actor)\n" + "\n".join(lines)


def _template_validation(
    chunk: list[SpanRow], roster: list[EntityRow]
) -> ValidationContext:
    return ValidationContext(
        batch_labels=frozenset(span.label for span in chunk),
        roster_entity_ids=frozenset(str(entity.entity_id) for entity in roster),
        supersedable_fact_ids=frozenset(),
        open_commitment_ids=frozenset(),
        tracked_predicates=frozenset(),
        rejected_targets=frozenset(),
        is_template_scope=True,
    )


async def _chunk_roster(
    connection: AsyncConnection,
    template_id: UUID,
    chunk: list[SpanRow],
    cap: int,
) -> list[EntityRow]:
    mentioned = list(
        dict.fromkeys(entity_id for span in chunk for entity_id in span.entity_ids)
    )
    return await entity_repo.get_entities(
        connection, [(TEMPLATE_SCOPE, template_id)], mentioned[:cap]
    )


async def build_template_input(
    connection: AsyncConnection, batch: ExtractionBatchRow, settings: Settings
) -> BuiltInput | None:
    """None when the chunk no longer exists (the template changed under the batch)."""
    spans = await span_repo.list_template_spans_in_order(connection, batch.scope_id)
    chunks = chunk_spans(spans, settings.enrichment_chunk_tokens)
    if batch.from_seq > len(chunks):
        return None
    chunk = chunks[batch.from_seq - 1]
    roster = await _chunk_roster(
        connection, batch.scope_id, chunk, settings.extraction_roster_cap
    )
    user_content = render_user_content(
        turns=_render_source_text(chunk),
        context=NO_CONTEXT,
        roster=render_roster(roster),
        tracked=NO_CONTEXT,
        scene=NO_CONTEXT,
    )
    return BuiltInput(
        user_content=user_content,
        validation=_template_validation(chunk, roster),
        spans_by_label={span.label: span for span in chunk},
        input_hash=sha256_hex(f"{batch.model}:{batch.prompt_version}:{user_content}"),
        scopes=[(TEMPLATE_SCOPE, batch.scope_id)],
    )
