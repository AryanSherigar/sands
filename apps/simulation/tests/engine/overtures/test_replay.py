from app.engine.hashing import world_hash
from app.engine.negotiation import close_negotiation
from app.engine.overtures.arming import arm_overture
from strategy_contracts.scene import TermsResult

from tests.engine.overtures.builders import scenario_with, war_world


def _ignored_run() -> str:
    world = war_world(attacker_score=40)
    scenario = scenario_with(peace_offer_min_strain=0)
    arm_overture(world, scenario)
    closed, _ = close_negotiation(
        world, scenario, world.progress.pending_scene_id, None, TermsResult.REFUSED
    )
    return world_hash(closed)


def test_an_ignored_overture_replays_to_identical_hashes() -> None:
    assert _ignored_run() == _ignored_run()


def test_accepting_instead_of_ignoring_changes_the_hash() -> None:
    world = war_world(attacker_score=40)
    scenario = scenario_with(peace_offer_min_strain=0)
    arm_overture(world, scenario)
    card = world.progress.pending_negotiation.overture.card
    confirmed = card.model_copy(update={"is_confirmed_by_player": True})
    accepted, _ = close_negotiation(
        world, scenario, world.progress.pending_scene_id, confirmed, TermsResult.AGREED
    )

    assert world_hash(accepted) != _ignored_run()


def test_ruleset_0_hash_ignores_overture_state() -> None:
    plain = war_world()
    plain.overture_ruleset = 0
    marked = plain.model_copy(deep=True)
    marked.overture_cooldowns = {"house_dunwick": 9}
    marked.overture_renewals = ["truce_1"]

    assert world_hash(plain) == world_hash(marked)
