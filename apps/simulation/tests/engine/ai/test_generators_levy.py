from app.engine.ai.generators.levy import levy_candidates
from app.models.orders import RaiseArmyOrder
from app.models.world_diplomacy import WarState
from app.models.world_region import OccupationState
from strategy_contracts.enums import TroopType
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

TUNING = SCENARIO.tuning.ai
OCCUPATION = OccupationState(occupier_id=WRATHFUL_RIVAL, siege_progress=0)


def _levies(world) -> dict[str, int]:
    return {
        item.order.region_id: item.order.troops[TroopType.INFANTRY]
        for item in levy_candidates(world, SCENARIO, CAUTIOUS_RIVAL)
    }


def test_one_levy_is_offered_from_the_most_populous_owned_region() -> None:
    levies = _levies(make_world())

    assert levies == {"carrow_vale": 55}


def test_levy_never_exceeds_the_maximum() -> None:
    world = make_world()
    world.regions["carrow_vale"].manpower = 1000

    assert _levies(world)["carrow_vale"] == TUNING.max_levy


def test_manpower_poor_regions_are_skipped() -> None:
    world = make_world()
    for region in world.regions.values():
        if region.owner_id == CAUTIOUS_RIVAL:
            region.manpower = TUNING.min_levy * 2 - 1

    assert _levies(world) == {}


def test_occupied_regions_are_skipped() -> None:
    world = make_world()
    world.regions["carrow_vale"].occupation = OCCUPATION

    assert "carrow_vale" not in _levies(world)


def test_peace_levy_carries_friction_and_war_levy_is_cheaper() -> None:
    peace = levy_candidates(make_world(), SCENARIO, CAUTIOUS_RIVAL)
    world = make_world()
    world.wars.append(
        WarState(
            id="war_1",
            attacker_id=WRATHFUL_RIVAL,
            defender_id=CAUTIOUS_RIVAL,
            started_turn=0,
        )
    )
    war = levy_candidates(world, SCENARIO, CAUTIOUS_RIVAL)

    assert {item.base_score for item in peace} == {-TUNING.levy_friction}
    assert {item.base_score for item in war} == {
        TUNING.situation_bonus - TUNING.levy_friction
    }
    assert {item.category for item in war} == {ScoreCategory.ATTACK}
    assert all(isinstance(item.order, RaiseArmyOrder) for item in war)


def test_no_levy_once_the_army_cap_is_reached() -> None:
    world = make_world()
    template = world.armies["army_carrow_1"]
    for index in range(TUNING.max_armies):
        world.armies[f"filler_{index}"] = template.model_copy(
            update={"id": f"filler_{index}"}
        )

    assert levy_candidates(world, SCENARIO, CAUTIOUS_RIVAL) == []


def test_no_levy_when_the_treasury_is_low() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].treasury = TUNING.low_treasury - 1

    assert levy_candidates(world, SCENARIO, CAUTIOUS_RIVAL) == []
