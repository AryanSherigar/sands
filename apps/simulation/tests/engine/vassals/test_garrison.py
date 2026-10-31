from app.engine.movement.contact import relation_status
from app.engine.vassals.garrison import apply_garrison_unrest, has_garrison_access
from app.engine.vassals.registry import vassalage_of
from app.models.world_army import ArmyState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus

from tests.engine.peace.builders import region_owned_by
from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    add_vassalage,
    make_world,
)

STEP = SCENARIO.tuning.vassal.garrison_unrest_per_turn
DEMAND_TURNS = SCENARIO.tuning.vassal.garrison_demand_turns


def _station_overlord_army(world: WorldState, region_id: str) -> None:
    world.armies["army_garrison"] = ArmyState(
        id="army_garrison",
        owner_id=PLAYER,
        troops={"infantry": 100},
        morale=50,
        location_id=region_id,
    )


def _setup(has_garrison: bool = True) -> tuple[WorldState, str]:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, has_garrison=has_garrison)
    region_id = region_owned_by(world, CAUTIOUS_RIVAL)
    world.regions[region_id].unrest = 10
    _station_overlord_army(world, region_id)
    return world, region_id


def test_overlord_army_in_vassal_region_adds_unrest_each_turn() -> None:
    world, region_id = _setup()

    apply_garrison_unrest(world, SCENARIO)
    apply_garrison_unrest(world, SCENARIO)

    assert world.regions[region_id].unrest == 10 + 2 * STEP


def test_no_unrest_without_an_army_present() -> None:
    world, region_id = _setup()
    del world.armies["army_garrison"]

    assert apply_garrison_unrest(world, SCENARIO) == []
    assert world.regions[region_id].unrest == 10


def test_unrest_is_capped_at_one_hundred() -> None:
    world, region_id = _setup()
    world.regions[region_id].unrest = 99

    apply_garrison_unrest(world, SCENARIO)

    assert world.regions[region_id].unrest == 100


def test_no_unrest_without_garrison_rights_or_temporary_access() -> None:
    world, region_id = _setup(has_garrison=False)

    assert apply_garrison_unrest(world, SCENARIO) == []
    assert world.regions[region_id].unrest == 10


def test_temporary_access_lapses_at_its_turn() -> None:
    world, _ = _setup(has_garrison=False)
    commitment = vassalage_of(world, CAUTIOUS_RIVAL)
    world.vassal.garrison_until[commitment.id] = world.clock.turn + DEMAND_TURNS

    assert has_garrison_access(world, PLAYER, CAUTIOUS_RIVAL)
    world.clock.turn += DEMAND_TURNS
    assert not has_garrison_access(world, PLAYER, CAUTIOUS_RIVAL)


def test_overlord_army_enters_vassal_region_without_contact() -> None:
    world, _ = _setup()

    assert relation_status(world, PLAYER, CAUTIOUS_RIVAL) is not RelationStatus.WAR


def test_two_armies_in_one_region_add_unrest_once() -> None:
    world, region_id = _setup()
    world.armies["army_second"] = world.armies["army_garrison"].model_copy(
        update={"id": "army_second"}
    )

    apply_garrison_unrest(world, SCENARIO)

    assert world.regions[region_id].unrest == 10 + STEP
