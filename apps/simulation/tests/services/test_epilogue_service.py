from uuid import UUID, uuid4

import pytest
from app.exceptions.base import SimulationServiceError
from app.services.campaign_service import CampaignService
from app.services.epilogue_service import EpilogueService
from psycopg import AsyncConnection
from strategy_contracts.epilogue import EpilogueCompleteInput, EpilogueFailInput
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.test_campaign_service import guard, initialization
from tests.services.test_campaign_service_endings import (
    _request_with_foreign_player_capital,
)


async def _ended_playthrough(connection: AsyncConnection) -> UUID:
    request = _request_with_foreign_player_capital()
    service = CampaignService(connection)
    await service.initialize(request)
    await service.begin(request.playthrough_id, OWNER_USER_ID, guard("begin0", 1))
    return request.playthrough_id


async def _running_playthrough(connection: AsyncConnection) -> UUID:
    request = initialization()
    await CampaignService(connection).initialize(request)
    return request.playthrough_id


async def _count_rows(connection: AsyncConnection) -> int:
    cursor = await connection.execute("SELECT count(*) FROM epilogue_deliveries")
    row = await cursor.fetchone()
    return row[0]


async def test_get_before_the_ending_is_a_conflict_and_creates_no_row(
    db_connection: AsyncConnection,
) -> None:
    identity = await _running_playthrough(db_connection)
    service = EpilogueService(db_connection)
    with pytest.raises(SimulationServiceError) as error:
        await service.get(identity, OWNER_USER_ID)
    assert error.value.status_code == 409
    with pytest.raises(SimulationServiceError):
        await service.claim(identity, OWNER_USER_ID, uuid4())
    assert await _count_rows(db_connection) == 0


async def test_get_after_the_ending_without_a_row_is_pending(
    db_connection: AsyncConnection,
) -> None:
    identity = await _ended_playthrough(db_connection)
    view = await EpilogueService(db_connection).get(identity, OWNER_USER_ID)
    assert view.status == "pending"
    assert view.narration is None
    assert await _count_rows(db_connection) == 0


async def test_claim_complete_roundtrip_saves_the_narration(
    db_connection: AsyncConnection,
) -> None:
    identity = await _ended_playthrough(db_connection)
    service = EpilogueService(db_connection)
    claim = await service.claim(identity, OWNER_USER_ID, uuid4())
    assert claim.lease_token is not None
    assert claim.briefing.ending_id == "default_defeat_capital_lost"
    assert claim.briefing.chronicler_id == "lucan"
    done = await service.complete(
        identity,
        OWNER_USER_ID,
        EpilogueCompleteInput(
            lease_token=claim.lease_token,
            input_hash=claim.input_hash,
            narration="The house was remembered as a warning.",
        ),
    )
    assert done.status == "completed"
    again = await service.claim(identity, OWNER_USER_ID, uuid4())
    assert again.epilogue.narration == "The house was remembered as a warning."
    assert again.lease_token is None
    assert (await service.get(identity, OWNER_USER_ID)).status == "completed"


async def test_a_wrong_lease_token_cannot_complete(
    db_connection: AsyncConnection,
) -> None:
    identity = await _ended_playthrough(db_connection)
    service = EpilogueService(db_connection)
    claim = await service.claim(identity, OWNER_USER_ID, uuid4())
    with pytest.raises(SimulationServiceError) as error:
        await service.complete(
            identity,
            OWNER_USER_ID,
            EpilogueCompleteInput(
                lease_token=uuid4(), input_hash=claim.input_hash, narration="x"
            ),
        )
    assert error.value.status_code == 409


async def test_a_failure_is_recorded_and_the_entry_can_be_claimed_again(
    db_connection: AsyncConnection,
) -> None:
    identity = await _ended_playthrough(db_connection)
    service = EpilogueService(db_connection)
    claim = await service.claim(identity, OWNER_USER_ID, uuid4())
    failed = await service.fail(
        identity,
        OWNER_USER_ID,
        EpilogueFailInput(
            lease_token=claim.lease_token, error_code="provider_unavailable"
        ),
    )
    assert failed.status == "failed"
    assert failed.is_retryable is True
    retry = await service.claim(identity, OWNER_USER_ID, uuid4())
    assert retry.lease_token is not None


async def test_another_user_cannot_read_the_epilogue(
    db_connection: AsyncConnection,
) -> None:
    identity = await _ended_playthrough(db_connection)
    with pytest.raises(SimulationServiceError) as error:
        await EpilogueService(db_connection).get(identity, uuid4())
    assert error.value.status_code == 404
