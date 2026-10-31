import pytest
from app.engine.economy.upkeep import army_upkeep, faction_upkeep
from strategy_contracts.enums import PayLevel, TroopType

from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    TEST_TUNING,
    make_army,
    make_faction,
    make_world,
)

TUNING = TEST_TUNING


@pytest.mark.parametrize(
    ("troop_type", "expected"),
    [
        (TroopType.INFANTRY, 20),
        (TroopType.CAVALRY, 40),
        (TroopType.ARCHERS_SIEGE, 50),
    ],
)
def test_upkeep_is_priced_by_troop_type(troop_type: TroopType, expected: int) -> None:
    army = make_army("a1", PLAYER, troops={troop_type: 200})
    assert army_upkeep(army, TUNING) == expected


def test_a_mixed_army_pays_for_each_type() -> None:
    troops = {TroopType.INFANTRY: 100, TroopType.CAVALRY: 50}
    assert army_upkeep(make_army("a1", PLAYER, troops=troops), TUNING) == 20


def test_reduced_pay_costs_less() -> None:
    full = make_army("a1", PLAYER, pay_level=PayLevel.FULL)
    reduced = make_army("a1", PLAYER, pay_level=PayLevel.REDUCED)
    assert army_upkeep(reduced, TUNING) < army_upkeep(full, TUNING)


def test_upkeep_rounds_up_so_a_small_army_is_never_free() -> None:
    army = make_army("a1", PLAYER, troops={TroopType.INFANTRY: 1})
    assert army_upkeep(army, TUNING) == 1


def test_an_empty_army_costs_nothing() -> None:
    army = make_army("a1", PLAYER, troops={TroopType.INFANTRY: 0})
    assert army_upkeep(army, TUNING) == 0


def test_faction_upkeep_lists_only_its_own_armies_in_id_order() -> None:
    world = make_world(
        factions=[make_faction(PLAYER), make_faction(RIVAL)],
        armies=[
            make_army("a2", PLAYER),
            make_army("a1", PLAYER),
            make_army("b1", RIVAL),
        ],
    )
    assert list(faction_upkeep(world, TUNING, PLAYER)) == ["a1", "a2"]
