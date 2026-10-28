from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId


def war_enemies(world: WorldState, faction_id: FactionId) -> list[FactionId]:
    enemies: set[FactionId] = set()
    for war in world.wars:
        if war.attacker_id == faction_id:
            enemies.add(war.defender_id)
        if war.defender_id == faction_id:
            enemies.add(war.attacker_id)
    enemies |= _relation_enemies(world, faction_id)
    return sorted(enemies)


def _relation_enemies(world: WorldState, faction_id: FactionId) -> set[FactionId]:
    enemies: set[FactionId] = set()
    for relation in world.relations:
        if relation.status != RelationStatus.WAR:
            continue
        if relation.faction_a == faction_id:
            enemies.add(relation.faction_b)
        if relation.faction_b == faction_id:
            enemies.add(relation.faction_a)
    return enemies


def is_hostile(world: WorldState, faction_id: FactionId) -> bool:
    return bool(war_enemies(world, faction_id)) or any(
        item.holder_faction_id == faction_id for item in world.grounds
    )
