from app.engine.pressure.bands import to_band
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.wars import wars_of
from app.engine.pressure.will import compute_will
from app.models.api_world_view import OwnPressureView, RumorView
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
