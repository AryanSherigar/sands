"""Idempotent direct write of a published scenario's authored content into a template."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import structlog
from app.config import get_settings
from app.db.pool import get_connection
from app.exceptions.template_exceptions import TemplateContentConflictError
from app.models.common import TemplateEnrichmentStatus
from app.models.evidence import SourceCreate, SpanRow
from app.models.facts import AliasCreate, EntityCreate, FactSourceCreate
from app.models.templates import (
    MasterTemplateContent,
    NewbieTemplateContent,
    TemplateBuildRequest,
    TemplateBuildResponse,
    TemplateCreate,
    TemplateRow,
)
from app.repositories import (
    entity_repo,
    fact_repo,
    source_repo,
    span_repo,
    template_repo,
)
from app.services.entity_tagger import build_alias_index
from app.services.ingest_common import TEMPLATE_SCOPE, sha256_hex, span_from_draft
from app.services.template_master_builder import (
    build_alias_creates,
    build_description_sources,
    build_entity_creates,
    build_fact_plans,
)
from app.services.template_newbie_builder import (
    authored_graph_of,
    build_card_alias_creates,
    build_card_entity_creates,
    build_card_sources,
    build_lore_sources,
)
from app.services.template_plans import FactPlan, SourcePlan, SpanLimits
from app.services.template_validator import validate_template_request
from fastapi import Depends
from psycopg import AsyncConnection

logger = structlog.get_logger()

EVENT_TEMPLATE_BUILT = "template_built"
AUTHORED_SEQUENCE = 0
ENRICHMENT_PENDING: TemplateEnrichmentStatus = "pending"
ENRICHMENT_NOT_NEEDED: TemplateEnrichmentStatus = "not_needed"


@dataclass(frozen=True)
class TemplateBuildResult:
    response: TemplateBuildResponse
    is_created: bool


def _limits() -> SpanLimits:
    settings = get_settings()
    return SpanLimits(settings.span_max_tokens, settings.span_chars_per_token)


def _to_response(row: TemplateRow) -> TemplateBuildResponse:
    return TemplateBuildResponse(
        template_id=row.template_id,
        direct_status=row.direct_status,
        enrichment_status=row.enrichment_status,
    )


def _require_same_content(row: TemplateRow, request: TemplateBuildRequest) -> None:
    if row.content_hash != request.content_hash:
        raise TemplateContentConflictError(
            f"{request.scenario_id} revision {request.publish_revision}"
        )


class TemplateService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def build_template(
        self, request: TemplateBuildRequest
    ) -> TemplateBuildResult:
        """Write the template in one transaction; a repeat of the same revision and
        hash is a no-op, and the same revision with a different hash is a conflict."""
        validate_template_request(request)
        async with self._connection.transaction():
            row, is_inserted = await template_repo.create_template_with_status(
                self._connection, _initial_template(request)
            )
            if is_inserted:
                row = await self._write_content(row, request)
            else:
                _require_same_content(row, request)
        _log_built(row, request, is_inserted)
        return TemplateBuildResult(_to_response(row), is_inserted)

    async def _write_content(
        self, row: TemplateRow, request: TemplateBuildRequest
    ) -> TemplateRow:
        if request.master is not None:
            await self._write_master(row.template_id, request.master)
            return row
        assert request.newbie is not None
        status = await self._write_newbie(row.template_id, request, request.newbie)
        if status == row.enrichment_status:
            return row
        updated = await template_repo.update_template_statuses(
            self._connection, row.template_id, None, status
        )
        assert updated is not None
        return updated

    async def _write_master(
        self, template_id: UUID, content: MasterTemplateContent
    ) -> None:
        limits = _limits()
        entity_ids = await self._create_entities(
            build_entity_creates(template_id, content)
        )
        await entity_repo.add_aliases(
            self._connection, build_alias_creates(template_id, content, entity_ids)
        )
        for plan in build_description_sources(content, entity_ids, limits):
            await self._persist_source(template_id, plan)
        for fact_plan in build_fact_plans(template_id, content, entity_ids, limits):
            await self._persist_fact(template_id, fact_plan)

    async def _write_newbie(
        self,
        template_id: UUID,
        request: TemplateBuildRequest,
        content: NewbieTemplateContent,
    ) -> TemplateEnrichmentStatus:
        scenario_id = request.scenario_id
        graph = authored_graph_of(content)
        entity_ids, aliases = await self._write_newbie_entities(
            template_id, scenario_id, graph, content
        )
        alias_index = build_alias_index(
            [(alias.alias_normalized, alias.entity_id) for alias in aliases]
        )
        limits = _limits()
        plans = [
            *build_description_sources(graph, entity_ids, limits),
            *build_card_sources(scenario_id, content, entity_ids, alias_index, limits),
            *build_lore_sources(content, alias_index, limits),
        ]
        await self._persist_newbie_content(template_id, graph, entity_ids, plans)
        has_spans = any(plan.spans for plan in plans)
        return ENRICHMENT_PENDING if has_spans else ENRICHMENT_NOT_NEEDED

    async def _write_newbie_entities(
        self,
        template_id: UUID,
        scenario_id: UUID,
        graph: MasterTemplateContent,
        content: NewbieTemplateContent,
    ) -> tuple[dict[UUID, UUID], list[AliasCreate]]:
        entity_ids = await self._create_entities(
            [
                *build_entity_creates(template_id, graph),
                *build_card_entity_creates(template_id, scenario_id, content),
            ]
        )
        aliases = [
            *build_alias_creates(template_id, graph, entity_ids),
            *build_card_alias_creates(template_id, scenario_id, content, entity_ids),
        ]
        await entity_repo.add_aliases(self._connection, aliases)
        return entity_ids, aliases

    async def _persist_newbie_content(
        self,
        template_id: UUID,
        graph: MasterTemplateContent,
        entity_ids: dict[UUID, UUID],
        plans: list[SourcePlan],
    ) -> None:
        for plan in plans:
            await self._persist_source(template_id, plan)
        fact_plans = build_fact_plans(template_id, graph, entity_ids, _limits())
        for fact_plan in fact_plans:
            await self._persist_fact(template_id, fact_plan)

    async def _create_entities(self, creates: list[EntityCreate]) -> dict[UUID, UUID]:
        entity_ids: dict[UUID, UUID] = {}
        for create in creates:
            row = await entity_repo.create_entity(self._connection, create)
            assert row.authored_entity_id is not None
            entity_ids[row.authored_entity_id] = row.entity_id
        return entity_ids

    async def _persist_source(
        self, template_id: UUID, plan: SourcePlan
    ) -> list[SpanRow]:
        source = await source_repo.create_source(
            self._connection,
            SourceCreate(
                scope_kind=TEMPLATE_SCOPE,
                scope_id=template_id,
                source_kind=plan.source_kind,
                source_ref=plan.source_ref,
                sequence=AUTHORED_SEQUENCE,
                content=plan.content,
                content_hash=sha256_hex(plan.content),
            ),
        )
        spans = [
            span_from_draft(source, span.draft, span.entity_ids).model_copy(
                update={
                    "is_hidden": span.is_hidden,
                    "conditional": span.conditional,
                    "authored_fact_id": span.authored_fact_id,
                }
            )
            for span in plan.spans
        ]
        return await span_repo.create_spans(self._connection, spans)

    async def _persist_fact(self, template_id: UUID, plan: FactPlan) -> None:
        span_rows = await self._persist_source(template_id, plan.source)
        fact_rows = await fact_repo.create_facts(self._connection, [plan.fact])
        await fact_repo.add_fact_sources(
            self._connection,
            [
                FactSourceCreate(fact_id=fact_rows[0].fact_id, span_id=span.span_id)
                for span in span_rows
            ],
        )


def _initial_template(request: TemplateBuildRequest) -> TemplateCreate:
    return TemplateCreate(
        scenario_id=request.scenario_id,
        publish_revision=request.publish_revision,
        mode=request.mode,
        direct_status="ready",
        enrichment_status=ENRICHMENT_NOT_NEEDED,
        content_hash=request.content_hash,
    )


def _log_built(
    row: TemplateRow, request: TemplateBuildRequest, is_created: bool
) -> None:
    logger.info(
        EVENT_TEMPLATE_BUILT,
        template_id=str(row.template_id),
        scenario_id=str(request.scenario_id),
        publish_revision=request.publish_revision,
        mode=request.mode,
        is_created=is_created,
    )


def get_template_service(
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> TemplateService:
    return TemplateService(connection)
