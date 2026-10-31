from app.models.world_state import WorldState
from strategy_contracts.ids import ArmyId, FactionId, RegionId


def armies_at(
    world: WorldState, faction_id: FactionId, region_id: RegionId
) -> list[ArmyId]:
    return sorted(
        army.id
        for army in world.armies.values()
        if army.owner_id == faction_id and army.location_id == region_id
    )


def siege_at(world: WorldState, region_id: RegionId) -> bool:
    return any(siege.region_id == region_id for siege in world.sieges)
