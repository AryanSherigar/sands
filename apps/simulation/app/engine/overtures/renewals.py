from app.engine.negotiation import player_faction_id
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId


def _asking_faction(world: WorldState, truce_id: str) -> FactionId | None:
    truce = next((item for item in world.truces if item.id == truce_id), None)
    has_lapse = any(item.truce_id == truce_id for item in world.peace.lapses)
    if truce is None or not has_lapse:
        return None
    player_id = player_faction_id(world)
    npc_id = truce.faction_b if truce.faction_a == player_id else truce.faction_a
    faction = world.factions.get(npc_id)
    if faction is None or faction.is_destroyed or faction.is_player:
        return None
    if faction.leader_id is None or faction.leader_id not in world.leaders:
        return None
    return npc_id


def pending_renewals(world: WorldState) -> list[tuple[str, FactionId]]:
    """Queued lapsed treaties whose heir can still ask, as (truce id, asking faction), sorted by truce id."""
    pairs = [
        (truce_id, _asking_faction(world, truce_id))
        for truce_id in sorted(world.overture_renewals)
    ]
    return [(truce_id, npc_id) for truce_id, npc_id in pairs if npc_id is not None]


def prune_renewals(world: WorldState) -> None:
    world.overture_renewals = [truce_id for truce_id, _ in pending_renewals(world)]


def renewal_truce_id(world: WorldState, faction_id: FactionId) -> str | None:
    return next(
        (
            truce_id
            for truce_id, npc_id in pending_renewals(world)
            if npc_id == faction_id
        ),
        None,
    )
