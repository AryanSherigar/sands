from app.engine.battles.outlook import estimate_outlook
from app.models.battle_intelligence import Confidence
from app.models.world_battle import OutlookBasis, StandingPlan
from strategy_contracts.battle import Tactic
from strategy_contracts.enums import TroopType

from tests.engine.battles.builders import (
    ATTACKER,
    BATTLE_ID,
    DEFENDER,
    battle_fixture,
    start_battle,
)
from tests.engine.battles.test_views import observed_report


def _outlook(world, scenario):
    return estimate_outlook(world, BATTLE_ID, ATTACKER, scenario)


def _started(attacker: int = 1000, defender: int = 1000):
    world, scenario = battle_fixture(attacker, defender)
    start_battle(world, scenario)
    return world, scenario


def test_outlook_is_ordered_bounded_and_repeatable() -> None:
    world, scenario = _started()

    outlook = _outlook(world, scenario)

    assert outlook is not None
    for losses in (outlook.own_losses, outlook.enemy_losses):
        assert losses.low <= losses.expected <= losses.high
    assert 0 <= outlook.own_share_percent <= 100
    assert outlook == _outlook(world, scenario)
    assert {factor.id for factor in outlook.factors} == {
        "formation",
        "tactic",
        "weather",
        "supply",
    }


def test_unscouted_enemy_gives_a_low_confidence_even_mix_estimate() -> None:
    world, scenario = _started()

    outlook = _outlook(world, scenario)

    assert outlook.basis == OutlookBasis.ASSUMED_EVEN_MIX
    assert outlook.confidence == Confidence.LOW


def test_a_scouted_composition_raises_confidence_and_changes_the_basis() -> None:
    world, scenario = _started(1000, 100)
    report = observed_report().model_copy(update={"available_from_wave": 1})
    world.recon_reports[report.id] = report
    world.battles[0].report_ids.append(report.id)

    outlook = _outlook(world, scenario)

    assert outlook.basis == OutlookBasis.SCOUTED_COMPOSITION
    assert outlook.confidence == Confidence.HIGH


def test_hidden_enemy_details_do_not_change_the_outlook() -> None:
    world, scenario = _started()
    before = _outlook(world, scenario)

    enemy = world.battles[0].contingents[DEFENDER]
    enemy.plan = StandingPlan(tactic=Tactic.PRESS)
    world.armies["army_b"].morale = 1
    world.armies["army_b"].troops = {TroopType.CAVALRY: 1000}
    world.factions[DEFENDER].treasury = 7654321

    assert _outlook(world, scenario) == before


def test_a_stronger_own_army_improves_the_expected_exchange() -> None:
    weak_world, scenario = _started(300, 1000)
    strong_world, _ = _started(3000, 1000)

    weak = _outlook(weak_world, scenario)
    strong = _outlook(strong_world, scenario)

    assert strong.enemy_losses.expected > weak.enemy_losses.expected
    assert strong.own_share_percent > weak.own_share_percent


def test_outlook_factors_may_exceed_one_hundred_percent() -> None:
    world, scenario = _started()
    scenario.tuning.battle.formation_attack_percent = {
        formation: 110 for formation in scenario.tuning.battle.formation_attack_percent
    }

    outlook = _outlook(world, scenario)

    formation = next(item for item in outlook.factors if item.id == "formation")
    assert formation.percent == 110
