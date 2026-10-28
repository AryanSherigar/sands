"""Finds memory scopes that Core no longer knows about and purges them."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

import structlog
from app.config import settings
from app.integrations import memory_client
from app.models.memory_purge import MemoryScopes
from app.repositories.memory_reconcile_repo import MemoryReconcileRepo
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

ReconcileStatus = Literal["dry_run", "applied", "aborted"]

REASON_EMPTY_LIVE_SET = "empty_core_live_set"
REASON_ORPHAN_SHARE = "orphan_share_over_limit"
MAX_ORPHAN_SHARE = 0.5
EVENT_RECONCILE_PLANNED = "memory_reconcile_planned"
EVENT_RECONCILE_ABORTED = "memory_reconcile_aborted"


@dataclass(frozen=True)
class ReconcilePlan:
    orphan_playthrough_ids: list[uuid.UUID] = field(default_factory=list)
    orphan_scenario_ids: list[uuid.UUID] = field(default_factory=list)
    scope_count: int = 0
    skipped_young_count: int = 0
    live_core_count: int = 0

    @property
    def orphan_count(self) -> int:
        return len(self.orphan_playthrough_ids) + len(self.orphan_scenario_ids)


@dataclass(frozen=True)
class ReconcileResult:
    plan: ReconcilePlan
    status: ReconcileStatus
    reason: str | None = None


def build_plan(
    scopes: MemoryScopes,
    live_playthrough_ids: set[uuid.UUID],
    live_scenario_ids: set[uuid.UUID],
    cutoff: datetime,
) -> ReconcilePlan:
    """Scopes newer than `cutoff` are never orphans: a registration may be in flight."""
    old_playthroughs = [
        item for item in scopes.playthroughs if item.created_at <= cutoff
    ]
    old_templates = [item for item in scopes.templates if item.created_at <= cutoff]
    scenario_ids = dict.fromkeys(
        item.scenario_id
        for item in old_templates
        if item.scenario_id not in live_scenario_ids
    )
    scope_count = len(scopes.playthroughs) + len(scopes.templates)
    return ReconcilePlan(
        orphan_playthrough_ids=[
            item.playthrough_id
            for item in old_playthroughs
            if item.playthrough_id not in live_playthrough_ids
        ],
        orphan_scenario_ids=list(scenario_ids),
        scope_count=scope_count,
        skipped_young_count=scope_count - len(old_playthroughs) - len(old_templates),
        live_core_count=len(live_playthrough_ids) + len(live_scenario_ids),
    )


def find_safety_violation(plan: ReconcilePlan, is_forced: bool) -> str | None:
    """NOTE: --force overrides only the share limit; an empty Core live set while
    memory holds scopes means the id list is wrong, never that everything is orphaned."""
    if plan.live_core_count == 0 and plan.scope_count > 0:
        return REASON_EMPTY_LIVE_SET
    is_over_limit = plan.orphan_count > plan.scope_count * MAX_ORPHAN_SHARE
    if is_over_limit and not is_forced:
        return REASON_ORPHAN_SHARE
    return None


async def reconcile_memory_orphans(
    session: AsyncSession,
    is_apply: bool,
    is_forced: bool,
    now: datetime | None = None,
) -> ReconcileResult:
    """Memory is listed before Core's live ids are read, so a scope that exists in
    memory but was just created in Core is seen as live, never as an orphan."""
    cutoff = (now or datetime.now(UTC)) - timedelta(
        hours=settings.memory_reconcile_min_age_hours
    )
    scopes = await memory_client.list_scopes()
    repo = MemoryReconcileRepo(session)
    plan = build_plan(
        scopes,
        await repo.list_playthrough_ids(),
        await repo.list_scenario_ids(),
        cutoff,
    )
    _log_plan(plan, is_apply)
    if not is_apply:
        return ReconcileResult(plan, "dry_run")
    reason = find_safety_violation(plan, is_forced)
    if reason is not None:
        logger.error(EVENT_RECONCILE_ABORTED, reason=reason)
        return ReconcileResult(plan, "aborted", reason)
    await memory_client.purge(plan.orphan_playthrough_ids, plan.orphan_scenario_ids)
    return ReconcileResult(plan, "applied")


def _log_plan(plan: ReconcilePlan, is_apply: bool) -> None:
    logger.info(
        EVENT_RECONCILE_PLANNED,
        is_apply=is_apply,
        scope_count=plan.scope_count,
        orphan_playthrough_ids=[str(item) for item in plan.orphan_playthrough_ids],
        orphan_scenario_ids=[str(item) for item in plan.orphan_scenario_ids],
        skipped_young_count=plan.skipped_young_count,
    )
