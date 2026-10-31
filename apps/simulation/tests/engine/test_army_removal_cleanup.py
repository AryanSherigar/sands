from app.engine.battles.reducer import _apply_armies
from app.engine.battles.state import BattleDelta
from app.engine.economy.armies import remove_army
from app.engine.pressure.strain import compute_strain
from app.models.world_siege import SiegeState

from tests.engine.pressure.builders import PLAYER, SCENARIO, add_war, make_world


def _starving_army_id(world) -> str:
    army_id = next(
        identity for identity, army in world.armies.items() if army.owner_id == PLAYER
    )
    world.supply_failure_turns[army_id] = 2
    return army_id


def test_removing_an_army_clears_its_supply_failure_entry() -> None:
    world = make_world()
    army_id = _starving_army_id(world)

    remove_army(world, army_id)

    assert army_id not in world.supply_failure_turns


def test_a_battle_destroying_an_army_clears_its_supply_failure_entry() -> None:
    world = make_world()
    army_id = _starving_army_id(world)
    delta = BattleDelta.model_construct(
        removed_army_ids=[army_id],
        army_updates={},
        commander_updates={},
        prisoners=[],
    )

    _apply_armies(world, delta)

    assert army_id not in world.supply_failure_turns


def test_strain_survives_a_stale_supply_failure_entry() -> None:
    world = make_world()
    add_war(world)
    world.supply_failure_turns["army_that_was_destroyed"] = 3

    compute_strain(world, SCENARIO, PLAYER)


def test_removing_an_army_clears_its_siege_reference() -> None:
    world = make_world()
    army_id = _starving_army_id(world)
    world.sieges = [
        SiegeState(
            region_id="region_x", besieger_id=PLAYER, army_ids=[army_id], progress=10
        )
    ]

    remove_army(world, army_id)

    assert world.sieges == []


def test_removing_one_of_two_besieging_armies_keeps_the_siege() -> None:
    world = make_world()
    army_id = _starving_army_id(world)
    world.sieges = [
        SiegeState(
            region_id="region_x",
            besieger_id=PLAYER,
            army_ids=[army_id, "army_other"],
            progress=10,
        )
    ]

    remove_army(world, army_id)

    assert world.sieges[0].army_ids == ["army_other"]
