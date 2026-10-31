from app.engine.campaign_completion import complete_campaign
from app.engine.economy.income import faction_income
from app.engine.economy.manpower import refill_manpower
from app.engine.economy.state import start_run
from app.engine.internal.phase import InternalPhase
from app.engine.negotiation import acceptance_range
from app.engine.pressure.effects import pressure_stability_loss, pressure_unrest
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.will import compute_will
from app.models.world_state import WorldState
from strategy_contracts.scene import OutrageLevel

from tests.engine.diplomacy.builders import run_phase
from tests.engine.outrage.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    enrage,
    make_world,
)
from tests.engine.vassals.builders import add_war

TUNING = SCENARIO.tuning.outrage
ECONOMY = SCENARIO.tuning.economy


def _calm_and_mobilized() -> tuple[WorldState, WorldState]:
    calm = make_world()
    angry = make_world()
    enrage(angry, level=OutrageLevel.OUTRAGED)
    return calm, angry


def test_mobilization_lifts_will_and_adds_strain() -> None:
    calm, angry = _calm_and_mobilized()
    for world in (calm, angry):
        add_war(world, WRATHFUL_RIVAL, PLAYER)

    assert "mobilization" not in compute_will(calm, SCENARIO, WRATHFUL_RIVAL).factors
    will = compute_will(angry, SCENARIO, WRATHFUL_RIVAL)
    strain = compute_strain(angry, SCENARIO, WRATHFUL_RIVAL)
    assert will.factors["mobilization"] == TUNING.mobilization_will
    assert strain.factors["mobilization"] == TUNING.mobilization_strain


def test_mobilization_costs_stability_and_unrest_even_at_peace() -> None:
    calm, angry = _calm_and_mobilized()

    assert pressure_stability_loss(calm, SCENARIO, WRATHFUL_RIVAL) == 0
    assert (
        pressure_stability_loss(angry, SCENARIO, WRATHFUL_RIVAL)
        == TUNING.mobilization_stability_loss
    )
    assert (
        pressure_unrest(angry, SCENARIO, WRATHFUL_RIVAL) >= TUNING.mobilization_unrest
    )


def test_a_humiliated_ruler_demands_more_before_a_deal() -> None:
    calm, angry = _calm_and_mobilized()

    before = acceptance_range(calm, SCENARIO, PLAYER, WRATHFUL_RIVAL).accept_at
    after = acceptance_range(angry, SCENARIO, PLAYER, WRATHFUL_RIVAL).accept_at

    assert after > before


def test_mobilization_raises_taxes() -> None:
    calm, angry = _calm_and_mobilized()

    calm_tax = faction_income(calm, ECONOMY, WRATHFUL_RIVAL).tax_percent
    angry_tax = faction_income(angry, ECONOMY, WRATHFUL_RIVAL).tax_percent

    assert angry_tax == calm_tax + ECONOMY.mobilization_tax_bonus_percent


def _refill(world: WorldState) -> int:
    for region in world.regions.values():
        region.manpower = 0
    run = start_run(world, SCENARIO)
    refill_manpower(run, WRATHFUL_RIVAL)
    return sum(
        region.manpower
        for region in world.regions.values()
        if region.owner_id == WRATHFUL_RIVAL
    )


def test_mobilization_speeds_manpower_refill() -> None:
    calm, angry = _calm_and_mobilized()

    assert _refill(angry) > _refill(calm)


def test_mobilization_grants_extra_orders() -> None:
    calm, angry = _calm_and_mobilized()

    complete_campaign(calm, SCENARIO)
    complete_campaign(angry, SCENARIO)

    gained = (
        angry.factions[WRATHFUL_RIVAL].orders_remaining
        - calm.factions[WRATHFUL_RIVAL].orders_remaining
    )
    assert gained == TUNING.mobilization_orders_bonus


def test_mobilization_wears_the_faction_out_faster() -> None:
    calm, angry = _calm_and_mobilized()

    calm_after = run_phase(InternalPhase(), calm).world
    angry_after = run_phase(InternalPhase(), angry).world

    gained = (
        angry_after.factions[WRATHFUL_RIVAL].war_exhaustion
        - calm_after.factions[WRATHFUL_RIVAL].war_exhaustion
    )
    assert gained == TUNING.mobilization_exhaustion
