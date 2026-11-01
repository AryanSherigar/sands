import pytest
from app.exceptions.command_exceptions import CommandError
from app.models.orders import SetTaxRateOrder
from app.models.replay import ReplayStepKind
from app.repositories import replay_step_repo, world_state_repo
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from app.services.replay_service import ReplayService
from psycopg import AsyncConnection
from strategy_contracts.enums import TaxRate
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import install_failure, remove_failure
from tests.services.test_campaign_service import guard, initialization

PLAYER_FACTION = "house_carrow"


def raise_tax() -> SetTaxRateOrder:
    return SetTaxRateOrder(faction_id=PLAYER_FACTION, tax_rate=TaxRate.HIGH)


async def test_cancel_removes_the_order_and_journals_a_step(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    await CampaignService(db_connection).initialize(request)
    commands = CommandService(db_connection)
    accepted = await commands.accept(
        request.playthrough_id, OWNER_USER_ID, guard("tax"), raise_tax()
    )
    cancelled = await commands.cancel(
        request.playthrough_id,
        OWNER_USER_ID,
        guard("untax", accepted.world_version),
        accepted.accepted_command_id,
    )
    assert cancelled.orders_remaining == accepted.orders_remaining + 1
    assert await commands.list_commands(request.playthrough_id, OWNER_USER_ID) == []
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)
    assert [step.kind for step in steps] == [
        ReplayStepKind.ACCEPT_COMMAND,
        ReplayStepKind.CANCEL_COMMAND,
    ]


async def test_cancel_retry_is_idempotent_and_writes_no_second_step(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    await CampaignService(db_connection).initialize(request)
    commands = CommandService(db_connection)
    accepted = await commands.accept(
        request.playthrough_id, OWNER_USER_ID, guard("tax"), raise_tax()
    )
    retry_guard = guard("untax", accepted.world_version)
    first = await commands.cancel(
        request.playthrough_id, OWNER_USER_ID, retry_guard, accepted.accepted_command_id
    )
    again = await commands.cancel(
        request.playthrough_id, OWNER_USER_ID, retry_guard, accepted.accepted_command_id
    )
    assert again == first
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)
    assert len(steps) == 2


async def test_cancelled_order_never_runs_and_history_still_verifies(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    campaign = CampaignService(db_connection)
    await campaign.initialize(request)
    commands = CommandService(db_connection)
    accepted = await commands.accept(
        request.playthrough_id, OWNER_USER_ID, guard("tax"), raise_tax()
    )
    cancelled = await commands.cancel(
        request.playthrough_id,
        OWNER_USER_ID,
        guard("untax", accepted.world_version),
        accepted.accepted_command_id,
    )
    await campaign.begin(
        request.playthrough_id,
        OWNER_USER_ID,
        guard("begin", cancelled.world_version),
    )
    verified = await ReplayService(db_connection).verify(
        request.playthrough_id, OWNER_USER_ID, 1
    )
    assert verified.verified_turn == 1
    assert verified.step_count == 3


async def test_cancel_unknown_order_is_not_found_and_writes_nothing(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    await CampaignService(db_connection).initialize(request)
    with pytest.raises(CommandError) as raised:
        await CommandService(db_connection).cancel(
            request.playthrough_id, OWNER_USER_ID, guard("untax"), "missing"
        )
    assert raised.value.status_code == 404
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)
    assert steps == []


async def test_replay_step_failure_rolls_back_the_cancel(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    await CampaignService(db_connection).initialize(request)
    commands = CommandService(db_connection)
    accepted = await commands.accept(
        request.playthrough_id, OWNER_USER_ID, guard("tax"), raise_tax()
    )
    before = await world_state_repo.get_world_state(
        db_connection, request.playthrough_id
    )
    await install_failure(db_connection, "simulation_replay_steps")
    try:
        with pytest.raises(Exception, match="injected persistence failure"):
            await commands.cancel(
                request.playthrough_id,
                OWNER_USER_ID,
                guard("untax", accepted.world_version),
                accepted.accepted_command_id,
            )
    finally:
        await remove_failure(db_connection, "simulation_replay_steps")
    assert (
        await world_state_repo.get_world_state(db_connection, request.playthrough_id)
        == before
    )
    assert len(await commands.list_commands(request.playthrough_id, OWNER_USER_ID)) == 1
