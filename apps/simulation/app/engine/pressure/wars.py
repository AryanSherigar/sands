from app.models.world_diplomacy import WarSide, WarState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId


def wars_of(world: WorldState, faction_id: FactionId) -> list[WarState]:
    return sorted(
        (
            war
            for war in world.wars
            if faction_id in {war.attacker_id, war.defender_id, *war.participant_ids}
        ),
        key=lambda war: war.id,
    )


def side_of(war: WarState, faction_id: FactionId) -> WarSide | None:
    side = war.side_by_faction.get(faction_id)
    if side is not None:
        return side
    if faction_id == war.attacker_id:
        return WarSide.ATTACKER
    if faction_id == war.defender_id:
        return WarSide.DEFENDER
    return None


def opposing_ids(war: WarState, faction_id: FactionId) -> list[FactionId]:
    side = side_of(war, faction_id)
    if side is None:
        return []
    participants = {war.attacker_id, war.defender_id, *war.participant_ids}
    return sorted(
        other for other in participants if side_of(war, other) not in (None, side)
    )


def side_score(war: WarState, faction_id: FactionId) -> int:
    if side_of(war, faction_id) is WarSide.ATTACKER:
        return war.war_score_attacker
    return war.war_score_defender


def find_war(
    world: WorldState, faction_a: FactionId, faction_b: FactionId
) -> WarState | None:
    return next(
        (
            war
            for war in sorted(world.wars, key=lambda item: item.id)
            if faction_b in opposing_ids(war, faction_a)
        ),
        None,
    )
