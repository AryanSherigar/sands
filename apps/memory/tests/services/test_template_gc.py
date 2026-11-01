"""Template GC: the sweep step and its wiring into process-pending."""

from uuid import uuid4

import pytest
import structlog
from app.models.process_pending import ProcessPendingRequest
from app.services import template_gc as gc_module
from app.services.indexing_service import IndexingService
from app.services.purge_service import PurgeService
from app.services.template_gc import collect_template_garbage
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from structlog.testing import capture_logs
from tests.services import purge_helpers as helpers
from tests.services.indexing_helpers import FakeEmbedder, make_settings

FAILED_AGE_SECONDS = 86400
OLDER_THAN_AGE = FAILED_AGE_SECONDS + 60
YOUNGER_THAN_AGE = 60


@pytest.fixture
def purge_service(retrieval_pool: AsyncConnectionPool) -> PurgeService:
    return PurgeService(retrieval_pool)


async def _collect(pool: AsyncConnectionPool, service: PurgeService) -> tuple[int, int]:
    result = await collect_template_garbage(pool, service, FAILED_AGE_SECONDS)
    return result.deleted, result.retained


async def test_it_keeps_the_highest_ready_revision_and_deletes_older_ones(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    purge_service: PurgeService,
) -> None:
    scenario_id = uuid4()
    old = await helpers.build_template(db_connection, scenario_id=scenario_id)
    latest = await helpers.build_template(
        db_connection, scenario_id=scenario_id, publish_revision=2
    )
    await db_connection.commit()

    assert await _collect(retrieval_pool, purge_service) == (1, 0)

    assert not await helpers.template_exists(db_connection, old.template_id)
    assert await helpers.template_exists(db_connection, latest.template_id)


async def test_an_older_referenced_template_is_retained(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    purge_service: PurgeService,
) -> None:
    scenario_id = uuid4()
    old = await helpers.build_template(db_connection, scenario_id=scenario_id)
    await helpers.build_template(
        db_connection, scenario_id=scenario_id, publish_revision=2
    )
    await helpers.build_playthrough(db_connection, old)
    await db_connection.commit()

    assert await _collect(retrieval_pool, purge_service) == (0, 1)

    assert await helpers.template_exists(db_connection, old.template_id)


async def test_a_single_ready_template_is_never_collected(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    purge_service: PurgeService,
) -> None:
    only = await helpers.build_template(db_connection)
    await db_connection.commit()

    assert await _collect(retrieval_pool, purge_service) == (0, 0)

    assert await helpers.template_exists(db_connection, only.template_id)


async def test_a_failed_template_goes_only_after_the_age(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    purge_service: PurgeService,
) -> None:
    young = await helpers.build_template(
        db_connection, direct_status="failed", age_seconds=YOUNGER_THAN_AGE
    )
    stale = await helpers.build_template(
        db_connection, direct_status="failed", age_seconds=OLDER_THAN_AGE
    )
    await db_connection.commit()

    assert await _collect(retrieval_pool, purge_service) == (1, 0)

    assert await helpers.template_exists(db_connection, young.template_id)
    assert not await helpers.template_exists(db_connection, stale.template_id)


async def test_a_building_template_younger_than_the_age_is_kept_beside_a_ready_one(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    purge_service: PurgeService,
) -> None:
    scenario_id = uuid4()
    ready = await helpers.build_template(db_connection, scenario_id=scenario_id)
    building = await helpers.build_template(
        db_connection,
        scenario_id=scenario_id,
        publish_revision=2,
        direct_status="building",
        age_seconds=YOUNGER_THAN_AGE,
    )
    await db_connection.commit()

    assert await _collect(retrieval_pool, purge_service) == (0, 0)

    assert await helpers.template_exists(db_connection, ready.template_id)
    assert await helpers.template_exists(db_connection, building.template_id)


async def test_the_unscoped_sweep_collects_but_a_scoped_sweep_does_not(
    db_connection: AsyncConnection, retrieval_pool: AsyncConnectionPool
) -> None:
    scenario_id = uuid4()
    old = await helpers.build_template(db_connection, scenario_id=scenario_id)
    await helpers.build_template(
        db_connection, scenario_id=scenario_id, publish_revision=2
    )
    world = await helpers.build_playthrough(db_connection)
    await db_connection.commit()
    service = IndexingService(retrieval_pool, make_settings(), FakeEmbedder())

    scoped = await service.process_pending(
        ProcessPendingRequest(playthrough_id=world.playthrough_id)
    )
    assert await helpers.template_exists(db_connection, old.template_id)
    assert scoped.counts.templates_gc_deleted == 0

    unscoped = await service.process_pending()
    assert unscoped.counts.templates_gc_deleted == 1
    assert not await helpers.template_exists(db_connection, old.template_id)


async def test_logs_never_contain_template_text(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    purge_service: PurgeService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gc_module, "logger", structlog.get_logger())
    scenario_id = uuid4()
    await helpers.build_template(db_connection, scenario_id=scenario_id)
    await helpers.build_template(
        db_connection, scenario_id=scenario_id, publish_revision=2
    )
    await db_connection.commit()

    with capture_logs() as logs:
        await _collect(retrieval_pool, purge_service)

    assert logs
    assert helpers.CANARY not in str(logs)
