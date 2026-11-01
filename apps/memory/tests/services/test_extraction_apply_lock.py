"""The apply guard reads the scope row under a share lock, so a purge cannot interleave."""

import asyncio

from app.models.jobs import ExtractionBatchRow
from app.repositories import extraction_batch_repo, playthrough_repo, template_repo
from app.services import extraction_apply
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services import purge_helpers as helpers

LOCK_WAIT_SECONDS = 0.3


async def _batch_of(
    connection: AsyncConnection, scope_id: object
) -> ExtractionBatchRow:
    cursor = await connection.execute(
        "SELECT batch_id FROM memory_extraction_batch WHERE scope_id = %s", (scope_id,)
    )
    row = await cursor.fetchone()
    assert row is not None
    batch = await extraction_batch_repo.get_batch(connection, row[0])
    assert batch is not None
    return batch


async def test_apply_waits_for_a_purge_and_then_sees_the_scope_gone(
    db_connection: AsyncConnection, retrieval_pool: AsyncConnectionPool
) -> None:
    world = await helpers.build_playthrough(db_connection)
    await db_connection.commit()
    batch = await _batch_of(db_connection, world.playthrough_id)
    async with (
        retrieval_pool.connection() as purger,
        retrieval_pool.connection() as applier,
    ):
        await purger.execute("BEGIN")
        assert await playthrough_repo.lock_playthrough_for_update(
            purger, world.playthrough_id
        )
        await applier.execute("BEGIN")
        apply_task = asyncio.create_task(extraction_apply._scope_exists(applier, batch))
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        assert not apply_task.done()
        await playthrough_repo.delete_playthrough(purger, world.playthrough_id)
        await purger.execute("COMMIT")

        assert await asyncio.wait_for(apply_task, timeout=5) is False
        await applier.execute("ROLLBACK")


async def test_a_template_scope_is_locked_the_same_way(
    db_connection: AsyncConnection, retrieval_pool: AsyncConnectionPool
) -> None:
    template = await helpers.build_template(db_connection)
    await db_connection.commit()
    batch = await _batch_of(db_connection, template.template_id)
    async with (
        retrieval_pool.connection() as purger,
        retrieval_pool.connection() as applier,
    ):
        await purger.execute("BEGIN")
        assert await template_repo.lock_template_for_update(
            purger, template.template_id
        )
        await applier.execute("BEGIN")
        apply_task = asyncio.create_task(extraction_apply._scope_exists(applier, batch))
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        assert not apply_task.done()
        await purger.execute("ROLLBACK")

        assert await asyncio.wait_for(apply_task, timeout=5) is True
        await applier.execute("ROLLBACK")
