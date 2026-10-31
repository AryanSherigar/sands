from app.engine.negotiation import close_negotiation
from app.engine.opinion import opinion_of
from app.engine.outrage.status import outrage_of
from app.engine.overtures.arming import arm_overture
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import RefusedDemand, TermsResult

from tests.engine.overtures.builders import (
    PLAYER,
    WRATHFUL_RIVAL,
    scenario_with,
    set_axes,
    war_world,
)

NEVER_EXHAUSTED = {"peace_offer_min_strain": 101, "peace_offer_max_will": 0}
PENALTY = 7


def _armed(*, kind: str, **axes: int) -> tuple[WorldState, StrategyScenario, object]:
    world = war_world(attacker_score=60)
    if kind == "peace":
        scenario = scenario_with(
            peace_offer_min_strain=0, ignore_opinion_penalty=PENALTY
        )
    else:
        scenario = scenario_with(ignore_opinion_penalty=PENALTY, **NEVER_EXHAUSTED)
    scenario = set_axes(world, scenario, WRATHFUL_RIVAL, **axes)
    arm_overture(world, scenario)
    assert world.progress.pending_negotiation is not None
    return world, scenario, world.progress.pending_scene_id


def _opinion(world: WorldState) -> int:
    leader = world.leaders[world.factions[WRATHFUL_RIVAL].leader_id]
    return opinion_of(leader, world.factions[PLAYER].leader_id)


def _decline(world, scenario, scene_id, *, is_explicit: bool = False):
    refused = None
    if is_explicit:
        card = world.progress.pending_negotiation.overture.card
        refused = RefusedDemand(terms_card=card, tone_grade=1)
    return close_negotiation(
        world, scenario, scene_id, None, TermsResult.REFUSED, refused
    )


def _insult_grounds(world: WorldState) -> list:
    return [
        ground
        for ground in world.grounds
        if ground.holder_faction_id == WRATHFUL_RIVAL
        and ground.kind is GroundKind.INSULT
    ]


def test_ignored_peace_offer_lowers_opinion_only_for_calm_ruler() -> None:
    world, scenario, scene_id = _armed(kind="peace", caution=3)
    before = _opinion(world)

    closed, _ = _decline(world, scenario, scene_id)

    assert _opinion(closed) == before - PENALTY
    assert _insult_grounds(closed) == []


def test_ignored_peace_offer_grants_ground_to_aggressive_ruler() -> None:
    world, scenario, scene_id = _armed(kind="peace", aggression=3)

    closed, _ = _decline(world, scenario, scene_id)

    assert len(_insult_grounds(closed)) == 1


def test_refused_demand_raises_outrage_by_configured_levels() -> None:
    world, scenario, scene_id = _armed(kind="demand")

    closed, _ = _decline(world, scenario, scene_id, is_explicit=True)

    state = outrage_of(closed, WRATHFUL_RIVAL)
    assert state is not None
    assert state.target_faction_id == PLAYER


def test_ignored_demand_stronger_than_refused_for_proud_ruler() -> None:
    refused_world, scenario, scene_id = _armed(kind="demand", pride=3)
    ignored_world, ignored_scenario, ignored_id = _armed(kind="demand", pride=3)

    refused, _ = _decline(refused_world, scenario, scene_id, is_explicit=True)
    ignored, _ = _decline(ignored_world, ignored_scenario, ignored_id)

    levels = ["none", "annoyed", "offended", "outraged", "enraged"]
    refused_level = levels.index(outrage_of(refused, WRATHFUL_RIVAL).level.value)
    ignored_level = levels.index(outrage_of(ignored, WRATHFUL_RIVAL).level.value)
    assert ignored_level > refused_level


def test_decline_clears_pending_and_keeps_cooldown() -> None:
    world, scenario, scene_id = _armed(kind="peace")

    closed, _ = _decline(world, scenario, scene_id)

    assert closed.progress.pending_negotiation is None
    assert closed.progress.pending_scene_id is None
    assert closed.overture_cooldowns[WRATHFUL_RIVAL] > closed.clock.turn


def test_accepted_peace_offer_signs_truce() -> None:
    world, scenario, scene_id = _armed(kind="peace")
    card = world.progress.pending_negotiation.overture.card
    confirmed = card.model_copy(update={"is_confirmed_by_player": True})

    closed, _ = close_negotiation(
        world, scenario, scene_id, confirmed, TermsResult.AGREED
    )

    assert closed.wars == []
    assert len(closed.truces) == 1


def test_accepted_demand_moves_gold_and_ends_the_war() -> None:
    world, scenario, scene_id = _armed(kind="demand")
    treasury = world.factions[PLAYER].treasury
    card = world.progress.pending_negotiation.overture.card
    confirmed = card.model_copy(update={"is_confirmed_by_player": True})

    closed, _ = close_negotiation(
        world, scenario, scene_id, confirmed, TermsResult.AGREED
    )

    assert closed.wars == []
    assert closed.factions[PLAYER].treasury < treasury
