"""Sweep step: removes unreferenced templates that are no longer a scenario's latest."""

from dataclasses import dataclass

import structlog
from app.repositories import template_repo
from app.services.purge_service import PurgeService
from psycopg_pool import AsyncConnectionPool

logger = structlog.get_logger()

EVENT_TEMPLATE_GC_COMPLETED = "template_gc_completed"


@dataclass(frozen=True)
class TemplateGcResult:
    deleted: int = 0
    retained: int = 0


async def collect_template_garbage(
    pool: AsyncConnectionPool, purge_service: PurgeService, failed_age_seconds: int
) -> TemplateGcResult:
    """NOTE: "latest" is memory's highest ready revision per scenario, not Core's value.
    A template that is not ready is only a candidate once it is older than the age."""
    async with pool.connection() as connection:
        candidates = await template_repo.list_gc_candidates(
            connection, failed_age_seconds
        )
    outcomes = [
        "retained"
        if candidate.is_referenced
        else await purge_service.purge_template(candidate.template_id)
        for candidate in candidates
    ]
    result = TemplateGcResult(
        deleted=outcomes.count("deleted"), retained=outcomes.count("retained")
    )
    logger.info(
        EVENT_TEMPLATE_GC_COMPLETED, deleted=result.deleted, retained=result.retained
    )
    return result
