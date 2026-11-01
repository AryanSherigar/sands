"""PurgeService over a real pool: whole-scope deletes, retained templates, idempotence."""

import asyncio
from uuid import uuid4

import pytest
import structlog
from app.models.purge import PurgeRequest
from app.repositories import playthrough_repo
from app.services import purge_service as purge_module
from app.services.purge_service import PurgeService
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from structlog.testing import capture_logs
from tests.services import purge_helpers as helpers

LOCK_WAIT_SECONDS = 0.3


@pytest.fixture
def service(retrieval_pool: AsyncConnectionPool) -> PurgeService:
    return PurgeService(retrieval_pool)


async def _blocked_statement(connection: AsyncConnection) -> str:
    """NOTE: the purge must wait at the lock, before it deletes anything; waiting at its
    final DELETE would let an apply write rows the purge already swept past."""
    cursor = await connection.execute(
        "SELECT query FROM pg_stat_activity WHERE wait_event_type = 'Lock' "
        "AND datname = current_database()"
    )
    queries = [row[0] for row in await cursor.fetchall()]
    assert len(queries) == 1
    return "FOR UPDATE" if "FOR UPDATE" in queries[0] else queries[0]


def _nonzero(counts: dict[str, int]) -> dict[str, int]:
    return {name: count for name, count in counts.items() if count}


async def test_purging_a_lone_playthrough_leaves_no_rows(
    db_connection: AsyncConnection, service: PurgeService
) -> None:
    world = await helpers.build_playthrough(db_connection)
    await db_connection.commit()
    before = await helpers.table_counts(db_connection)
    assert before["memory_fact"] and before["memory_embedding"]

    response = await service.purge(PurgeRequest(playthrough_ids=[world.playthrough_id]))

    assert response.playthroughs_purged == 1
    assert _nonzero(await helpers.table_counts(db_connection)) == {
        "memory_purged_playthrough": 1,
        helpers.MODEL_TABLE: 1,
        helpers.FAILURE_TABLE: helpers.UNRELATED_FAILURES_PER_BUILD,
    }


async def test_purging_one_playthrough_keeps_the_template_and_the_others(
    db_connection: AsyncConnection, service: PurgeService
) -> None:
    template = await helpers.build_template(db_connection)
    await helpers.build_playthrough(db_connection, template)
    await db_connection.commit()
    baseline = await helpers.table_counts(db_connection)
    doomed = await helpers.build_playthrough(db_connection, template)
    await db_connection.commit()

    await service.purge(PurgeRequest(playthrough_ids=[doomed.playthrough_id]))

    after = await helpers.table_counts(db_connection)
    baseline["memory_purged_playthrough"] += 1
    baseline[helpers.FAILURE_TABLE] += helpers.UNRELATED_FAILURES_PER_BUILD
    assert after == baseline
    assert await helpers.template_exists(db_connection, template.template_id)


async def test_a_template_entity_survives_a_playthrough_purge(
    db_connection: AsyncConnection, service: PurgeService
) -> None:
    template = await helpers.build_template(db_connection)
    world = await helpers.build_playthrough(db_connection, template)
    await db_connection.commit()

    await service.purge(PurgeRequest(playthrough_ids=[world.playthrough_id]))

    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_fact WHERE fact_id = %s", (template.fact_id,)
    )
    assert await cursor.fetchone() == (1,)
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_entity WHERE entity_id = %s",
        (template.entity_id,),
    )
    assert await cursor.fetchone() == (1,)


async def test_a_second_purge_and_unknown_ids_are_noops(
    db_connection: AsyncConnection, service: PurgeService
) -> None:
    world = await helpers.build_playthrough(db_connection)
    await db_connection.commit()
    request = PurgeRequest(
        playthrough_ids=[world.playthrough_id, uuid4()], scenario_ids=[uuid4()]
    )

    first = await service.purge(request)
    after_first = await helpers.table_counts(db_connection)
    second = await service.purge(request)

    assert first.model_dump() == {
        "playthroughs_purged": 1,
        "templates_purged": 0,
        "templates_retained_in_use": 0,
    }
    assert second.model_dump() == dict.fromkeys(first.model_dump(), 0)
    assert await helpers.table_counts(db_connection) == after_first


