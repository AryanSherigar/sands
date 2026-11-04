"""Tests for app/services/memory_reconcile_service.py."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from app.config import settings
from app.models.memory_purge import (
    MemoryPurgeResult,
    MemoryScopes,
    PlaythroughScope,
    TemplateScope,
)
from app.repositories.memory_reconcile_repo import MemoryReconcileRepo
from app.services.memory_reconcile_service import (
    REASON_EMPTY_LIVE_SET,
    REASON_ORPHAN_SHARE,
    ReconcilePlan,
    build_plan,
    find_safety_violation,
    reconcile_memory_orphans,
)
from tests.stats_factories import add_playthrough, make_scenario, make_user

NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
OLD = NOW - timedelta(hours=settings.memory_reconcile_min_age_hours + 1)
YOUNG = NOW - timedelta(hours=1)
CUTOFF = NOW - timedelta(hours=settings.memory_reconcile_min_age_hours)


def _playthrough_scope(playthrough_id: uuid.UUID, created_at: datetime = OLD):
    return PlaythroughScope(playthrough_id=playthrough_id, created_at=created_at)


def _template_scope(scenario_id: uuid.UUID, revision: int = 1, created_at=OLD):
    return TemplateScope(
        template_id=uuid.uuid4(),
        scenario_id=scenario_id,
        publish_revision=revision,
        created_at=created_at,
    )


@pytest.fixture
def memory_calls():
    with (
        patch(
            "app.services.memory_reconcile_service.memory_client.list_scopes",
            new_callable=AsyncMock,
        ) as list_scopes,
        patch(
            "app.services.memory_reconcile_service.memory_client.purge",
            new_callable=AsyncMock,
            return_value=MemoryPurgeResult(),
        ) as purge,
    ):
        yield list_scopes, purge


def test_build_plan_finds_orphans_and_skips_young_scopes() -> None:
    live_playthrough, orphan_playthrough, young_orphan = (
        uuid.uuid4() for _ in range(3)
    )
    live_scenario, orphan_scenario, young_scenario = (uuid.uuid4() for _ in range(3))
    scopes = MemoryScopes(
        playthroughs=[
            _playthrough_scope(live_playthrough),
            _playthrough_scope(orphan_playthrough),
            _playthrough_scope(young_orphan, YOUNG),
        ],
        templates=[
            _template_scope(live_scenario),
            _template_scope(orphan_scenario, 1),
            _template_scope(orphan_scenario, 2),
            _template_scope(young_scenario, created_at=YOUNG),
        ],
    )

    plan = build_plan(scopes, {live_playthrough}, {live_scenario}, CUTOFF)

    assert plan.orphan_playthrough_ids == [orphan_playthrough]
    assert plan.orphan_scenario_ids == [orphan_scenario]
    assert plan.scope_count == 7
    assert plan.skipped_young_count == 2


def test_an_empty_live_set_is_never_overridable() -> None:
    plan = ReconcilePlan(
        orphan_playthrough_ids=[uuid.uuid4()], scope_count=1, live_core_count=0
    )

    assert find_safety_violation(plan, is_forced=False) == REASON_EMPTY_LIVE_SET
    assert find_safety_violation(plan, is_forced=True) == REASON_EMPTY_LIVE_SET


def test_more_than_half_orphans_needs_force() -> None:
    plan = ReconcilePlan(
        orphan_playthrough_ids=[uuid.uuid4(), uuid.uuid4(), uuid.uuid4()],
        scope_count=5,
        live_core_count=2,
    )

    assert find_safety_violation(plan, is_forced=False) == REASON_ORPHAN_SHARE
    assert find_safety_violation(plan, is_forced=True) is None


def test_exactly_half_orphans_is_allowed() -> None:
    plan = ReconcilePlan(
        orphan_playthrough_ids=[uuid.uuid4()], scope_count=2, live_core_count=1
    )

    assert find_safety_violation(plan, is_forced=False) is None


@pytest.mark.asyncio
async def test_dry_run_plans_but_never_purges(db_session, memory_calls) -> None:
    list_scopes, purge = memory_calls
    list_scopes.return_value = MemoryScopes(
        playthroughs=[_playthrough_scope(uuid.uuid4())], templates=[]
    )
    owner = await make_user(db_session)
    await make_scenario(db_session, owner)

    result = await reconcile_memory_orphans(
        db_session, is_apply=False, is_forced=False, now=NOW
    )

    assert result.status == "dry_run"
    assert len(result.plan.orphan_playthrough_ids) == 1
    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_purges_only_the_orphans(db_session, memory_calls) -> None:
    list_scopes, purge = memory_calls
    owner = await make_user(db_session)
    scenario = await make_scenario(db_session, owner)
    kept = await add_playthrough(db_session, scenario, owner)
    orphan_playthrough, orphan_scenario = uuid.uuid4(), uuid.uuid4()
    list_scopes.return_value = MemoryScopes(
        playthroughs=[
            _playthrough_scope(kept.playthrough_id),
            _playthrough_scope(orphan_playthrough),
        ],
        templates=[
            _template_scope(scenario.scenario_id),
            _template_scope(orphan_scenario),
        ],
    )

    result = await reconcile_memory_orphans(
        db_session, is_apply=True, is_forced=True, now=NOW
    )

    assert result.status == "applied"
    purge.assert_awaited_once_with([orphan_playthrough], [orphan_scenario])


@pytest.mark.asyncio
async def test_apply_aborts_without_purging_when_core_has_no_live_ids(
    db_session, memory_calls
) -> None:
    list_scopes, purge = memory_calls
    list_scopes.return_value = MemoryScopes(
        playthroughs=[_playthrough_scope(uuid.uuid4())], templates=[]
    )

    with (
        patch.object(
            MemoryReconcileRepo,
            "list_playthrough_ids",
            AsyncMock(return_value=set()),
        ),
        patch.object(
            MemoryReconcileRepo, "list_scenario_ids", AsyncMock(return_value=set())
        ),
    ):
        result = await reconcile_memory_orphans(
            db_session, is_apply=True, is_forced=True, now=NOW
        )

    assert (result.status, result.reason) == ("aborted", REASON_EMPTY_LIVE_SET)
    purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_aborts_when_most_scopes_are_orphans_without_force(
    db_session, memory_calls
) -> None:
    list_scopes, purge = memory_calls
    owner = await make_user(db_session)
    await make_scenario(db_session, owner)
    list_scopes.return_value = MemoryScopes(
        playthroughs=[_playthrough_scope(uuid.uuid4()) for _ in range(3)],
        templates=[],
    )

    refused = await reconcile_memory_orphans(
        db_session, is_apply=True, is_forced=False, now=NOW
    )
    forced = await reconcile_memory_orphans(
        db_session, is_apply=True, is_forced=True, now=NOW
    )

    assert (refused.status, refused.reason) == ("aborted", REASON_ORPHAN_SHARE)
    assert forced.status == "applied"
    assert purge.await_count == 1
