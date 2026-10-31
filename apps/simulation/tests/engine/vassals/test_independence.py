from uuid import uuid4

from app.engine.peace.signing import sign_peace
from app.engine.pressure.will import compute_will
from app.engine.vassals.consequences import apply_reply
from app.engine.vassals.registry import vassalage_of
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.vassal import DemandKind, DemandReply

from tests.engine.peace.builders import make_peace_card, set_score
from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    add_vassalage,
    make_demand,
    make_world,
)

TUNING = SCENARIO.tuning.vassal


def _rebellion(is_controlled: bool = False) -> tuple[WorldState, str]:
    world = make_world()
    commitment = add_vassalage(
        world, PLAYER, CAUTIOUS_RIVAL, tribute=20, is_controlled=is_controlled
    )
    demand = make_demand(commitment, DemandKind.TRIBUTE, 80)
    apply_reply(world, SCENARIO, demand, DemandReply.REBEL)
    return world, commitment.id


def test_rebel_reply_opens_a_war_with_an_independence_ground() -> None:
    world, commitment_id = _rebellion()

    [war] = world.wars

    assert (war.attacker_id, war.defender_id) == (CAUTIOUS_RIVAL, PLAYER)
    assert war.ground_kind is GroundKind.INDEPENDENCE
    assert world.vassal.independence_wars[war.id] == commitment_id


def test_rebellion_suspends_the_vassalage_without_charging_a_breach() -> None:
    world, commitment_id = _rebellion()

    commitment = next(c for c in world.commitments if c.id == commitment_id)

    assert commitment.status is CommitmentStatus.BREACHED
    assert vassalage_of(world, CAUTIOUS_RIVAL) is None
    assert all(mark.faction_id != CAUTIOUS_RIVAL for mark in world.oathbreakers)


def test_independence_war_ignores_foreign_policy_control() -> None:
    world, _ = _rebellion(is_controlled=True)

    assert len(world.wars) == 1


def test_independence_adds_will_bonus_while_the_rebellion_lasts() -> None:
    world, _ = _rebellion()

    rebel = compute_will(world, SCENARIO, CAUTIOUS_RIVAL)
    overlord = compute_will(world, SCENARIO, PLAYER)

    assert rebel.factors["independence"] == TUNING.independence_will_bonus
    assert "independence" not in overlord.factors


def test_peace_with_vassal_not_the_loser_releases_the_vassalage() -> None:
    world, _ = _rebellion()
    [war] = world.wars
    set_score(war, attacker=40, defender=0)
    card = make_peace_card(CAUTIOUS_RIVAL, PLAYER, [], tier="medium")

    sign_peace(world, SCENARIO, card, uuid4())

    assert world.wars == []
    assert vassalage_of(world, CAUTIOUS_RIVAL) is None
    assert world.vassal.independence_wars == {}


def test_defeated_rebel_stays_bound_and_the_old_commitment_stays_breached() -> None:
    world, commitment_id = _rebellion()
    [war] = world.wars
    set_score(war, attacker=0, defender=40)
    card = make_peace_card(PLAYER, CAUTIOUS_RIVAL, [], tier="medium")

    sign_peace(world, SCENARIO, card, uuid4())

    bound = vassalage_of(world, CAUTIOUS_RIVAL)
    assert bound is not None
    assert bound.id != commitment_id
    assert bound.term.tribute_share_percent == 20
    old = next(c for c in world.commitments if c.id == commitment_id)
    assert old.status is CommitmentStatus.BREACHED
    assert world.vassal.independence_wars == {}
