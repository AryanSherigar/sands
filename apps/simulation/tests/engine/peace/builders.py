from app.engine.pressure.shocks import record_shock
from app.models.world_diplomacy import RelationState, WarState
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.pressure import ShockKind
from strategy_contracts.terms import PeaceTerm, TermsCard

from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

__all__ = [
    "CAUTIOUS_RIVAL",
    "PLAYER",
    "SCENARIO",
    "WRATHFUL_RIVAL",
    "add_war",
    "break_will",
    "kill_leader",
    "make_peace_card",
    "make_world",
    "region_owned_by",
    "set_score",
    "set_war_relation",
]


def set_war_relation(world: WorldState, first: str, second: str) -> None:
    low, high = sorted((first, second))
    world.relations.append(
        RelationState(
            faction_a=low,
            faction_b=high,
            status=RelationStatus.WAR,
            since_turn=world.clock.turn,
        )
    )


def set_score(war: WarState, attacker: int, defender: int) -> WarState:
    war.war_score_attacker = attacker
    war.war_score_defender = defender
    return war


def region_owned_by(world: WorldState, faction_id: str) -> str:
    return next(
        key
        for key, region in sorted(world.regions.items())
        if region.owner_id == faction_id
    )


def make_peace_card(
    proposer_id: str,
    counterpart_id: str,
    terms: list,
    tier: str = "short",
    guarantor_ids: list[str] | None = None,
    is_white_peace: bool = False,
) -> TermsCard:
    peace = PeaceTerm(
        faction_a=proposer_id,
        faction_b=counterpart_id,
        tier=tier,
        guarantor_ids=guarantor_ids or [],
        is_white_peace=is_white_peace,
    )
    return TermsCard(
        proposer_id=proposer_id,
        counterpart_id=counterpart_id,
        terms=[peace, *terms],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )


def break_will(world: WorldState, faction_id: str, war_id: str) -> None:
    for kind in (ShockKind.CAPITAL_FALLS, ShockKind.RULER_CAPTURED):
        record_shock(world, SCENARIO, kind, faction_id, war_id)


def kill_leader(world: WorldState, scenario, leader_id: str):
    from app.engine.peace.succession import leader_died

    return leader_died(world, scenario, leader_id)
