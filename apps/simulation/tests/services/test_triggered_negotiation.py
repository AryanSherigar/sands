from app.engine.negotiation_triggers import arm_triggered_negotiation
from app.repositories import scene_exchange_repo, scene_repo
from app.services.triggered_negotiation import persist_triggered_scene
from strategy_contracts.scene import SceneInitiator, SceneType
from tests.engine.overtures.builders import scenario_with, war_world
from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough


def _armed_world(**tuning: int):
    world = war_world(attacker_score=60)
    world.playthrough_id = PLAYTHROUGH_ID
    scenario = scenario_with(**tuning)
    arm_triggered_negotiation(world, scenario)
    return world, scenario


async def test_card_overture_persists_an_ai_peace_scene_with_a_first_proposal(
    db_connection,
) -> None:
    await seed_playthrough(db_connection)
    world, scenario = _armed_world(peace_offer_min_strain=0)

    await persist_triggered_scene(db_connection, world, scenario)

    scene_id = world.progress.pending_scene_id
    scene = await scene_repo.get_scene(db_connection, scene_id)
    assert scene.package.scene_type is SceneType.PEACE
    assert scene.package.initiator is SceneInitiator.AI
    exchanges = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    assert len(exchanges) == 1
    assert exchanges[0].proposal is not None
    assert (
        exchanges[0].leader_text == world.progress.pending_negotiation.overture.pretext
    )


async def test_replayed_persist_is_a_no_op(db_connection) -> None:
    await seed_playthrough(db_connection)
    world, scenario = _armed_world(peace_offer_min_strain=0)

    await persist_triggered_scene(db_connection, world, scenario)
    await persist_triggered_scene(db_connection, world, scenario)

    scene_id = world.progress.pending_scene_id
    exchanges = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    assert len(exchanges) == 1


async def test_talks_overture_has_no_proposal(db_connection) -> None:
    await seed_playthrough(db_connection)
    world = war_world()
    world.playthrough_id = PLAYTHROUGH_ID
    world.clock.turn += 3
    scenario = scenario_with(peace_offer_min_strain=101, peace_offer_max_will=0)
    arm_triggered_negotiation(world, scenario)
    assert world.progress.pending_negotiation is not None

    await persist_triggered_scene(db_connection, world, scenario)

    scene_id = world.progress.pending_scene_id
    exchanges = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    assert exchanges == []


async def test_heir_renewal_persists_a_negotiation_scene_with_the_old_tier(
    db_connection,
) -> None:
    from app.engine.overtures.succession_hook import remove_ruler
    from tests.engine.overtures.builders import (
        SCENARIO,
        WRATHFUL_RIVAL,
    )
    from tests.engine.overtures.test_heir_renewal import _signed_world

    await seed_playthrough(db_connection)
    world, _ = _signed_world()
    world.playthrough_id = PLAYTHROUGH_ID
    remove_ruler(world, SCENARIO, WRATHFUL_RIVAL)
    arm_triggered_negotiation(world, SCENARIO)

    await persist_triggered_scene(db_connection, world, SCENARIO)

    scene_id = world.progress.pending_scene_id
    scene = await scene_repo.get_scene(db_connection, scene_id)
    assert scene.package.scene_type is SceneType.NEGOTIATION
    exchanges = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    assert exchanges[0].proposal.terms[0].tier == "generation"
