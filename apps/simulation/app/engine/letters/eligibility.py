from app.engine.diplomacy.validation import is_at_war
from app.engine.negotiation import player_faction_id
from app.engine.opinion import opinion_of
from app.models.world_character import LeaderState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.letters import LetterTopic


def _remembers_player(leader: LeaderState, player_leader_id: str) -> bool:
    has_memory = any(item.subject_id == player_leader_id for item in leader.memories)
    opinion = leader.opinions.get(player_leader_id)
    return has_memory or (opinion is not None and bool(opinion.reasons))


def _is_eligible(
    world: WorldState,
    faction_id: FactionId,
    player_id: FactionId,
    player_leader_id: str,
) -> bool:
    faction = world.factions[faction_id]
    leader = world.leaders.get(faction.leader_id) if faction.leader_id else None
    if faction_id == player_id or faction.is_destroyed or leader is None:
        return False
    if not leader.is_alive or is_at_war(world, faction_id, player_id):
        return False
    if world.letter_cooldowns.get(faction_id, 0) > world.clock.turn:
        return False
    return _remembers_player(leader, player_leader_id)


def eligible_senders(world: WorldState) -> list[FactionId]:
    player_id = player_faction_id(world)
    player_leader_id = world.factions[player_id].leader_id
    if player_leader_id is None:
        return []
    return [
        faction_id
        for faction_id in sorted(world.factions)
        if _is_eligible(world, faction_id, player_id, player_leader_id)
    ]


def _claims_player_region(
    world: WorldState, sender_id: FactionId, player_id: FactionId
) -> bool:
    return any(
        region.owner_id == player_id and sender_id in region.claimant_ids
        for region in world.regions.values()
    )


def letter_topic(world: WorldState, sender_faction_id: FactionId) -> LetterTopic:
    player_id = player_faction_id(world)
    sender = world.leaders[world.factions[sender_faction_id].leader_id]
    if opinion_of(sender, world.factions[player_id].leader_id) < 0:
        return LetterTopic.WARNING
    if _claims_player_region(world, sender_faction_id, player_id):
        return LetterTopic.BORDER_DISPUTE
    return LetterTopic.COURTESY
