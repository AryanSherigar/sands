from app.engine.pressure.wars import side_of
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId
from strategy_contracts.terms import PeaceTerm

FactionPair = tuple[FactionId, FactionId]


def signing_parties(peace: PeaceTerm) -> list[FactionId]:
    return sorted({peace.faction_a, peace.faction_b, *peace.party_ids})


def war_participants(war: WarState) -> list[FactionId]:
    return sorted({war.attacker_id, war.defender_id, *war.participant_ids})


def pair_is_at_war(
    world: WorldState, war: WarState, first: FactionId, second: FactionId
) -> bool:
    if not war.side_by_faction:
        return True
    pair = tuple(sorted((first, second)))
    relation = next(
        (item for item in world.relations if (item.faction_a, item.faction_b) == pair),
        None,
    )
    return relation is not None and relation.status == RelationStatus.WAR


def _opposing_pairs(
    world: WorldState, war: WarState, members: list[FactionId]
) -> list[FactionPair]:
    return [
        (first, second)
        for first in members
        for second in members
        if first < second
        and side_of(war, first) not in (None, side_of(war, second))
        and side_of(war, second) is not None
        and pair_is_at_war(world, war, first, second)
    ]


def open_pairs(
    world: WorldState, war: WarState, parties: list[FactionId]
) -> list[FactionPair]:
    return _opposing_pairs(world, war, parties)


def remaining_pairs(world: WorldState, war: WarState) -> list[FactionPair]:
    return _opposing_pairs(world, war, war_participants(war))


def check_parties(war: WarState, peace: PeaceTerm, parties: list[FactionId]) -> None:
    has_duplicates = len(peace.party_ids) != len(set(peace.party_ids))
    is_known = all(side_of(war, party) is not None for party in parties)
    is_opposed = side_of(war, peace.faction_a) is not side_of(war, peace.faction_b)
    if has_duplicates or not is_known or not is_opposed:
        raise CampaignProgressError("invalid peace parties", "invalid_term", 422)
