"""participants items merge joiner names into a registered playthrough."""

from uuid import UUID, uuid4

import pytest
from app.exceptions.ingest_exceptions import (
    IngestOrderError,
    PlaythroughNotRegisteredError,
)
from app.models.ingest import (
    ParticipantsItem,
    ParticipantsPayload,
    RegisterItem,
    RegisterPayload,
)
from app.models.templates import ParticipantPayload
from app.repositories import playthrough_repo
from app.services.extraction_input import ParticipantNames
from app.services.ingest_service import IngestService
from psycopg import AsyncConnection
from tests.services.ingest_helpers import (
    PUBLISH_REVISION,
    TurnSpec,
    build_request,
    turn_item,
)

OWNER_NAME = "Ada"
JOINER_NAME = "Bram"


def _participant(participant_id: UUID, name: str) -> ParticipantPayload:
    return ParticipantPayload(participant_id=participant_id, display_name=name)


def _register(owner: ParticipantPayload) -> RegisterItem:
    return RegisterItem(
        item_kind="register_playthrough",
        sequence=0,
        payload=RegisterPayload(
            scenario_id=uuid4(),
            publish_revision=PUBLISH_REVISION,
            participants=[owner],
        ),
    )


def _update(sequence: int, *participants: ParticipantPayload) -> ParticipantsItem:
    return ParticipantsItem(
        item_kind="participants",
        sequence=sequence,
        payload=ParticipantsPayload(participants=list(participants)),
    )


async def _names(connection: AsyncConnection, playthrough_id: UUID) -> dict[UUID, str]:
    row = await playthrough_repo.get_playthrough(connection, playthrough_id)
    assert row is not None
    return {item.participant_id: item.display_name for item in row.participants}


async def _registered(
    connection: AsyncConnection,
) -> tuple[UUID, ParticipantPayload]:
    playthrough_id = uuid4()
    owner = _participant(uuid4(), OWNER_NAME)
    await IngestService(connection).ingest_items(
        build_request(playthrough_id, _register(owner))
    )
    return playthrough_id, owner


async def test_joiner_is_added_and_extraction_uses_the_name(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id, owner = await _registered(db_connection)
    joiner = _participant(uuid4(), JOINER_NAME)

    response = await IngestService(db_connection).ingest_items(
        build_request(playthrough_id, _update(0, owner, joiner))
    )

    assert [item.outcome for item in response.items] == ["applied"]
    names = await _names(db_connection, playthrough_id)
    assert names == {
        owner.participant_id: OWNER_NAME,
        joiner.participant_id: JOINER_NAME,
    }
    row = await playthrough_repo.get_playthrough(db_connection, playthrough_id)
    assert row is not None
    assert (
        ParticipantNames(row.participants).name_of(joiner.participant_id) == JOINER_NAME
    )


async def test_redelivery_is_a_duplicate(db_connection: AsyncConnection) -> None:
    playthrough_id, owner = await _registered(db_connection)
    request = build_request(
        playthrough_id, _update(0, owner, _participant(uuid4(), "X"))
    )
    await IngestService(db_connection).ingest_items(request)

    response = await IngestService(db_connection).ingest_items(request)

    assert [item.outcome for item in response.items] == ["duplicate"]


async def test_changed_display_name_is_refreshed(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id, owner = await _registered(db_connection)
    renamed = _participant(owner.participant_id, "Ada Lovelace")

    await IngestService(db_connection).ingest_items(
        build_request(playthrough_id, _update(0, renamed))
    )

    assert await _names(db_connection, playthrough_id) == {
        owner.participant_id: "Ada Lovelace"
    }


async def test_older_update_replayed_later_never_drops_a_joiner(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id, owner = await _registered(db_connection)
    joiner = _participant(uuid4(), JOINER_NAME)
    service = IngestService(db_connection)
    await service.ingest_items(build_request(playthrough_id, _update(2, owner, joiner)))

    await service.ingest_items(build_request(playthrough_id, _update(1, owner)))

    assert set(await _names(db_connection, playthrough_id)) == {
        owner.participant_id,
        joiner.participant_id,
    }


async def test_update_for_an_unregistered_playthrough_raises(
    db_connection: AsyncConnection,
) -> None:
    owner = _participant(uuid4(), OWNER_NAME)

    with pytest.raises(PlaythroughNotRegisteredError):
        await IngestService(db_connection).ingest_items(
            build_request(uuid4(), _update(0, owner))
        )


async def test_update_orders_between_a_turn_and_its_flush_sequence(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id, owner = await _registered(db_connection)
    joiner = _participant(uuid4(), JOINER_NAME)
    turn = turn_item(TurnSpec(1, narration="x"))

    await IngestService(db_connection).ingest_items(
        build_request(playthrough_id, turn, _update(1, owner, joiner))
    )

    assert joiner.participant_id in await _names(db_connection, playthrough_id)
    with pytest.raises(IngestOrderError):
        await IngestService(db_connection).ingest_items(
            build_request(playthrough_id, _update(1, owner, joiner), turn)
        )
