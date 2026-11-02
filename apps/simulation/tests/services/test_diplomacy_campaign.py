from app.engine.replay import replay_history
from app.engine.world_document import world_from_document
from app.models.orders import DeclareWarOrder
from app.repositories import replay_step_repo, world_snapshot_repo
from app.services.campaign_service import CampaignService
from app.services.command_service import CommandService
from app.services.world_view_service import WorldViewService
from psycopg import AsyncConnection
from strategy_contracts.enums import RelationStatus
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.test_campaign_service import guard, initialization

PLAYER = "house_carrow"
RIVAL = "house_dunwick"


async def _declare_and_begin(connection: AsyncConnection):
    request = initialization()
    await CampaignService(connection).initialize(request)
    await CommandService(connection).accept(
        request.playthrough_id,
        OWNER_USER_ID,
        guard("declare"),
        DeclareWarOrder(faction_id=PLAYER, target_faction_id=RIVAL),
    )
    await CampaignService(connection).begin(
        request.playthrough_id, OWNER_USER_ID, guard("begin", version=2)
    )
    return request


async def test_declared_war_replays_to_the_same_hashes(
    db_connection: AsyncConnection,
) -> None:
    request = await _declare_and_begin(db_connection)
    snapshot = await world_snapshot_repo.get_latest_snapshot_at_or_before(
        db_connection, request.playthrough_id, 0
    )
    steps = await replay_step_repo.list_steps(db_connection, request.playthrough_id)

    result = replay_history(
        world_from_document(snapshot.document), request.scenario, list(reversed(steps))
    )

    assert result.world_hash == steps[-1].after_hash
    assert (PLAYER, RIVAL) in [
        (war.attacker_id, war.defender_id) for war in result.world.wars
    ]
    relation = next(
        item
        for item in result.world.relations
        if {item.faction_a, item.faction_b} == {PLAYER, RIVAL}
    )
    assert relation.status == RelationStatus.WAR


async def test_player_view_never_contains_forgery_state_or_ground_strength(
    db_connection: AsyncConnection,
) -> None:
    request = await _declare_and_begin(db_connection)

    view = await WorldViewService(db_connection).load_world(
        request.playthrough_id, OWNER_USER_ID
    )

    dumped = view.model_dump_json().lower()
    assert "suspect_level" not in dumped
    assert "is_forged" not in dumped
    assert "strength" not in dumped
    assert "matures_turn" not in dumped
    for ground in view.usable_grounds:
        assert set(ground.model_dump()) == {
            "id",
            "kind",
            "target_faction_id",
            "region_id",
        }
