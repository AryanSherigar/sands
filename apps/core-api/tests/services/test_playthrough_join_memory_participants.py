"""Joining a playthrough queues the participant list for memory."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models.memory_outbox import MemoryOutbox
from app.db.models.playthrough import Playthrough
from app.db.models.share import PlaythroughShare
from app.models.playthrough import PlaythroughCreate
from app.repositories.user_repo import UserRepo
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from tests.services.test_playthrough_service import (
    _make_scenario,
    _make_service,
    _make_user,
)

JOIN_TOKEN = "memory-participants-join"


async def _named_user(db_session: AsyncSession, name: str):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name=name
    )


async def _joinable_playthrough(db_session: AsyncSession):
    service = await _make_service(db_session)
    owner = await _named_user(db_session, "Ada")
    scenario = await _make_scenario(
        db_session, owner.user_id, player_count_support="both"
    )
    created = await service.create_playthrough(
        user_id=owner.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    db_session.add(
        PlaythroughShare(
            playthrough_id=created.playthrough_id,
            share_token=JOIN_TOKEN,
            mode="join",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )
    await db_session.flush()
    return service, created.playthrough_id


async def _participant_rows(
    db_session: AsyncSession, playthrough_id: uuid.UUID
) -> list[MemoryOutbox]:
    stmt = select(MemoryOutbox).where(
        MemoryOutbox.playthrough_id == playthrough_id,
        MemoryOutbox.item_kind == "participants",
    )
    return list((await db_session.execute(stmt)).scalars().all())


def _names(row: MemoryOutbox) -> list[str]:
    assert row.payload is not None
    return [item["display_name"] for item in row.payload["participants"]]


@pytest.mark.asyncio
async def test_join_queues_the_full_participant_list_at_the_current_turn(
    db_session: AsyncSession,
) -> None:
    service, playthrough_id = await _joinable_playthrough(db_session)
    joiner = await _named_user(db_session, "Bram")

    await service.join_playthrough(JOIN_TOKEN, joiner.user_id)

    [row] = await _participant_rows(db_session, playthrough_id)
    assert row.sequence == 0
    assert _names(row) == ["Ada", "Bram"]
    assert row.delivered_at is None


@pytest.mark.asyncio
async def test_second_join_at_the_same_turn_replaces_and_requeues_the_row(
    db_session: AsyncSession,
) -> None:
    service, playthrough_id = await _joinable_playthrough(db_session)
    first = await _named_user(db_session, "Bram")
    second = await _named_user(db_session, "Cleo")
    await service.join_playthrough(JOIN_TOKEN, first.user_id)
    [row] = await _participant_rows(db_session, playthrough_id)
    row.delivered_at = datetime.now(UTC)
    row.attempt_count = 2
    row.last_error = "memory_unavailable"
    await db_session.flush()

    await service.join_playthrough(JOIN_TOKEN, second.user_id)

    await db_session.refresh(row)
    rows = await _participant_rows(db_session, playthrough_id)
    assert [item.outbox_id for item in rows] == [row.outbox_id]
    assert _names(row) == ["Ada", "Bram", "Cleo"]
    assert (row.delivered_at, row.attempt_count, row.last_error) == (None, 0, None)


@pytest.mark.asyncio
async def test_rejoin_by_the_same_user_does_not_requeue(
    db_session: AsyncSession,
) -> None:
    service, playthrough_id = await _joinable_playthrough(db_session)
    joiner = await _named_user(db_session, "Bram")
    await service.join_playthrough(JOIN_TOKEN, joiner.user_id)
    [row] = await _participant_rows(db_session, playthrough_id)
    delivered_at = datetime.now(UTC)
    row.delivered_at = delivered_at
    await db_session.flush()

    await service.join_playthrough(JOIN_TOKEN, joiner.user_id)

    await db_session.refresh(row)
    assert row.delivered_at == delivered_at


@pytest.mark.asyncio
async def test_join_after_turns_queues_at_that_turn_count(
    db_session: AsyncSession,
) -> None:
    service, playthrough_id = await _joinable_playthrough(db_session)
    await db_session.execute(
        update(Playthrough)
        .where(Playthrough.playthrough_id == playthrough_id)
        .values(turn_count=4)
    )
    joiner = await _named_user(db_session, "Bram")

    await service.join_playthrough(JOIN_TOKEN, joiner.user_id)

    [row] = await _participant_rows(db_session, playthrough_id)
    assert row.sequence == 4


@pytest.mark.asyncio
async def test_playthrough_never_registered_with_memory_queues_nothing(
    db_session: AsyncSession,
) -> None:
    service, playthrough_id = await _joinable_playthrough(db_session)
    await db_session.execute(
        update(Playthrough)
        .where(Playthrough.playthrough_id == playthrough_id)
        .values(memory_publish_revision=None)
    )
    joiner = await _make_user(db_session)

    await service.join_playthrough(JOIN_TOKEN, joiner.user_id)

    assert await _participant_rows(db_session, playthrough_id) == []
