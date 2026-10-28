from app.engine.movement.contact import relation_status
from app.engine.movement.map_index import MapIndex
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId, RegionId


def _allies_of(world: WorldState, faction_id: FactionId) -> set[FactionId]:
    return {
        other_id
        for other_id in world.factions
        if relation_status(world, faction_id, other_id) is RelationStatus.ALLIANCE
    }


def _own_sight(
    world: WorldState, index: MapIndex, faction_id: FactionId
) -> set[RegionId]:
    owned = {
        region_id
        for region_id, region in world.regions.items()
        if region.owner_id == faction_id
    }
    seen = set(owned)
    for region_id in owned:
        seen |= index.neighbors.get(region_id, frozenset())
    seen |= {
        army.location_id
        for army in world.armies.values()
        if army.owner_id == faction_id
    }
    return seen


def _envoy_sight(world: WorldState, faction_id: FactionId) -> set[RegionId]:
    return {
        capital_region_id
        for envoy in world.envoys
        if envoy.from_faction_id == faction_id
        if (capital_region_id := world.factions[envoy.at_faction_id].capital_region_id)
        is not None
    }


def visible_regions(
    world: WorldState, faction_id: FactionId, index: MapIndex
) -> frozenset[RegionId]:
    if faction_id not in world.factions:
        return frozenset()
    sharing = {faction_id, *_allies_of(world, faction_id)}
    direct_sight = {
        region_id
        for sharer_id in sharing
        for region_id in _own_sight(world, index, sharer_id)
    }
    return frozenset(direct_sight | _envoy_sight(world, faction_id))


def _is_foreign(world: WorldState, faction_id: FactionId, other_id: FactionId) -> bool:
    if other_id == faction_id:
        return False
    return relation_status(world, faction_id, other_id) is not RelationStatus.ALLIANCE


def known_hazards(
    world: WorldState, faction_id: FactionId, index: MapIndex
) -> frozenset[RegionId]:
    # NOTE: only what is visible right now counts; FactionState.intel is not used
    # until the fog system fills it, so fogged regions are never guessed at.
    visible = visible_regions(world, faction_id, index)
    owned_by_others = {
        region_id
        for region_id in visible
        if region_id in world.regions
        and world.regions[region_id].owner_id is not None
        and _is_foreign(world, faction_id, world.regions[region_id].owner_id)
    }
    held_by_armies = {
        army.location_id
        for army in world.armies.values()
        if army.location_id in visible and _is_foreign(world, faction_id, army.owner_id)
    }
    return frozenset(owned_by_others | held_by_armies)
