import pytest
from app.engine.endings import CAPITAL_LOST_ENDING_ID
from app.exceptions.command_exceptions import GameEndedError
from app.services.campaign_service import CampaignService
from app.services.world_view_service import WorldViewService
from psycopg import AsyncConnection
from strategy_contracts.scenario import EndingKind
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.test_campaign_service import guard, initialization


def _request_with_foreign_player_capital():
    request = initialization()
    setups = {setup.id: setup for setup in request.scenario.factions}
    rival = next(key for key in setups if key != request.player_faction_id)
    setups[request.player_faction_id].capital_region_id = setups[
        rival
    ].capital_region_id
    return request


async def test_a_lost_capital_ends_the_playthrough_and_surfaces_the_ending(
    db_connection: AsyncConnection,
) -> None:
    request = _request_with_foreign_player_capital()
    service = CampaignService(db_connection)
    await service.initialize(request)

    await service.begin(request.playthrough_id, OWNER_USER_ID, guard("begin0", 1))
    view = await WorldViewService(db_connection).load_world(
        request.playthrough_id, OWNER_USER_ID
    )

    assert view.ending is not None
    assert view.ending.ending_id == CAPITAL_LOST_ENDING_ID
    assert view.ending.kind is EndingKind.DEFEAT


async def test_an_ended_playthrough_refuses_another_turn(
    db_connection: AsyncConnection,
) -> None:
    request = _request_with_foreign_player_capital()
    service = CampaignService(db_connection)
    await service.initialize(request)
    await service.begin(request.playthrough_id, OWNER_USER_ID, guard("begin0", 1))
    next_turn = guard("begin1", 2).model_copy(update={"expected_turn": 1})

    with pytest.raises(GameEndedError):
        await service.begin(request.playthrough_id, OWNER_USER_ID, next_turn)


async def test_a_playthrough_without_a_lost_capital_has_no_ending(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    service = CampaignService(db_connection)
    await service.initialize(request)

    await service.begin(request.playthrough_id, OWNER_USER_ID, guard("begin0", 1))
    view = await WorldViewService(db_connection).load_world(
        request.playthrough_id, OWNER_USER_ID
    )

    assert view.ending is None


async def test_reaching_the_end_date_surfaces_a_graded_ending_with_own_components(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    request.scenario.tuning.end_year = request.scenario.tuning.start_year - 1
    service = CampaignService(db_connection)
    await service.initialize(request)

    await service.begin(request.playthrough_id, OWNER_USER_ID, guard("begin0", 1))
    view = await WorldViewService(db_connection).load_world(
        request.playthrough_id, OWNER_USER_ID
    )

    assert view.ending is not None
    assert view.ending.kind is EndingKind.GRADED
    assert view.ending.grade is not None
    assert set(view.ending.inputs) == {
        "position",
        "stability",
        "treasury",
        "will",
        "strain",
        "score",
    }
