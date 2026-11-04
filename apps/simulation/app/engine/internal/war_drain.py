from app.engine.pressure.strain import compute_strain
from app.engine.pressure.wars import opposing_ids, side_score, wars_of
from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def _is_losing(war: WarState, faction_id: FactionId) -> bool:
    enemies = opposing_ids(war, faction_id)
    if not enemies:
        return False
    return side_score(war, faction_id) < side_score(war, enemies[0])


def _besieged_region_count(world: WorldState, faction_id: FactionId) -> int:
    return sum(
        1
        for siege in world.sieges
        if world.regions[siege.region_id].owner_id == faction_id
        and siege.besieger_id != faction_id
    )


def war_stability_factors(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> dict[str, int]:
    """Named per-turn stability costs of the faction's current wars, empty at peace."""
    wars = wars_of(world, faction_id)
    if not wars:
        return {}
    tuning = scenario.tuning.internal
    strain = compute_strain(world, scenario, faction_id).factors
    besieged = min(
        _besieged_region_count(world, faction_id), tuning.stability_loss_besieged_cap
    )
    losing = sum(1 for war in wars if _is_losing(war, faction_id))
    return {
        "war_base": len(wars) * tuning.stability_loss_per_active_war,
        "losing_war": losing * tuning.stability_loss_when_losing,
        "besieged": besieged * tuning.stability_loss_per_besieged_region,
        "unsupplied": tuning.stability_loss_unsupplied if strain["supply"] else 0,
        "low_manpower": tuning.stability_loss_low_manpower if strain["manpower"] else 0,
    }
