from uuid import uuid4

import pytest
from app.exceptions.command_exceptions import CommandError
from app.models.battle_progress import InitializeCampaign, OperationGuard
from app.models.orders import SetTaxRateOrder
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from psycopg import AsyncConnection
from strategy_contracts.enums import TaxRate
from strategy_contracts.examples import load_three_crowns
from tests.models.builders import make_world
from tests.repositories.helpers import OWNER_USER_ID


def initialization() -> InitializeCampaign:
    scenario = load_three_crowns()
    return InitializeCampaign(
        playthrough_id=uuid4(),
        owner_user_id=OWNER_USER_ID,
        operation_id="initialize",
        scenario=scenario,
        seed=42,
        player_faction_id="house_carrow",
        ruler=make_world().ruler,
    )


def guard(operation_id: str, version: int = 1) -> OperationGuard:
    return OperationGuard(
        operation_id=operation_id,
        expected_world_version=version,
        expected_turn=0,
        expected_wave=0,
    )


async def test_init_and_command_retry_returns_committed_response(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    service = CampaignService(db_connection)
    initial = await service.initialize(request)
    assert initial.world_version == 1
    payload = SetTaxRateOrder(faction_id="house_carrow", tax_rate=TaxRate.HIGH)
    commands = CommandService(db_connection)
    result = await commands.accept(
        request.playthrough_id, OWNER_USER_ID, guard("tax"), payload
    )
    replay = await commands.accept(
        request.playthrough_id, OWNER_USER_ID, guard("tax"), payload
    )
    assert replay.model_dump_json() == result.model_dump_json()
    assert result.orders_remaining == initial.orders_remaining - 1
    with pytest.raises(CommandError, match="operation identity"):
        await commands.accept(
            request.playthrough_id,
            OWNER_USER_ID,
            guard("tax"),
            payload.model_copy(update={"tax_rate": TaxRate.LOW}),
        )
    assert (await service.initialize(request)) == initial


async def test_initialize_without_a_seed_draws_one_and_replays_identically(
    db_connection: AsyncConnection,
) -> None:
    request = initialization().model_copy(update={"seed": None})
    service = CampaignService(db_connection)

    first = await service.initialize(request)
    replayed = await service.initialize(request)

    assert replayed.world_hash == first.world_hash
    assert replayed.world_version == first.world_version


async def test_initialize_without_a_seed_differs_between_playthroughs(
    db_connection: AsyncConnection,
) -> None:
    service = CampaignService(db_connection)
    first = await service.initialize(initialization().model_copy(update={"seed": None}))
    second = await service.initialize(
        initialization().model_copy(update={"seed": None})
    )

    assert first.world_hash != second.world_hash
