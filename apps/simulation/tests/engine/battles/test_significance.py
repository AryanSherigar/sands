from app.engine.battles.creation import create_battle
from app.models.world_battle import BattleSignificance
from strategy_contracts.enums import TroopType

from tests.engine.battles.builders import ATTACKER, REGION, battle_fixture
from tests.engine.movement.builders import make_army


def test_committed_strength_classifies_battle_once() -> None:
    reserve = make_army("reserve_a", ATTACKER, "home_a", {TroopType.INFANTRY: 2000})
    world, scenario = battle_fixture(extra_armies=[reserve])

    battle = create_battle(world, REGION, ["army_a"], ["army_b"], scenario)

    assert battle.is_big
    assert BattleSignificance.COMMITTED_STRENGTH in battle.significance_reasons


def test_claimed_region_classifies_even_a_small_battle() -> None:
    world, scenario = battle_fixture(attacker=10, defender=10)
    world.regions[REGION].claimant_ids = [ATTACKER]

    battle = create_battle(world, REGION, ["army_a"], ["army_b"], scenario)

    assert battle.is_big
    assert BattleSignificance.CLAIMED_REGION in battle.significance_reasons
