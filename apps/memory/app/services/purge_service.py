"""Deletes a playthrough's or a scenario's memory scopes, one transaction per scope."""

import time
from typing import Literal
from uuid import UUID

import structlog
from app.db.pool import get_pool
from app.models.common import ScopeKind
from app.models.purge import PurgeRequest, PurgeResponse, ScopesResponse
from app.repositories import (
    embedding_failure_repo,
    embedding_repo,
    entity_repo,
    extraction_batch_repo,
    fact_repo,
    ingest_delivery_repo,
    playthrough_repo,
    source_repo,
    template_repo,
)
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

logger = structlog.get_logger()

EVENT_PURGE_COMPLETED = "memory_purge_completed"
MILLISECONDS_PER_SECOND = 1000

TemplateOutcome = Literal["deleted", "retained", "missing"]


async def delete_scope_rows(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> None:
    """NOTE: failures first (their only link to the scope is the spans and facts), then
    rows by (scope_kind, scope_id) so a shared template entity is never reached by a
    cascade from a playthrough. Aliases are deleted explicitly because a playthrough
    can alias a template entity."""
    await embedding_failure_repo.delete_scope_failures(connection, scope_kind, scope_id)
    await embedding_repo.delete_scope_embeddings(connection, scope_kind, scope_id)
    await fact_repo.delete_scope_facts(connection, scope_kind, scope_id)
    await entity_repo.delete_scope_aliases(connection, scope_kind, scope_id)
    await entity_repo.delete_scope_entities(connection, scope_kind, scope_id)
    await source_repo.delete_scope_sources(connection, scope_kind, scope_id)
    await extraction_batch_repo.delete_scope_batches(connection, scope_kind, scope_id)


class PurgeService:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def purge(self, request: PurgeRequest) -> PurgeResponse:
        """Playthroughs go first so a template they referenced can be deleted by the
        same call. Unknown ids count 0, so a re-run is a no-op."""
        started = time.monotonic()
        playthroughs_purged = 0
        for playthrough_id in dict.fromkeys(request.playthrough_ids):
            if await self.purge_playthrough(playthrough_id):
                playthroughs_purged += 1
        outcomes = await self._purge_scenarios(request.scenario_ids)
        response = PurgeResponse(
            playthroughs_purged=playthroughs_purged,
            templates_purged=outcomes.count("deleted"),
            templates_retained_in_use=outcomes.count("retained"),
        )
        logger.info(
            EVENT_PURGE_COMPLETED,
            **response.model_dump(),
            duration_ms=int((time.monotonic() - started) * MILLISECONDS_PER_SECOND),
        )
        return response

    async def list_scopes(self) -> ScopesResponse:
        async with self._pool.connection() as connection:
            playthroughs = await playthrough_repo.list_playthrough_scopes(connection)
            templates = await template_repo.list_template_scopes(connection)
        return ScopesResponse(playthroughs=playthroughs, templates=templates)

    async def purge_playthrough(self, playthrough_id: UUID) -> bool:
        async with self._pool.connection() as connection, connection.transaction():
            await ingest_delivery_repo.lock_ingestion(connection, playthrough_id)
            await ingest_delivery_repo.mark_purged(connection, playthrough_id)
            if not await playthrough_repo.lock_playthrough_for_update(
                connection, playthrough_id
            ):
                return False
            await delete_scope_rows(connection, "playthrough", playthrough_id)
            return await playthrough_repo.delete_playthrough(connection, playthrough_id)

    async def purge_template(self, template_id: UUID) -> TemplateOutcome:
        async with self._pool.connection() as connection, connection.transaction():
            if not await template_repo.lock_template_for_update(
                connection, template_id
            ):
                return "missing"
            if await playthrough_repo.count_playthroughs_for_template(
                connection, template_id
            ):
                return "retained"
            await delete_scope_rows(connection, "template", template_id)
            await template_repo.delete_template(connection, template_id)
            return "deleted"

    async def _purge_scenarios(self, scenario_ids: list[UUID]) -> list[TemplateOutcome]:
        async with self._pool.connection() as connection:
            template_ids = await template_repo.list_template_ids_for_scenarios(
                connection, list(dict.fromkeys(scenario_ids))
            )
        return [await self.purge_template(template_id) for template_id in template_ids]


def get_purge_service() -> PurgeService:
    return PurgeService(get_pool())
