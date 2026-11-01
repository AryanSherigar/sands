import pytest
from app.models.battle_progress import OperationGuard
from app.models.orders import SetTaxRateOrder
from app.models.replay import ReplayStepKind
from app.repositories import replay_step_repo, world_state_repo
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from app.services.replay_service import ReplayService
from psycopg import AsyncConnection
from strategy_contracts.enums import TaxRate
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import (
    install_failure,
    mutation,
    remove_failure,
    seed_battle,
)
from tests.services.test_campaign_service import guard, initialization


async def test_journals_each_committed_campaign_transition(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    campaign = CampaignService(db_connection)
    initial = await campaign.initialize(request)
    command = SetTaxRateOrder(faction_id="house_carrow", tax_rate=TaxRate.HIGH)
    accepted = await CommandService(db_connection).accept(
        request.playthrough_id, OWNER_USER_ID, guard("tax"), command
    )
    await campaign.begin(
        request.playthrough_id,
        OWNER_USER_ID,
        OperationGuard(
            operation_id="begin",
            expected_world_version=accepted.world_version,
            expected_turn=0,
            expected_wave=0,
        ),
    )
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)
    assert [step.kind for step in steps] == [
        ReplayStepKind.ACCEPT_COMMAND,
        ReplayStepKind.BEGIN_CAMPAIGN,
    ]
    assert [step.sequence for step in steps] == [1, 2]
    assert steps[0].before_hash == initial.world_hash
    assert steps[-1].after_hash


async def test_idempotent_retry_does_not_append_a_replay_step(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    await CampaignService(db_connection).initialize(request)
    command = SetTaxRateOrder(faction_id="house_carrow", tax_rate=TaxRate.HIGH)
    service = CommandService(db_connection)
    first = await service.accept(
        request.playthrough_id, OWNER_USER_ID, guard("tax"), command
    )
    await service.accept(request.playthrough_id, OWNER_USER_ID, guard("tax"), command)
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)
    assert len(steps) == 1
    assert steps[0].after_hash == first.world_hash


async def test_advance_journals_the_frozen_intents(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id = await seed_battle(db_connection)
    campaign = CampaignService(db_connection)
    opened = await campaign.begin(playthrough_id, OWNER_USER_ID, mutation("begin", 1))
    await campaign.advance(
        playthrough_id,
        OWNER_USER_ID,
        mutation("wave", opened.world_version, wave=1),
    )
    step = (await replay_step_repo.list_steps(db_connection, playthrough_id))[-1]
    assert step.kind is ReplayStepKind.ADVANCE_CAMPAIGN
    assert step.input.kind is ReplayStepKind.ADVANCE_CAMPAIGN
    assert step.input.intents


async def test_replay_step_write_failure_rolls_back_world_update(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    await CampaignService(db_connection).initialize(request)
    before = await world_state_repo.get_world_state(
        db_connection, request.playthrough_id
    )
    await install_failure(db_connection, "simulation_replay_steps")
    try:
        with pytest.raises(Exception, match="injected persistence failure"):
            await CommandService(db_connection).accept(
                request.playthrough_id,
                OWNER_USER_ID,
                guard("tax"),
                SetTaxRateOrder(faction_id="house_carrow", tax_rate=TaxRate.HIGH),
            )
    finally:
        await remove_failure(db_connection, "simulation_replay_steps")
    assert (
        await world_state_repo.get_world_state(db_connection, request.playthrough_id)
        == before
    )


async def test_verifies_completed_turn_and_reads_historical_projection(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    campaign = CampaignService(db_connection)
    await campaign.initialize(request)
    accepted = await CommandService(db_connection).accept(
        request.playthrough_id,
        OWNER_USER_ID,
        guard("tax"),
        SetTaxRateOrder(faction_id="house_carrow", tax_rate=TaxRate.HIGH),
    )
    await campaign.begin(
        request.playthrough_id, OWNER_USER_ID, guard("begin", accepted.world_version)
    )
    replay = ReplayService(db_connection)
    verified = await replay.verify(request.playthrough_id, OWNER_USER_ID, 1)
    historical = await replay.load_history(request.playthrough_id, OWNER_USER_ID, 0)
    assert verified.verified_turn == 1
    assert historical.turn == 0
    assert historical.world.clock.turn == 0
