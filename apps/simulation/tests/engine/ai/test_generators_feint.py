from app.engine.ai.generators.feint import feint_candidates
from app.models.orders import MoveArmyOrder
from app.models.world_ai import AimState
from app.models.world_diplomacy import RelationState, WarState
from app.models.world_region import RegionIntel
from strategy_contracts.enums import RelationStatus
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_traits,
)

TUNING = SCENARIO.tuning.ai


def _world(traits: list[str], has_war: bool = True, has_aim: bool = True):
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, traits)
    world.factions[CAUTIOUS_RIVAL].intel["dunwick"] = RegionIntel(
        last_seen_turn=0, owner_id=WRATHFUL_RIVAL, garrison_low=40, garrison_high=60
    )
    if has_war:
        low, high = sorted((CAUTIOUS_RIVAL, WRATHFUL_RIVAL))
        world.relations = [
            RelationState(
                faction_a=low,
                faction_b=high,
                status=RelationStatus.WAR,
                since_turn=0,
            )
        ]
        world.wars.append(
            WarState(
                id="war_1",
                attacker_id=CAUTIOUS_RIVAL,
                defender_id=WRATHFUL_RIVAL,
                started_turn=0,
            )
        )
    if has_aim:
        world.aims[CAUTIOUS_RIVAL] = AimState(
            category=ScoreCategory.ATTACK,
            target_faction_id=WRATHFUL_RIVAL,
            chosen_turn=0,
            leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
            capital_held=True,
        )
    return world


def _feint(world):
    return feint_candidates(world, SCENARIO, CAUTIOUS_RIVAL)


def test_cunning_ruler_sends_the_stronger_army_at_the_weakest_target() -> None:
    candidates = _feint(_world(["treacherous"]))
    by_army = {item.order.army_id: item.order for item in candidates}

    assert by_army["army_carrow_1"].to_region_id == "dunwick"


def test_the_weaker_army_is_the_decoy_aimed_somewhere_else() -> None:
    candidates = _feint(_world(["treacherous"]))
    by_army = {item.order.army_id: item.order for item in candidates}

    assert by_army["army_carrow_2"].to_region_id == "fenwatch"
    assert all(isinstance(item.order, MoveArmyOrder) for item in candidates)
    assert {item.base_score for item in candidates} == {TUNING.feint_bonus}
    assert {item.category for item in candidates} == {ScoreCategory.ATTACK}


def test_an_honest_ruler_never_feints() -> None:
    assert _feint(_world(["honorable"])) == []


def test_no_feint_without_a_war_or_an_attack_aim() -> None:
    assert _feint(_world(["treacherous"], has_war=False)) == []
    assert _feint(_world(["treacherous"], has_aim=False)) == []


def test_no_feint_with_a_single_idle_army() -> None:
    world = _world(["treacherous"])
    del world.armies["army_carrow_2"]

    assert _feint(world) == []


def test_no_feint_with_a_single_known_target_region() -> None:
    world = _world(["treacherous"])
    del world.factions[CAUTIOUS_RIVAL].intel["dunwick"]

    assert _feint(world) == []
