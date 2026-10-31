import pytest
from app.engine.replay import replay_history
from app.engine.world_document import world_from_document
from app.exceptions.world_exceptions import ReplayMismatchError
from app.models.orders import SetTaxRateOrder
from app.repositories import replay_step_repo, world_snapshot_repo
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from psycopg import AsyncConnection
from strategy_contracts.enums import TaxRate

from tests.repositories.helpers import OWNER_USER_ID
from tests.services.test_campaign_service import guard, initialization


async def test_replays_journaled_campaign_from_turn_zero(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    initial = await CampaignService(db_connection).initialize(request)
    await CommandService(db_connection).accept(
        request.playthrough_id,
        OWNER_USER_ID,
        guard("tax"),
        SetTaxRateOrder(faction_id="house_carrow", tax_rate=TaxRate.HIGH),
    )
    await CampaignService(db_connection).begin(
        request.playthrough_id, OWNER_USER_ID, guard("begin", version=2)
    )
    snapshot = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, request.playthrough_id, 0
    )
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)
    result = replay_history(
        world_from_document(snapshot.document), request.scenario, list(reversed(steps))
    )
    assert result.step_count == 2
    assert result.world_hash == steps[-1].after_hash
    assert initial.world_hash == steps[0].before_hash


async def test_replay_stops_at_the_first_tampered_hash(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    await CampaignService(db_connection).initialize(request)
    await CommandService(db_connection).accept(
        request.playthrough_id,
        OWNER_USER_ID,
        guard("tax"),
        SetTaxRateOrder(faction_id="house_carrow", tax_rate=TaxRate.HIGH),
    )
    snapshot = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, request.playthrough_id, 0
    )
    step = (await replay_step_repo.list_steps(db_connection, request.playthrough_id))[0]
    tampered = step.model_copy(update={"after_hash": "not-a-real-hash"})
    with pytest.raises(ReplayMismatchError) as error:
        replay_history(
            world_from_document(snapshot.document), request.scenario, [tampered]
        )
    assert error.value.sequence == 1
