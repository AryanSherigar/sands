from app.engine.internal.war_drain import war_stability_factors
from app.engine.outrage.status import outrage_of
from app.engine.pressure.bands import to_band
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.wars import wars_of
from app.engine.pressure.will import compute_will
from app.models.api_world_view import (
    MobilizationView,
    OwnPressureView,
    RumorView,
    SubsidyView,
)
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def project_own_pressure(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> OwnPressureView | None:
    if not world.pressure_ruleset or not wars_of(world, faction_id):
        return None
    tuning = scenario.tuning.pressure
    will = compute_will(world, scenario, faction_id)
    strain = compute_strain(world, scenario, faction_id)
    return OwnPressureView(
        will_band=to_band(will.value, tuning),
        strain_band=to_band(strain.value, tuning),
        will_factors=will.factors,
        strain_factors=strain.factors,
        stability_factors=war_stability_factors(world, scenario, faction_id),
    )


def project_rumors(world: WorldState, faction_id: FactionId) -> list[RumorView]:
    return [
        RumorView(
            about_faction_id=rumor.about_faction_id,
            topic=rumor.topic,
            band=rumor.band,
            line_key=rumor.line_key,
            turn=rumor.turn,
        )
        for rumor in sorted(world.pressure.rumors, key=lambda item: item.id)
        if rumor.observer_id == faction_id
    ]


def project_subsidies(world: WorldState, faction_id: FactionId) -> list[SubsidyView]:
    return [
        SubsidyView(
            id=item.id,
            payer_id=item.payer_id,
            receiver_id=item.receiver_id,
            war_id=item.war_id,
            amount_per_turn=item.amount_per_turn,
            turns_left=item.expires_turn - world.clock.turn + 1,
        )
        for item in sorted(world.pressure.subsidies, key=lambda entry: entry.id)
        if faction_id in (item.payer_id, item.receiver_id)
    ]


def project_mobilization(
    world: WorldState, faction_id: FactionId
) -> MobilizationView | None:
    state = outrage_of(world, faction_id)
    if state is None or world.clock.turn >= state.mobilized_until_turn:
        return None
    return MobilizationView(turns_left=state.mobilized_until_turn - world.clock.turn)
