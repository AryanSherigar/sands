from app.engine.outrage.effects import (
    mobilization_stability_loss,
    mobilization_unrest,
)
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.wars import wars_of
from app.engine.pressure.will import compute_will
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

STRAIN_LOSS_START = 60
STRAIN_LOSS_DIVISOR = 10
WILL_LOSS_CEILING = 40
WILL_LOSS_DIVISOR = 10
UNREST_DIVISOR = 2
ACCEPTANCE_SHIFT_CAP = 10


def _readings(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> tuple[int, int] | None:
    if not world.pressure_ruleset or not wars_of(world, faction_id):
        return None
    strain = compute_strain(world, scenario, faction_id).value
    return strain, compute_will(world, scenario, faction_id).value


def pressure_stability_loss(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    mobilized_loss = mobilization_stability_loss(world, scenario, faction_id)
    readings = _readings(world, scenario, faction_id)
    if readings is None:
        return mobilized_loss
    strain, will = readings
    strain_loss = max(0, strain - STRAIN_LOSS_START) // STRAIN_LOSS_DIVISOR
    will_loss = max(0, WILL_LOSS_CEILING - will) // WILL_LOSS_DIVISOR
    return strain_loss + will_loss + mobilized_loss


def pressure_unrest(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    war_loss = pressure_stability_loss(world, scenario, faction_id)
    war_loss -= mobilization_stability_loss(world, scenario, faction_id)
    return war_loss // UNREST_DIVISOR + mobilization_unrest(world, scenario, faction_id)


def acceptance_shift(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    readings = _readings(world, scenario, faction_id)
    if readings is None:
        return 0
    strain, will = readings
    shift = (strain - will) // scenario.tuning.pressure.acceptance_shift_divisor
    return max(-ACCEPTANCE_SHIFT_CAP, min(ACCEPTANCE_SHIFT_CAP, shift))


def mediation_shift(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    if not world.peace_ruleset:
        return 0
    war_ids = {war.id for war in wars_of(world, faction_id)}
    is_mediated = any(
        offer.war_id in war_ids and offer.expires_turn >= world.clock.turn
        for offer in world.pressure.mediation_offers
    )
    return scenario.tuning.peace.mediation_acceptance_bonus if is_mediated else 0
