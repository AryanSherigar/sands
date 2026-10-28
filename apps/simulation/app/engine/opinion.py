from app.models.world_character import LeaderState, OpinionReason, OpinionState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId


def opinion_of(leader: LeaderState, target_id: str | None) -> int:
    opinion = leader.opinions.get(target_id) if target_id is not None else None
    return sum(reason.value for reason in opinion.reasons) if opinion else 0


def shift_opinion(
    world: WorldState,
    holder_faction_id: FactionId,
    target_faction_id: FactionId,
    cause: str,
    value: int,
    fade_per_turn: int,
) -> None:
    holder_id = world.factions[holder_faction_id].leader_id
    target_id = world.factions[target_faction_id].leader_id
    if holder_id is None or target_id is None:
        return
    opinions = world.leaders[holder_id].opinions
    opinion = opinions.setdefault(target_id, OpinionState(target_id=target_id))
    opinion.reasons.append(
        OpinionReason(cause=cause, value=value, fade_per_turn=fade_per_turn)
    )
