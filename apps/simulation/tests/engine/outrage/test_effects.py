from app.engine.outrage.effects import (
    denies_quarter,
    has_press_bias,
    humiliation_shift,
    is_calculating,
    mobilization_exhaustion,
    mobilization_orders_bonus,
    mobilization_stability_loss,
    mobilization_strain,
    mobilization_unrest,
    mobilization_will,
)
from strategy_contracts.scene import OutrageLevel

from tests.engine.outrage.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    enrage,
    make_world,
    set_axes,
)

TUNING = SCENARIO.tuning.outrage


def test_a_mobilized_faction_pays_and_gains_by_tuning() -> None:
    world = make_world()
    enrage(world, level=OutrageLevel.OUTRAGED)

    args = (world, SCENARIO, WRATHFUL_RIVAL)

    assert mobilization_will(*args) == TUNING.mobilization_will
    assert mobilization_strain(*args) == TUNING.mobilization_strain
    assert mobilization_stability_loss(*args) == TUNING.mobilization_stability_loss
    assert mobilization_unrest(*args) == TUNING.mobilization_unrest
    assert mobilization_exhaustion(*args) == TUNING.mobilization_exhaustion
    assert mobilization_orders_bonus(*args) == TUNING.mobilization_orders_bonus


def test_an_unmobilized_faction_feels_nothing() -> None:
    world = make_world()
    enrage(world, level=OutrageLevel.OUTRAGED)
    args = (world, SCENARIO, CAUTIOUS_RIVAL)

    assert mobilization_will(*args) == 0
    assert mobilization_orders_bonus(*args) == 0


def test_humiliation_raises_the_bar_for_a_deal() -> None:
    world = make_world()
    assert humiliation_shift(world, SCENARIO, WRATHFUL_RIVAL) == 0

    enrage(world)

    expected = 4 * TUNING.humiliation_per_level // TUNING.humiliation_shift_divisor
    assert humiliation_shift(world, SCENARIO, WRATHFUL_RIVAL) == expected


def test_legacy_worlds_have_no_humiliation_shift() -> None:
    world = make_world()
    world.pressure.humiliation[WRATHFUL_RIVAL] = 30
    world.outrage_ruleset = 0

    assert humiliation_shift(world, SCENARIO, WRATHFUL_RIVAL) == 0


def _traits(world, faction_id, **axes):
    return set_axes(world, SCENARIO, faction_id, **axes)


def test_a_wrathful_enraged_ruler_presses_and_gives_no_quarter() -> None:
    world = make_world()
    scenario = _traits(world, WRATHFUL_RIVAL, pride=2, aggression=3, caution=0)
    enrage(world)

    assert has_press_bias(world, scenario, WRATHFUL_RIVAL)
    assert denies_quarter(world, scenario, WRATHFUL_RIVAL)


def test_a_calm_ruler_neither_presses_nor_denies_quarter() -> None:
    world = make_world()
    scenario = _traits(world, WRATHFUL_RIVAL, pride=2, aggression=3, caution=0)

    assert not has_press_bias(world, scenario, WRATHFUL_RIVAL)
    assert not denies_quarter(world, scenario, WRATHFUL_RIVAL)


def test_a_calculating_ruler_mobilizes_but_keeps_their_head() -> None:
    world = make_world()
    scenario = _traits(
        world, WRATHFUL_RIVAL, pride=2, aggression=3, caution=0, cunning=3
    )
    enrage(world)

    assert is_calculating(world, scenario, WRATHFUL_RIVAL)
    assert not has_press_bias(world, scenario, WRATHFUL_RIVAL)
    assert not denies_quarter(world, scenario, WRATHFUL_RIVAL)
    assert mobilization_will(world, scenario, WRATHFUL_RIVAL) > 0


def test_a_cautious_enraged_ruler_does_not_charge_blindly() -> None:
    world = make_world()
    scenario = _traits(world, CAUTIOUS_RIVAL, pride=0, aggression=0, caution=3)
    enrage(world, faction_id=CAUTIOUS_RIVAL)

    assert not has_press_bias(world, scenario, CAUTIOUS_RIVAL)
