import pytest
from app.repositories import scene_repo, world_state_repo
from app.services.campaign_service import CampaignService
from psycopg import AsyncConnection
from psycopg.errors import RaiseException
from strategy_contracts.scene import SceneStatus
from tests.engine.economy.builders import make_scenario
from tests.engine.economy.test_shortfall import _world
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import (
    install_failure,
    mutation,
    remove_failure,
    seed_world,
    table_counts,
)


@pytest.mark.parametrize("choice", ["shortfall_take_loan", "shortfall_default"])
async def test_economy_choice_is_durable_and_charged_once(
    db_connection: AsyncConnection, choice: str
) -> None:
    identity = await seed_world(db_connection, _world(), make_scenario())
    service = CampaignService(db_connection)
    paused = await service.begin(identity, OWNER_USER_ID, mutation("begin", 1))
    assert paused.status == "awaiting_scene" and paused.scene_id is not None
    counts = await table_counts(db_connection)
    request = mutation("choice", paused.world_version)
    completed = await service.resume_economy(
        identity, OWNER_USER_ID, request, paused.scene_id, choice
    )
    assert completed.status == "turn_completed" and completed.turn == 1
    assert (
        await service.resume_economy(
            identity, OWNER_USER_ID, request, paused.scene_id, choice
        )
        == completed
    )
    scene = await scene_repo.get_scene(db_connection, paused.scene_id)
    assert scene.status == SceneStatus.RESOLVED and scene.outcome.option_id == choice
    assert (await table_counts(db_connection))["world_snapshots"] == counts[
        "world_snapshots"
    ] + 1


async def test_scene_creation_failure_retains_unstarted_campaign(
    db_connection: AsyncConnection,
) -> None:
    identity = await seed_world(db_connection, _world(), make_scenario())
    before = await world_state_repo.get_world_state(db_connection, identity)
    await install_failure(db_connection, "scenes")
    try:
        with pytest.raises(RaiseException):
            await CampaignService(db_connection).begin(
                identity, OWNER_USER_ID, mutation("begin", 1)
            )
    finally:
        await remove_failure(db_connection, "scenes")
    assert await world_state_repo.get_world_state(db_connection, identity) == before
    assert (await table_counts(db_connection))["simulation_operations"] == 0
