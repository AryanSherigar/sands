"""Rebuilds memory templates for scenarios published before the new memory
service existed (template-publish task 5)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

import structlog
from app.db.models.scenario import Scenario
from app.exceptions.memory_exceptions import MemoryTemplateBuildError
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.map_repo import MapRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.memory_template_service import push_template
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

RebuildStatus = Literal["would_build", "built", "unchanged", "skipped_drift", "failed"]

CODE_CONTENT_CONFLICT = "template_content_conflict"
FIRST_REVISION = 1
EVENT_TEMPLATE_REBUILD_RESULT = "memory_template_rebuild_result"


@dataclass(frozen=True)
class RebuildResult:
    scenario_id: uuid.UUID
    revision: int
    status: RebuildStatus


async def rebuild_all_templates(
    session: AsyncSession, is_dry_run: bool
) -> list[RebuildResult]:
    """Each scenario commits on its own, so one failure never rolls back the rest."""
    scenarios = await ScenarioRepo(session).list_published_for_memory_rebuild()
    results = [
        await rebuild_scenario_template(session, scenario, is_dry_run)
        for scenario in scenarios
    ]
    for result in results:
        logger.info(
            EVENT_TEMPLATE_REBUILD_RESULT,
            scenario_id=str(result.scenario_id),
            revision=result.revision,
            status=result.status,
        )
    return results


async def rebuild_scenario_template(
    session: AsyncSession, scenario: Scenario, is_dry_run: bool
) -> RebuildResult:
    """A scenario still at revision 0 is built as revision 1 and bumped after
    memory confirms. A memory 409 means the authored content changed since the
    revision was published, so the scenario is skipped rather than overwritten."""
    revision = max(scenario.publish_revision, FIRST_REVISION)
    if is_dry_run:
        return RebuildResult(scenario.scenario_id, revision, "would_build")
    try:
        outcome = await push_template(
            scenario,
            revision,
            EntityRepo(session),
            FactRepo(session),
            MapRepo(session),
        )
    except MemoryTemplateBuildError as exc:
        status: RebuildStatus = (
            "skipped_drift" if exc.code == CODE_CONTENT_CONFLICT else "failed"
        )
        return RebuildResult(scenario.scenario_id, revision, status)
    await _pin_revision(session, scenario, revision)
    status = "built" if outcome.was_created else "unchanged"
    return RebuildResult(scenario.scenario_id, revision, status)


async def _pin_revision(
    session: AsyncSession, scenario: Scenario, revision: int
) -> None:
    if scenario.publish_revision >= revision:
        return
    scenario.publish_revision = revision
    await session.commit()
