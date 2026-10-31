from app.engine.ai.knowledge import (
    build_knowledge,
    known_foreign_armies,
    region_distances,
)
from app.models.world_army import ArmyState
from strategy_contracts.enums import TroopType

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

FOGGED = "brennmoor"


def _knowledge(world):
    return build_knowledge(world, SCENARIO, CAUTIOUS_RIVAL)


def test_visible_regions_report_their_current_owner() -> None:
    world = make_world()
    world.regions["kings_ford"].owner_id = WRATHFUL_RIVAL

    knowledge = _knowledge(world)

    assert "kings_ford" in knowledge.visible
    assert knowledge.owners["kings_ford"] == WRATHFUL_RIVAL


def test_fogged_regions_fall_back_to_remembered_intel() -> None:
    world = make_world()
    assert FOGGED not in _knowledge(world).visible
    assert FOGGED not in _knowledge(world).owners

    world.factions[CAUTIOUS_RIVAL].intel[FOGGED] = (
        world.factions[CAUTIOUS_RIVAL]
        .intel["kings_ford"]
        .model_copy(update={"owner_id": "house_ashford"})
    )

    assert _knowledge(world).owners[FOGGED] == "house_ashford"


def test_changes_inside_the_fog_do_not_change_knowledge() -> None:
    world = make_world()
    before = _knowledge(world)
    world.regions[FOGGED].owner_id = WRATHFUL_RIVAL
    world.regions[FOGGED].garrison = 999

    assert _knowledge(world) == before


def test_only_foreign_armies_in_visible_regions_are_known() -> None:
    world = make_world()
    world.armies["scout"] = ArmyState(
        id="scout",
        owner_id=WRATHFUL_RIVAL,
        troops={TroopType.INFANTRY: 10},
        morale=50,
        location_id="kings_ford",
    )
    world.armies["hidden"] = ArmyState(
        id="hidden",
        owner_id=WRATHFUL_RIVAL,
        troops={TroopType.INFANTRY: 10},
        morale=50,
        location_id=FOGGED,
    )

    known = known_foreign_armies(world, CAUTIOUS_RIVAL, _knowledge(world))

    known_ids = {army.id for army in known}
    assert "scout" in known_ids
    assert "hidden" not in known_ids


def test_region_distances_count_steps_over_the_map() -> None:
    distances = region_distances(_knowledge(make_world()).index, "elmstead")

    assert distances["elmstead"] == 0
    assert distances["carrow_vale"] == 1
    assert distances["dunwick"] == 3
