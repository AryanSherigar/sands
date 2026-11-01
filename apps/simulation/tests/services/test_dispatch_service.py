from uuid import UUID, uuid4

import pytest
from app.exceptions.base import SimulationServiceError
from app.repositories import dispatch_delivery_repo
from app.services.dispatch_service import DispatchService
from psycopg import AsyncConnection
from strategy_contracts.agents import (
    AgentTrait,
    AgentView,
    DispatchBriefing,
    DispatchCompleteInput,
    DispatchFailInput,
)
from strategy_contracts.pressure import PressureBand, RumorTopic
from tests.services.art_helpers import FOREIGN_USER_ID, OWNER, seed_campaign

RUMOR_ID = "rumor_1"
NARRATION = "My lord, all is quiet along the border."


async def _service(connection: AsyncConnection) -> tuple[DispatchService, UUID]:
    identity = await seed_campaign(connection)
    await dispatch_delivery_repo.insert(
        connection,
        DispatchBriefing(
            rumor_id=RUMOR_ID,
            playthrough_id=identity,
            turn=3,
            agent=AgentView(name="Aldous", traits=[AgentTrait.HONEST]),
            about_faction_id="house_dunwick",
            topic=RumorTopic.WILL,
            reported_band=PressureBand.HIGH,
        ),
    )
    return DispatchService(connection), identity


def _complete(lease: UUID, text: str = NARRATION) -> DispatchCompleteInput:
    return DispatchCompleteInput(lease_token=lease, narration=text)


async def test_claim_leases_and_returns_briefing(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)

    claim = await service.claim(identity, OWNER, RUMOR_ID, uuid4())

    assert claim.dispatch.status == "generating"
    assert claim.lease_token is not None
    assert (
        claim.briefing is not None and claim.briefing.reported_band is PressureBand.HIGH
    )


async def test_second_claim_during_lease_is_409(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    await service.claim(identity, OWNER, RUMOR_ID, uuid4())

    with pytest.raises(SimulationServiceError) as caught:
        await service.claim(identity, OWNER, RUMOR_ID, uuid4())

    assert (caught.value.status_code, caught.value.code) == (
        409,
        "dispatch_in_progress",
    )


async def test_same_claim_id_resumes_the_same_lease(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    claim_id = uuid4()
    first = await service.claim(identity, OWNER, RUMOR_ID, claim_id)

    again = await service.claim(identity, OWNER, RUMOR_ID, claim_id)

    assert again.lease_token == first.lease_token


async def test_completed_claim_returns_saved_text_without_lease(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    claim = await service.claim(identity, OWNER, RUMOR_ID, uuid4())
    assert claim.lease_token is not None
    await service.complete(identity, OWNER, RUMOR_ID, _complete(claim.lease_token))

    again = await service.claim(identity, OWNER, RUMOR_ID, uuid4())

    assert again.dispatch.narration == NARRATION
    assert again.lease_token is None and again.briefing is None


async def test_complete_with_stale_lease_is_409(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    await service.claim(identity, OWNER, RUMOR_ID, uuid4())

    with pytest.raises(SimulationServiceError) as caught:
        await service.complete(identity, OWNER, RUMOR_ID, _complete(uuid4()))

    assert caught.value.code == "stale_dispatch_lease"


async def test_complete_twice_same_text_is_idempotent_but_different_text_conflicts(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    claim = await service.claim(identity, OWNER, RUMOR_ID, uuid4())
    assert claim.lease_token is not None
    request = _complete(claim.lease_token)
    first = await service.complete(identity, OWNER, RUMOR_ID, request)

    assert await service.complete(identity, OWNER, RUMOR_ID, request) == first
    with pytest.raises(SimulationServiceError) as caught:
        await service.complete(
            identity, OWNER, RUMOR_ID, _complete(claim.lease_token, "different")
        )
    assert caught.value.code == "idempotency_conflict"


async def test_fail_then_reclaim_until_attempts_are_exhausted(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)
    for _ in range(3):
        claim = await service.claim(identity, OWNER, RUMOR_ID, uuid4())
        assert claim.lease_token is not None
        failed = await service.fail(
            identity,
            OWNER,
            RUMOR_ID,
            DispatchFailInput(
                lease_token=claim.lease_token, error_code="provider_unavailable"
            ),
        )
        assert failed.status == "failed"

    with pytest.raises(SimulationServiceError) as caught:
        await service.claim(identity, OWNER, RUMOR_ID, uuid4())
    assert caught.value.code == "dispatch_attempts_exhausted"


async def test_foreign_user_and_unknown_rumor_are_404(
    db_connection: AsyncConnection,
) -> None:
    service, identity = await _service(db_connection)

    for user, rumor_id in ((FOREIGN_USER_ID, RUMOR_ID), (OWNER, "rumor_9")):
        with pytest.raises(SimulationServiceError) as caught:
            await service.claim(identity, user, rumor_id, uuid4())
        assert caught.value.status_code == 404
