from app.engine.alliances.signing import sign_alliance
from app.models.world_diplomacy import CommitmentState
from app.models.world_state import WorldState
from strategy_contracts.alliance import AllianceType
from strategy_contracts.terms import AllianceTerm, TermsCard

from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_peace_card,
    make_world,
    set_war_relation,
)

SCENE_ID = "00000000-0000-0000-0000-000000000001"

__all__ = [
    "CAUTIOUS_RIVAL",
    "PLAYER",
    "SCENARIO",
    "SCENE_ID",
    "WRATHFUL_RIVAL",
    "add_alliance",
    "add_war",
    "make_alliance_term",
    "make_party_card",
    "make_world",
    "set_war_relation",
]


def make_alliance_term(
    faction_a: str,
    faction_b: str,
    alliance_type: AllianceType = AllianceType.DEFENSIVE,
    duration_turns: int = 0,
    is_separate_peace_banned: bool = False,
) -> AllianceTerm:
    return AllianceTerm(
        faction_a=faction_a,
        faction_b=faction_b,
        alliance_type=alliance_type,
        duration_turns=duration_turns,
        is_separate_peace_banned=is_separate_peace_banned,
    )


def add_alliance(
    world: WorldState,
    faction_a: str,
    faction_b: str,
    alliance_type: AllianceType = AllianceType.DEFENSIVE,
    duration_turns: int = 0,
    is_separate_peace_banned: bool = False,
) -> CommitmentState:
    term = make_alliance_term(
        faction_a, faction_b, alliance_type, duration_turns, is_separate_peace_banned
    )
    sign_alliance(world, SCENARIO, term, SCENE_ID)
    return world.commitments[-1]


def make_party_card(
    proposer_id: str, counterpart_id: str, party_ids: list[str] | None = None
) -> TermsCard:
    card = make_peace_card(proposer_id, counterpart_id, [])
    card.terms[0] = card.terms[0].model_copy(update={"party_ids": party_ids or []})
    return card
