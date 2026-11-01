"""Immutable relay deliveries deduplicate the whole transaction."""

import asyncio
from uuid import uuid4

import pytest
from app.exceptions.ingest_exceptions import (
    IngestContentConflictError,
    PlaythroughNotRegisteredError,
)
from app.models.ingest import IngestRequest, ParticipantsItem, ParticipantsPayload
from app.models.templates import ParticipantPayload
from app.repositories import ingest_delivery_repo, playthrough_repo
from app.services.ingest_service import IngestService
from psycopg import AsyncConnection
from tests.services.ingest_helpers import register_item


def _participants(playthrough_id, participant_id, sequence, name, delivery_id=None):
    return IngestRequest(
        playthrough_id=playthrough_id,
        delivery_id=delivery_id or uuid4(),
        items=[
            ParticipantsItem(
                item_kind="participants",
                sequence=sequence,
                payload=ParticipantsPayload(
                    participants=[
                        ParticipantPayload(
                            participant_id=participant_id, display_name=name
                        )
                    ]
                ),
            )
        ],
    )


async def test_delayed_delivery_does_not_revert_participant_name(db_connection):
    playthrough_id, participant_id = uuid4(), uuid4()
    service = IngestService(db_connection)
    await service.ingest_items(
        IngestRequest(
            playthrough_id=playthrough_id,
            delivery_id=uuid4(),
            items=[register_item(uuid4())],
        )
    )
    older = _participants(playthrough_id, participant_id, 1, "Old name")
    await service.ingest_items(older)
    await service.ingest_items(
        _participants(playthrough_id, participant_id, 2, "New name")
    )
    replay = await service.ingest_items(older)
    assert replay.items[0].outcome == "duplicate"
    row = await playthrough_repo.get_playthrough(db_connection, playthrough_id)
    assert row.participants[0].display_name == "New name"


async def test_delivery_id_with_different_payload_is_rejected(db_connection):
    playthrough_id, delivery_id = uuid4(), uuid4()
    request = IngestRequest(
        playthrough_id=playthrough_id,
        delivery_id=delivery_id,
        items=[register_item(uuid4())],
    )
    service = IngestService(db_connection)
    await service.ingest_items(request)
    changed = IngestRequest(
        playthrough_id=playthrough_id,
        delivery_id=delivery_id,
        items=[register_item(uuid4())],
    )
    with pytest.raises(IngestContentConflictError):
        await service.ingest_items(changed)
    assert (await service.ingest_items(request)).items[0].outcome == "duplicate"


async def test_failed_delivery_records_no_receipt_and_can_be_retried(db_connection):
    playthrough_id, participant_id = uuid4(), uuid4()
    request = _participants(playthrough_id, participant_id, 1, "Ada")
    service = IngestService(db_connection)
    with pytest.raises(PlaythroughNotRegisteredError):
        await service.ingest_items(request)
    assert (
        await ingest_delivery_repo.get_payload_hash(
            db_connection, playthrough_id, request.delivery_id
        )
        is None
    )
    await service.ingest_items(
        IngestRequest(playthrough_id=playthrough_id, items=[register_item(uuid4())])
    )
    assert (await service.ingest_items(request)).items[0].outcome == "applied"


async def test_concurrent_delivery_applies_registration_once(
    db_connection, migrated_test_database_url
):
    await db_connection.commit()
    request = IngestRequest(
        playthrough_id=uuid4(), delivery_id=uuid4(), items=[register_item(uuid4())]
    )

    async def deliver():
        async with await AsyncConnection.connect(
            migrated_test_database_url, autocommit=True
        ) as connection:
            return await IngestService(connection).ingest_items(request)

    responses = await asyncio.gather(deliver(), deliver())
    assert sorted(response.items[0].outcome for response in responses) == [
        "applied",
        "duplicate",
    ]


async def test_delayed_registration_cannot_restore_purged_memory(
    db_connection, retrieval_pool
):
    from app.exceptions.ingest_exceptions import PlaythroughPurgedError
    from app.services.purge_service import PurgeService

    request = IngestRequest(
        playthrough_id=uuid4(), delivery_id=uuid4(), items=[register_item(uuid4())]
    )
    service = IngestService(db_connection)
    await service.ingest_items(request)
    await db_connection.commit()
    assert await PurgeService(retrieval_pool).purge_playthrough(request.playthrough_id)
    with pytest.raises(PlaythroughPurgedError):
        await service.ingest_items(request)
    assert (
        await playthrough_repo.get_playthrough(db_connection, request.playthrough_id)
        is None
    )


async def test_purge_before_registration_blocks_delayed_first_delivery(
    db_connection, retrieval_pool
):
    from app.exceptions.ingest_exceptions import PlaythroughPurgedError
    from app.services.purge_service import PurgeService

    request = IngestRequest(
        playthrough_id=uuid4(), delivery_id=uuid4(), items=[register_item(uuid4())]
    )
    assert not await PurgeService(retrieval_pool).purge_playthrough(
        request.playthrough_id
    )
    with pytest.raises(PlaythroughPurgedError):
        await IngestService(db_connection).ingest_items(request)
