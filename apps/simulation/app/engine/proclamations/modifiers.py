from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId


def active_modifier(world: WorldState, faction_id: FactionId, key: str) -> int:
    """An edict binds the player's realm only, and only while it has turns left."""
    faction = world.factions.get(faction_id)
    active = world.active_proclamation
    if faction is None or not faction.is_player:
        return 0
    if active is None or active.remaining_turns <= 0:
        return 0
    return active.ongoing_modifiers.get(key, 0)
