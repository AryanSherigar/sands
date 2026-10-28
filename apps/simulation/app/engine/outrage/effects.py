from app.engine.outrage.levels import temper_total
from app.engine.outrage.status import (
    MOBILIZING_LEVELS,
    is_enraged,
    is_mobilized,
    outrage_of,
)
from app.engine.trait_axes import axis_totals
from app.models.world_character import LeaderState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis


def _while_mobilized(world: WorldState, faction_id: FactionId, amount: int) -> int:
    return amount if is_mobilized(world, faction_id) else 0


def mobilization_will(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    return _while_mobilized(
        world, faction_id, scenario.tuning.outrage.mobilization_will
    )


def mobilization_strain(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    return _while_mobilized(
        world, faction_id, scenario.tuning.outrage.mobilization_strain
    )


def mobilization_stability_loss(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    return _while_mobilized(
        world, faction_id, scenario.tuning.outrage.mobilization_stability_loss
    )


def mobilization_unrest(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    return _while_mobilized(
        world, faction_id, scenario.tuning.outrage.mobilization_unrest
    )


def mobilization_exhaustion(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    return _while_mobilized(
        world, faction_id, scenario.tuning.outrage.mobilization_exhaustion
    )


def mobilization_orders_bonus(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    return _while_mobilized(
        world, faction_id, scenario.tuning.outrage.mobilization_orders_bonus
    )


def humiliation_shift(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    if world.outrage_ruleset < 1:
        return 0
    held = world.pressure.humiliation.get(faction_id, 0)
    return held // scenario.tuning.outrage.humiliation_shift_divisor


def _leader_of(world: WorldState, faction_id: FactionId) -> LeaderState | None:
    return world.leaders.get(world.factions[faction_id].leader_id or "")


def is_calculating(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    leader = _leader_of(world, faction_id)
    if leader is None:
        return False
    cunning = axis_totals(leader, scenario)[TraitAxis.CUNNING]
    return cunning >= scenario.tuning.outrage.ai_calculating_cunning


def has_press_bias(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    leader = _leader_of(world, faction_id)
    if leader is None or not is_enraged(world, faction_id):
        return False
    if is_calculating(world, scenario, faction_id):
        return False
    return temper_total(leader, scenario) >= scenario.tuning.outrage.press_trait_total


def denies_quarter(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    return is_enraged(world, faction_id) and not is_calculating(
        world, scenario, faction_id
    )


MAX_RAGE_STEPS = 2


def rage_steps(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> int:
    """How hard the AI leans into war: zero unless angry, uncalculating and quick to temper."""
    state = outrage_of(world, faction_id)
    leader = _leader_of(world, faction_id)
    if state is None or leader is None or state.level not in MOBILIZING_LEVELS:
        return 0
    if is_calculating(world, scenario, faction_id):
        return 0
    steps = temper_total(leader, scenario) // scenario.tuning.outrage.press_trait_total
    return max(0, min(MAX_RAGE_STEPS, steps))
