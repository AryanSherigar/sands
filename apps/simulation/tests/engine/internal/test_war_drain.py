from app.engine.internal.war_drain import war_stability_factors
from app.models.world_siege import SiegeState
from strategy_contracts.scenario import InternalTuning, StrategyScenario
from tests.engine.pressure.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)


def _scenario(**overrides: int) -> StrategyScenario:
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning = scenario.tuning.model_copy(
        update={"internal": InternalTuning(**overrides)}
    )
    return scenario


def _war_world():
    world = make_world()
    add_war(world)
    return world


def test_no_factors_at_peace() -> None:
    assert war_stability_factors(make_world(), SCENARIO, PLAYER) == {}


def test_holding_an_even_war_costs_only_the_base() -> None:
    scenario = _scenario(stability_loss_per_active_war=1)
    factors = war_stability_factors(_war_world(), scenario, PLAYER)

    assert factors["war_base"] == 1
    assert factors["losing_war"] == 0


def test_losing_on_score_adds_the_losing_cost() -> None:
    world = _war_world()
    world.wars[0].war_score_attacker = 30
    scenario = _scenario(stability_loss_when_losing=3)

    assert war_stability_factors(world, scenario, PLAYER)["losing_war"] == 3
    assert war_stability_factors(world, scenario, WRATHFUL_RIVAL)["losing_war"] == 0


def test_besieged_cost_scales_with_regions_and_is_capped() -> None:
    world = _war_world()
    owned = [r.id for r in world.regions.values() if r.owner_id == PLAYER]
    world.sieges = [
        SiegeState(region_id=region_id, besieger_id=WRATHFUL_RIVAL, army_ids=[])
        for region_id in owned
    ]
    scenario = _scenario(
        stability_loss_per_besieged_region=2, stability_loss_besieged_cap=1
    )

    assert war_stability_factors(world, scenario, PLAYER)["besieged"] == 2
