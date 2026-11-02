from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.models.event_delivery import EventDelivery
from app.repositories.event_delivery_repo import EventDeliveryRepo
from psycopg import AsyncConnection
from strategy_contracts.events import (
    EventNarrativeBriefing,
    EventNarrativePayload,
)

from tests.repositories.helpers import seed_playthrough


@pytest.fixture
def repo() -> EventDeliveryRepo:
    return EventDeliveryRepo()


def make_briefing(playthrough_id: UUID, event_id: str) -> EventNarrativeBriefing:
    return EventNarrativeBriefing(
        playthrough_id=playthrough_id,
        event_id=event_id,
        template_id="tax_grievance",
        template_name="Tax grievance",
        subject_name="Dunmere Vale",
        tier=1,
        cause_description="unrest is 45",
        ruler_name="Aldric Vane",
        ruler_traits=["stern"],
        season_year="Spring 1001",
        choices=[{"choice_id": "grant_relief", "label": "Grant tax relief"}],
    )


def make_payload() -> EventNarrativePayload:
    return EventNarrativePayload(
        body_prose="The town bailiffs gathered quietly before the gate.",
        cause_quote="We have given until our stores are empty.",
        character_name="Alderman Morvath",
        character_title="Guild Representative",
        disposition="Defiant",
    )


def test_event_delivery_model_structure() -> None:
    playthrough_id = uuid4()
    briefing = make_briefing(playthrough_id, "pe_1")
    delivery = EventDelivery(
        playthrough_id=playthrough_id,
        event_id="pe_1",
        turn=1,
        briefing=briefing,
        status="pending",
        created_at=datetime.now(UTC),
    )
    assert delivery.status == "pending"
    assert delivery.briefing.event_id == "pe_1"
    assert delivery.narration is None


async def test_insert_pending_and_get(
    db_connection: AsyncConnection, repo: EventDeliveryRepo
) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    briefing = make_briefing(playthrough_id, "pe_1")

    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    delivery = await repo.get(db_connection, playthrough_id, "pe_1")

    assert delivery is not None
    assert delivery.status == "pending"
    assert delivery.attempts == 0
    assert delivery.briefing.template_name == "Tax grievance"
    assert delivery.narration is None
    assert delivery.error_code is None


async def test_insert_pending_conflict_ignored(
    db_connection: AsyncConnection, repo: EventDeliveryRepo
) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    briefing = make_briefing(playthrough_id, "pe_1")

    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    delivery = await repo.get(db_connection, playthrough_id, "pe_1")

    assert delivery is not None
    assert delivery.status == "pending"


async def test_claim_success(
    db_connection: AsyncConnection, repo: EventDeliveryRepo
) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    briefing = make_briefing(playthrough_id, "pe_1")
    claim_id = uuid4()

    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    claim = await repo.claim(db_connection, playthrough_id, "pe_1", claim_id)

    assert claim is not None
    assert claim.lease_token is not None
    assert claim.briefing.event_id == "pe_1"

    delivery = await repo.get(db_connection, playthrough_id, "pe_1")
    assert delivery is not None
    assert delivery.status == "generating"
    assert delivery.attempts == 1
    assert delivery.claim_id == claim_id
    assert delivery.lease_token == claim.lease_token
    assert delivery.lease_expires_at is not None


async def test_claim_active_lease_blocks_second_claim(
    db_connection: AsyncConnection, repo: EventDeliveryRepo
) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    briefing = make_briefing(playthrough_id, "pe_1")

    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    first_claim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())
    second_claim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())

    assert first_claim is not None
    assert second_claim is None


async def test_claim_expired_lease_allows_reclaim(
    db_connection: AsyncConnection, repo: EventDeliveryRepo
) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    briefing = make_briefing(playthrough_id, "pe_1")

    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    first_claim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())
    assert first_claim is not None

    await db_connection.execute(
        "UPDATE event_deliveries SET lease_expires_at = now() - interval '1 second' "
        "WHERE playthrough_id = %s AND event_id = %s",
        (playthrough_id, "pe_1"),
    )
    second_claim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())

    assert second_claim is not None
    assert second_claim.lease_token != first_claim.lease_token

    delivery = await repo.get(db_connection, playthrough_id, "pe_1")
    assert delivery is not None
    assert delivery.attempts == 2


async def test_complete_success(
    db_connection: AsyncConnection, repo: EventDeliveryRepo
) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    briefing = make_briefing(playthrough_id, "pe_1")
    payload = make_payload()

    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    claim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())
    assert claim is not None

    is_completed = await repo.complete(
        db_connection, playthrough_id, "pe_1", claim.lease_token, payload
    )
    assert is_completed is True

    delivery = await repo.get(db_connection, playthrough_id, "pe_1")
    assert delivery is not None
    assert delivery.status == "completed"
    assert delivery.narration is not None
    assert delivery.narration.character_name == "Alderman Morvath"
    assert delivery.completed_at is not None
    assert delivery.lease_token is None
    assert delivery.lease_expires_at is None

    subsequent_claim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())
    assert subsequent_claim is None


async def test_complete_with_invalid_token(
    db_connection: AsyncConnection, repo: EventDeliveryRepo
) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    briefing = make_briefing(playthrough_id, "pe_1")
    payload = make_payload()

    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    claim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())
    assert claim is not None

    is_completed = await repo.complete(
        db_connection, playthrough_id, "pe_1", uuid4(), payload
    )
    assert is_completed is False

    delivery = await repo.get(db_connection, playthrough_id, "pe_1")
    assert delivery is not None
    assert delivery.status == "generating"


async def test_fail_marks_delivery_failed(
    db_connection: AsyncConnection, repo: EventDeliveryRepo
) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    briefing = make_briefing(playthrough_id, "pe_1")

    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    claim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())
    assert claim is not None

    await repo.fail(
        db_connection, playthrough_id, "pe_1", claim.lease_token, "upstream_error"
    )

    delivery = await repo.get(db_connection, playthrough_id, "pe_1")
    assert delivery is not None
    assert delivery.status == "failed"
    assert delivery.error_code == "upstream_error"
    assert delivery.lease_token is None


async def test_claim_can_reclaim_failed(
    db_connection: AsyncConnection, repo: EventDeliveryRepo
) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    briefing = make_briefing(playthrough_id, "pe_1")

    await repo.insert_pending(db_connection, playthrough_id, "pe_1", 1, briefing)
    claim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())
    assert claim is not None

    await repo.fail(
        db_connection, playthrough_id, "pe_1", claim.lease_token, "upstream_error"
    )

    reclaim = await repo.claim(db_connection, playthrough_id, "pe_1", uuid4())
    assert reclaim is not None

    delivery = await repo.get(db_connection, playthrough_id, "pe_1")
    assert delivery is not None
    assert delivery.status == "generating"
    assert delivery.attempts == 2
    assert delivery.error_code is None
