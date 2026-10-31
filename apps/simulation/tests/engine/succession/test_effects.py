from app.engine.negotiation import acceptance_range
from app.engine.pressure.effects import pressure_stability_loss, pressure_unrest
from app.engine.succession.effects import (
    crisis_acceptance_shift,
    crisis_stability_loss,
    crisis_unrest,
)
from app.engine.succession.install import kill_ruler
from app.models.world_state import WorldState

from tests.engine.succession.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    make_succession_world,
)

TUNING = SCENARIO.tuning.succession


def _crisis_world() -> WorldState:
    world = make_succession_world()
    kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness")
    return world


def test_crisis_costs_stability_unrest_and_acceptance_while_penalty_active() -> None:
    world = _crisis_world()

    assert crisis_stability_loss(world, SCENARIO, CAUTIOUS_RIVAL) == (
        TUNING.crisis_stability_loss
    )
    assert crisis_unrest(world, SCENARIO, CAUTIOUS_RIVAL) == TUNING.crisis_unrest
    assert crisis_acceptance_shift(world, SCENARIO, CAUTIOUS_RIVAL) == (
        TUNING.crisis_acceptance_shift
    )


def test_other_factions_and_peacetime_rulers_pay_nothing() -> None:
    world = _crisis_world()

    assert crisis_stability_loss(world, SCENARIO, PLAYER) == 0
    assert crisis_unrest(world, SCENARIO, PLAYER) == 0
    assert crisis_acceptance_shift(world, SCENARIO, PLAYER) == 0


def test_minor_heir_regency_has_no_penalty() -> None:
    world = _crisis_world()
    world.succession.crises[0].is_penalty_active = False

    assert crisis_stability_loss(world, SCENARIO, CAUTIOUS_RIVAL) == 0
    assert crisis_unrest(world, SCENARIO, CAUTIOUS_RIVAL) == 0
    assert crisis_acceptance_shift(world, SCENARIO, CAUTIOUS_RIVAL) == 0


def test_pressure_functions_include_the_crisis_even_without_a_war() -> None:
    world = _crisis_world()
    calm = make_succession_world()

    loss = pressure_stability_loss(world, SCENARIO, CAUTIOUS_RIVAL)
    unrest = pressure_unrest(world, SCENARIO, CAUTIOUS_RIVAL)

    assert loss == pressure_stability_loss(calm, SCENARIO, CAUTIOUS_RIVAL) + (
        TUNING.crisis_stability_loss
    )
    assert unrest == pressure_unrest(calm, SCENARIO, CAUTIOUS_RIVAL) + (
        TUNING.crisis_unrest
    )


def test_a_faction_in_crisis_concedes_more_easily() -> None:
    world = _crisis_world()
    calm = make_succession_world()
    regent_limits = acceptance_range(world, SCENARIO, PLAYER, CAUTIOUS_RIVAL)
    calm_limits = acceptance_range(calm, SCENARIO, PLAYER, CAUTIOUS_RIVAL)

    assert regent_limits.accept_at < calm_limits.accept_at
