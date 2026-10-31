from dataclasses import dataclass
from enum import Enum

from app.engine.treaty.access import has_military_access
from app.models.world_army import ArmyState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import ArmyId, FactionId, RegionId


class ContactKind(str, Enum):
    NONE = "none"
    BATTLE = "battle"
    CONFRONTATION = "confrontation"
    ENEMY_REGION = "enemy_region"


@dataclass(frozen=True)
class Contact:
    kind: ContactKind
    defender_ids: tuple[ArmyId, ...] = ()


def relation_status(
    world: WorldState, left: FactionId, right: FactionId
) -> RelationStatus | None:
    low, high = sorted((left, right))
    for relation in world.relations:
        if (relation.faction_a, relation.faction_b) == (low, high):
            return relation.status
    return None


def _armies_in(
    world: WorldState, region_id: RegionId, excluding: ArmyState
) -> list[ArmyState]:
    return [
        army
        for army_id, army in sorted(world.armies.items())
        if army.location_id == region_id and army.owner_id != excluding.owner_id
    ]


def _is_friendly(world: WorldState, mover: FactionId, other: FactionId) -> bool:
    if relation_status(world, mover, other) is RelationStatus.ALLIANCE:
        return True
    return has_military_access(world, mover, other)


def _owner_contact(
    world: WorldState, mover: ArmyState, region_id: RegionId
) -> ContactKind:
    owner_id = world.regions[region_id].owner_id
    if owner_id is None or owner_id == mover.owner_id:
        return ContactKind.NONE
    status = relation_status(world, mover.owner_id, owner_id)
    if status is RelationStatus.WAR:
        return ContactKind.ENEMY_REGION
    if _is_friendly(world, mover.owner_id, owner_id):
        return ContactKind.NONE
    return ContactKind.CONFRONTATION


def classify_entry(world: WorldState, mover: ArmyState, region_id: RegionId) -> Contact:
    present = _armies_in(world, region_id, mover)
    statuses = {
        army.id: relation_status(world, mover.owner_id, army.owner_id)
        for army in present
    }
    friendly = {
        army.id
        for army in present
        if _is_friendly(world, mover.owner_id, army.owner_id)
    }
    hostile = tuple(
        army_id for army_id, status in statuses.items() if status is RelationStatus.WAR
    )
    if hostile:
        return Contact(ContactKind.BATTLE, hostile)
    if any(army_id not in friendly for army_id in statuses):
        return Contact(ContactKind.CONFRONTATION)
    return Contact(_owner_contact(world, mover, region_id))
