from app.engine.replay import replay_history
from app.engine.world_document import world_from_document
from app.models.orders import SendEnvoyOrder
from app.repositories import replay_step_repo, world_snapshot_repo
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from psycopg import AsyncConnection
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.test_campaign_service import guard, initialization

PLAYER = "house_carrow"


async def test_replay_verifies_a_game_with_agent_envoys(
    db_connection: AsyncConnection,
) -> None:
    request = initialization()
    request.scenario.tuning.agents.is_enabled = True
    rival = next(
        faction.id for faction in request.scenario.factions if faction.id != PLAYER
    )
    await CampaignService(db_connection).initialize(request)
    await CommandService(db_connection).accept(
        request.playthrough_id,
        OWNER_USER_ID,
        guard("envoy"),
        SendEnvoyOrder(faction_id=PLAYER, target_faction_id=rival),
    )
    result = await CampaignService(db_connection).begin(
        request.playthrough_id, OWNER_USER_ID, guard("begin", version=2)
    )
    snapshot = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, request.playthrough_id, 0
    )
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)

    replayed = replay_history(
        world_from_document(snapshot.document), request.scenario, list(reversed(steps))
    )

    assert replayed.world_hash == steps[-1].after_hash
    assert result is not None
    envoys = replayed.world.envoys
    assert envoys and all(envoy.agent is not None for envoy in envoys)
