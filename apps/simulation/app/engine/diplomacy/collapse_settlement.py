from app.models.world_diplomacy import WarState
from app.models.world_region import RegionState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import CedeRegionTerm


def is_collapsed(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> bool:
    tuning = scenario.tuning.peace
    faction = world.factions[faction_id]
    return (
        bool(world.peace_ruleset)
        and faction.stability <= tuning.collapse_stability_floor
        and faction.war_exhaustion >= tuning.collapse_exhaustion_floor
    )


def _cession_rank(
    region: RegionState, world: WorldState, enemy_id: FactionId
) -> tuple[int, int, str]:
    is_held = (
        region.occupation is not None and region.occupation.occupier_id == enemy_id
    )
    is_besieged = any(
        siege.region_id == region.id and siege.besieger_id == enemy_id
        for siege in world.sieges
    )
    return (0 if is_held else 1 if is_besieged else 2, region.wealth, region.id)


def collapse_cession(
    world: WorldState,
    scenario: StrategyScenario,
    war: WarState,
    loser_id: FactionId,
    winner_id: FactionId,
) -> CedeRegionTerm | None:
    """The loser gives up one non-capital region, preferring ground the enemy already holds.

    NOTE: the capital is never ceded, so a collapsing house shrinks but survives.
    """
    capital_ids = {
        faction.capital_region_id
        for faction in scenario.factions
        if faction.id == loser_id
    }
    owned = [
        region
        for region in world.regions.values()
        if region.owner_id == loser_id and region.id not in capital_ids
    ]
    if not owned:
        return None
    region = min(owned, key=lambda item: _cession_rank(item, world, winner_id))
    return CedeRegionTerm(
        from_faction_id=loser_id, to_faction_id=winner_id, region_id=region.id
    )
