"""Relay claim recovery and pool availability against real PostgreSQL."""

import asyncio
from datetime import timedelta

import pytest
from app.db.models.memory_relay_claim import MemoryRelayClaim
from app.exceptions.memory_exceptions import MemoryIngestError
from app.integrations import memory_client
from app.models.memory_ingest import IngestResponse
from app.services.memory_relay_service import MemoryRelayService
from memory_outbox_factories import (
    add_register_row,
    add_turn,
    reload_rows,
    seed_playthrough,
)
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _ok(request):
    return IngestResponse(
        playthrough_id=request.playthrough_id,
        ingested_seq=0,
        latest_seq_seen=0,
        items=[
            {
                "item_kind": item.item_kind,
                "sequence": item.sequence,
                "outcome": "applied",
            }
            for item in request.items
        ],
    )


async def test_relay_http_releases_one_connection_pool(
    db_session, test_engine, monkeypatch
):
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    engine = create_async_engine(
        test_engine.url, pool_size=1, max_overflow=0, pool_timeout=0.2
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    relay = MemoryRelayService(factory)
    paused, resume = asyncio.Event(), asyncio.Event()

    async def ingest(request):
        paused.set()
        await resume.wait()
        return _ok(request)

    monkeypatch.setattr(memory_client, "ingest_items", ingest)
    task = asyncio.create_task(relay.deliver_playthrough(seeded.playthrough_id))
    try:
        await asyncio.wait_for(paused.wait(), 5)
        assert engine.pool.checkedout() == 0
        async with factory() as session:
            assert await session.scalar(select(1)) == 1
        assert (
            await relay.deliver_playthrough(seeded.playthrough_id)
        ).playthroughs_attempted == 0
        resume.set()
        assert (await task).rows_delivered == 1
    finally:
        resume.set()
        await asyncio.gather(task, return_exceptions=True)
        await engine.dispose()


async def test_expired_claim_reuses_payload_and_fences_old_owner(
    db_session, test_engine
):
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    relay = MemoryRelayService(factory)
    old, _ = await relay._claim_batch(seeded.playthrough_id)
    assert old is not None
    await add_turn(db_session, seeded, 1)
    await db_session.execute(
        update(MemoryRelayClaim)
        .where(MemoryRelayClaim.playthrough_id == seeded.playthrough_id)
        .values(lease_expires_at=func.now() - timedelta(seconds=1))
    )
    await db_session.commit()
    new, _ = await relay._claim_batch(seeded.playthrough_id)
    assert new is not None
    assert old.request == new.request
    assert old.ownership_token != new.ownership_token
    assert (await relay._finalize_batch(old, None)).rows_delivered == 0
    assert (await relay._finalize_batch(new, None)).rows_delivered == 1
    rows = await reload_rows(db_session, seeded)
    assert rows[0].delivered_at is not None
    assert rows[1].delivered_at is None


async def test_failed_batch_retry_retains_delivery_id(
    db_session, test_engine, monkeypatch
):
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    relay = MemoryRelayService(async_sessionmaker(test_engine, expire_on_commit=False))
    requests = []

    async def ingest(request):
        requests.append(request)
        if len(requests) == 1:
            raise MemoryIngestError("unavailable", upstream_status=503)
        return _ok(request)

    monkeypatch.setattr(memory_client, "ingest_items", ingest)
    assert (await relay.deliver_playthrough(seeded.playthrough_id)).rows_failed == 1
    await add_turn(db_session, seeded, 1)
    assert (await relay.deliver_playthrough(seeded.playthrough_id)).rows_delivered == 1
    assert requests[0] == requests[1]
    assert requests[0].delivery_id is not None
    assert (await relay.deliver_playthrough(seeded.playthrough_id)).rows_delivered == 1
    assert requests[2].delivery_id != requests[0].delivery_id


async def test_remote_success_before_ack_failure_is_retried_as_same_delivery(
    db_session, test_engine, monkeypatch
):
    from sqlalchemy.exc import SQLAlchemyError

    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    relay = MemoryRelayService(async_sessionmaker(test_engine, expire_on_commit=False))
    requests = []
    finalize = relay._finalize_batch

    async def ingest(request):
        requests.append(request)
        return _ok(request)

    async def broken_ack(*args):
        raise SQLAlchemyError("lost connection before acknowledgement")

    monkeypatch.setattr(memory_client, "ingest_items", ingest)
    monkeypatch.setattr(relay, "_finalize_batch", broken_ack)
    with pytest.raises(SQLAlchemyError):
        await relay.deliver_playthrough(seeded.playthrough_id)
    assert (await reload_rows(db_session, seeded))[0].delivered_at is None
    await db_session.execute(
        update(MemoryRelayClaim)
        .where(MemoryRelayClaim.playthrough_id == seeded.playthrough_id)
        .values(lease_expires_at=func.now() - timedelta(seconds=1))
    )
    await db_session.commit()
    monkeypatch.setattr(relay, "_finalize_batch", finalize)
    assert (await relay.deliver_playthrough(seeded.playthrough_id)).rows_delivered == 1
    assert requests[0] == requests[1]