async def test_a_scenario_purge_deletes_every_unreferenced_revision(
    db_connection: AsyncConnection, service: PurgeService
) -> None:
    scenario_id = uuid4()
    first = await helpers.build_template(db_connection, scenario_id=scenario_id)
    second = await helpers.build_template(
        db_connection, scenario_id=scenario_id, publish_revision=2
    )
    await db_connection.commit()

    response = await service.purge(PurgeRequest(scenario_ids=[scenario_id]))

    assert response.templates_purged == 2
    assert not await helpers.template_exists(db_connection, first.template_id)
    assert not await helpers.template_exists(db_connection, second.template_id)
    assert _nonzero(await helpers.table_counts(db_connection)) == {
        helpers.MODEL_TABLE: 1,
        helpers.FAILURE_TABLE: 2 * helpers.UNRELATED_FAILURES_PER_BUILD,
    }


async def test_a_referenced_template_is_retained(
    db_connection: AsyncConnection, service: PurgeService
) -> None:
    template = await helpers.build_template(db_connection)
    await helpers.build_playthrough(db_connection, template)
    await db_connection.commit()
    before = await helpers.table_counts(db_connection)

    response = await service.purge(PurgeRequest(scenario_ids=[template.scenario_id]))

    assert response.templates_retained_in_use == 1
    assert response.templates_purged == 0
    assert await helpers.table_counts(db_connection) == before


async def test_one_request_frees_a_template_by_purging_its_playthrough_first(
    db_connection: AsyncConnection, service: PurgeService
) -> None:
    template = await helpers.build_template(db_connection)
    world = await helpers.build_playthrough(db_connection, template)
    await db_connection.commit()

    response = await service.purge(
        PurgeRequest(
            playthrough_ids=[world.playthrough_id],
            scenario_ids=[template.scenario_id],
        )
    )

    assert (response.playthroughs_purged, response.templates_purged) == (1, 1)
    assert not await helpers.template_exists(db_connection, template.template_id)


async def test_a_purge_waits_for_an_in_flight_apply_holding_the_share_lock(
    db_connection: AsyncConnection,
    service: PurgeService,
    retrieval_pool: AsyncConnectionPool,
) -> None:
    world = await helpers.build_playthrough(db_connection)
    await db_connection.commit()
    request = PurgeRequest(playthrough_ids=[world.playthrough_id])
    async with retrieval_pool.connection() as applier:
        await applier.execute("BEGIN")
        assert await playthrough_repo.lock_playthrough_for_share(
            applier, world.playthrough_id
        )
        purge_task = asyncio.create_task(service.purge(request))
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        assert not purge_task.done()
        assert await _blocked_statement(db_connection) == "FOR UPDATE"
        await applier.execute("COMMIT")
        response = await asyncio.wait_for(purge_task, timeout=5)

    assert response.playthroughs_purged == 1
    async with retrieval_pool.connection() as late_applier:
        assert not await playthrough_repo.lock_playthrough_for_share(
            late_applier, world.playthrough_id
        )


async def test_logs_never_contain_scope_text(
    db_connection: AsyncConnection,
    service: PurgeService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(purge_module, "logger", structlog.get_logger())
    template = await helpers.build_template(db_connection)
    world = await helpers.build_playthrough(db_connection, template)
    await db_connection.commit()

    with capture_logs() as logs:
        await service.purge(
            PurgeRequest(
                playthrough_ids=[world.playthrough_id],
                scenario_ids=[template.scenario_id],
            )
        )

    assert logs
    assert helpers.CANARY not in str(logs)
