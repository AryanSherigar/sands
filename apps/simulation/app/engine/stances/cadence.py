from app.models.world_clock import TURNS_PER_YEAR
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId, LeaderId

STANCE_INTERVAL_TURNS = TURNS_PER_YEAR


def leaders_due_for_stance(world: WorldState, due_turn: int) -> list[LeaderId]:
    return [
        leader_id
        for faction_id in sorted(world.factions)
        if (leader_id := _eligible_leader(world, faction_id)) is not None
        and _is_due(world, faction_id, due_turn)
    ]


def _eligible_leader(world: WorldState, faction_id: FactionId) -> LeaderId | None:
    faction = world.factions[faction_id]
    if faction.is_player or faction.is_destroyed or faction.leader_id is None:
        return None
    leader = world.leaders.get(faction.leader_id)
    if leader is None or not leader.is_alive:
        return None
    return leader.id


def _is_due(world: WorldState, faction_id: FactionId, due_turn: int) -> bool:
    stance = world.factions[faction_id].stance
    if stance.requested_for_turn == due_turn:
        return False
    if stance.option_id is None:
        return True
    return due_turn - stance.chosen_turn >= STANCE_INTERVAL_TURNS


def major_event_leaders(before: WorldState, after: WorldState) -> list[LeaderId]:
    """Leaders whose faction suffered a derivable shock between two world states."""
    affected = _capital_losers(before, after)
    affected |= _leader_changes(before, after)
    affected |= _new_war_factions(before, after)
    leaders = {
        leader_id
        for faction_id in affected
        if (leader_id := _eligible_leader(after, faction_id)) is not None
    }
    return sorted(leaders)


def _capital_losers(before: WorldState, after: WorldState) -> set[FactionId]:
    losers: set[FactionId] = set()
    for faction_id, faction in before.factions.items():
        capital = after.regions.get(faction.capital_region_id or "")
        if capital is not None and capital.owner_id != faction_id:
            losers.add(faction_id)
    return losers


def _leader_changes(before: WorldState, after: WorldState) -> set[FactionId]:
    return {
        faction_id
        for faction_id, faction in after.factions.items()
        if faction_id in before.factions
        and before.factions[faction_id].leader_id != faction.leader_id
    }


def _new_war_factions(before: WorldState, after: WorldState) -> set[FactionId]:
    previous = _war_pairs(before)
    return {faction_id for pair in _war_pairs(after) - previous for faction_id in pair}


def _war_pairs(world: WorldState) -> set[frozenset[FactionId]]:
    return {
        frozenset((relation.faction_a, relation.faction_b))
        for relation in world.relations
        if relation.status is RelationStatus.WAR
    }
