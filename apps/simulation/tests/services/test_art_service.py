from uuid import UUID, uuid4

import pytest
from app.config import get_settings
from app.exceptions.base import SimulationServiceError
from app.services.art_service import ArtService
from psycopg import AsyncConnection
from strategy_contracts.art import ArtCompleteInput, ArtFailInput
from tests.services.art_helpers import (
    EVENT_ID,
    FOREIGN_USER_ID,
    OWNER,
    UPRISING_ID,
    add_pending_event,
    add_summary,
    add_uprising,
    remove_pending_events,
    remove_uprisings,
    seed_campaign,
)

ART_URL = "https://cdn.example/strategy-art/one.webp"


def _complete(lease: UUID) -> ArtCompleteInput:
    return ArtCompleteInput(lease_token=lease, art_url=ART_URL)


async def _service(connection: AsyncConnection) -> tuple[ArtService, UUID]:
    identity = await seed_campaign(connection)
    await add_pending_event(connection, identity)
    return ArtService(connection), identity


async def test_claim_creates_generating_row_with_lease(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    claim = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    assert claim.art.status == "generating"
    assert claim.lease_token is not None
    assert claim.briefing.item_id == EVENT_ID


async def test_claim_while_active_lease_raises_art_in_progress(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    with pytest.raises(SimulationServiceError) as caught:
        await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    assert caught.value.code == "art_in_progress"
    assert caught.value.status_code == 409


async def test_claim_after_lease_expiry_succeeds(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    first = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    await db_connection.execute(
        "UPDATE art_deliveries SET lease_expires_at = now() - interval '1 second'"
    )
    second = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    assert second.lease_token != first.lease_token


async def test_claim_completed_returns_art_url_without_lease(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    claim = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    assert claim.lease_token is not None
    await service.complete(
        identity, OWNER, "event", EVENT_ID, _complete(claim.lease_token)
    )
    again = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    assert again.art.status == "completed"
    assert again.art.art_url == ART_URL
    assert again.lease_token is None


async def test_claim_unknown_event_without_row_is_404(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    with pytest.raises(SimulationServiceError) as caught:
        await service.claim(identity, OWNER, "event", "missing", uuid4())
    assert caught.value.status_code == 404


async def test_complete_with_stale_lease_is_409(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    with pytest.raises(SimulationServiceError) as caught:
        await service.complete(identity, OWNER, "event", EVENT_ID, _complete(uuid4()))
    assert caught.value.code == "stale_art_lease"


async def test_complete_twice_same_lease_is_idempotent(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    claim = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    assert claim.lease_token is not None
    request = _complete(claim.lease_token)
    first = await service.complete(identity, OWNER, "event", EVENT_ID, request)
    second = await service.complete(identity, OWNER, "event", EVENT_ID, request)
    assert first == second
    assert second.art_url == ART_URL


async def test_complete_after_event_resolved_still_saves(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    claim = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    assert claim.lease_token is not None
    await remove_pending_events(db_connection, identity)
    view = await service.complete(
        identity, OWNER, "event", EVENT_ID, _complete(claim.lease_token)
    )
    assert view.status == "completed"


async def test_fail_records_error_and_is_retryable_until_max_attempts(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    claim = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    assert claim.lease_token is not None
    failed = await service.fail(
        identity,
        OWNER,
        "event",
        EVENT_ID,
        ArtFailInput(lease_token=claim.lease_token, error_code="provider_unavailable"),
    )
    assert failed.status == "failed"
    assert failed.is_retryable is True
    for _ in range(get_settings().art_max_attempts - 1):
        retry = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
        assert retry.lease_token is not None
        failed = await service.fail(
            identity,
            OWNER,
            "event",
            EVENT_ID,
            ArtFailInput(lease_token=retry.lease_token, error_code="provider_timeout"),
        )
    assert failed.is_retryable is False
    with pytest.raises(SimulationServiceError) as caught:
        await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    assert caught.value.code == "art_attempts_exhausted"


async def test_foreign_owner_gets_404(db_connection: AsyncConnection) -> None:
    service, identity = await _service(db_connection)
    with pytest.raises(Exception) as caught:
        await service.claim(identity, FOREIGN_USER_ID, "event", EVENT_ID, uuid4())
    assert getattr(caught.value, "status_code", None) == 404


async def test_uprising_and_chronicle_kinds_are_claimable(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    await add_uprising(db_connection, identity)
    summary_id = await add_summary(db_connection, identity)
    uprising = await service.claim(identity, OWNER, "uprising", UPRISING_ID, uuid4())
    chronicle = await service.claim(
        identity, OWNER, "chronicle", str(summary_id), uuid4()
    )
    assert uprising.briefing.kind == "uprising"
    assert chronicle.briefing.kind == "chronicle"


async def _expire_lease(connection: AsyncConnection) -> None:
    await connection.execute(
        "UPDATE art_deliveries SET lease_expires_at = now() - interval '1 second'"
    )


async def test_a_late_claim_after_the_event_was_answered_uses_the_kept_briefing(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    first = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())
    await remove_pending_events(db_connection, identity)
    await _expire_lease(db_connection)

    late = await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())

    assert late.briefing == first.briefing
    assert late.lease_token != first.lease_token


async def test_a_late_claim_after_the_uprising_ended_uses_the_kept_briefing(
    db_connection: AsyncConnection,
) -> None:
    identity = await seed_campaign(db_connection)
    await add_uprising(db_connection, identity)
    service = ArtService(db_connection)
    first = await service.claim(identity, OWNER, "uprising", UPRISING_ID, uuid4())
    await remove_uprisings(db_connection, identity)
    await _expire_lease(db_connection)

    late = await service.claim(identity, OWNER, "uprising", UPRISING_ID, uuid4())

    assert late.briefing == first.briefing


async def test_an_answered_event_that_was_never_claimed_is_still_not_found(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    await remove_pending_events(db_connection, identity)

    with pytest.raises(SimulationServiceError) as caught:
        await service.claim(identity, OWNER, "event", EVENT_ID, uuid4())

    assert caught.value.status_code == 404
