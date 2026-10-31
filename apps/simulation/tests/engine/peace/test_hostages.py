from uuid import uuid4

import pytest
from app.engine.diplomacy.phase import TimePhase
from app.engine.peace.hostages import (
    harm_hostage,
    hold_hostage,
    release_due_hostages,
)
from app.engine.peace.signing import sign_peace
from app.engine.peace.truces import breach_agreements
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import TruceState
from strategy_contracts.peace import PeaceTier
from strategy_contracts.terms import HostageTerm

from tests.engine.diplomacy.builders import run_phase
from tests.engine.peace.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_peace_card,
    make_world,
    set_score,
)

DURATION = 5


def _term(world, giver: str = WRATHFUL_RIVAL, holder: str = PLAYER) -> HostageTerm:
    leader_id = world.factions[giver].leader_id
    return HostageTerm(
        giver_id=giver, holder_id=holder, leader_id=leader_id, duration_turns=DURATION
    )


def _truce(world) -> TruceState:
    first, second = sorted((PLAYER, WRATHFUL_RIVAL))
    truce = TruceState(
        id="truce_1",
        faction_a=first,
        faction_b=second,
        expires_turn=world.clock.turn + 20,
        tier=PeaceTier.MEDIUM,
    )
    world.truces.append(truce)
    return truce


def test_signing_with_a_hostage_term_creates_a_hostage() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [_term(world)])

    sign_peace(world, SCENARIO, card, uuid4())

    hostage = world.peace.hostages[0]
    assert (hostage.giver_id, hostage.holder_id) == (WRATHFUL_RIVAL, PLAYER)
    assert hostage.truce_id == world.truces[0].id
    assert hostage.release_turn == world.clock.turn + DURATION


def test_hostage_leader_from_another_faction_is_rejected() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    wrong = _term(world).model_copy(
        update={"leader_id": world.factions[PLAYER].leader_id}
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [wrong])

    with pytest.raises(CampaignProgressError) as error:
        sign_peace(world, SCENARIO, card, uuid4())

    assert error.value.code == "invalid_term"


def test_hostage_is_released_at_its_release_turn() -> None:
    world = make_world()
    truce = _truce(world)
    hold_hostage(world, _term(world), truce.id)
    world.clock.turn += DURATION

    events = release_due_hostages(world)

    assert world.peace.hostages == []
    assert [event.kind for event in events] == ["hostage_released"]


def test_hostage_is_released_when_the_truce_expires() -> None:
    world = make_world()
    world.clock.turn = 10
    truce = _truce(world)
    truce.expires_turn = 9
    hold_hostage(world, _term(world), truce.id)

    result = run_phase(TimePhase(), world)

    assert result.world.peace.hostages == []


def test_breach_by_the_giver_puts_the_hostage_at_mercy_without_harm() -> None:
    world = make_world()
    truce = _truce(world)
    hold_hostage(world, _term(world), truce.id)

    breach_agreements(world, SCENARIO, WRATHFUL_RIVAL, PLAYER)

    hostage = world.peace.hostages[0]
    assert hostage.is_at_mercy
    assert release_due_hostages(world) == []


def test_breach_by_the_holder_frees_the_hostage() -> None:
    world = make_world()
    truce = _truce(world)
    hold_hostage(world, _term(world), truce.id)

    breach_agreements(world, SCENARIO, PLAYER, WRATHFUL_RIVAL)

    assert world.peace.hostages == []


def test_harming_a_hostage_is_an_atrocity_and_a_breach() -> None:
    world = make_world()
    truce = _truce(world)
    hostage = hold_hostage(world, _term(world), truce.id)
    before = world.factions[PLAYER].reputation

    events = harm_hostage(world, SCENARIO, hostage.id, PLAYER)

    assert world.peace.hostages == []
    assert world.truces == []
    assert world.factions[PLAYER].reputation < before
    assert "hostage_harmed" in [event.kind for event in events]
    assert [mark.faction_id for mark in world.oathbreakers] == [PLAYER]


def test_harming_an_at_mercy_hostage_is_an_atrocity_without_a_second_breach() -> None:
    world = make_world()
    truce = _truce(world)
    hostage = hold_hostage(world, _term(world), truce.id)
    breach_agreements(world, SCENARIO, WRATHFUL_RIVAL, PLAYER)

    harm_hostage(world, SCENARIO, hostage.id, PLAYER)

    assert world.oathbreakers[0].faction_id == WRATHFUL_RIVAL
    assert len(world.oathbreakers) == 1


def test_hostage_of_a_destroyed_giver_lapses_cleanly() -> None:
    world = make_world()
    truce = _truce(world)
    hold_hostage(world, _term(world), truce.id)
    world.factions[WRATHFUL_RIVAL].is_destroyed = True

    release_due_hostages(world)

    assert world.peace.hostages == []


def test_hostage_whose_leader_is_gone_is_released() -> None:
    world = make_world()
    truce = _truce(world)
    term = _term(world)
    hold_hostage(world, term, truce.id)
    del world.leaders[term.leader_id]

    release_due_hostages(world)

    assert world.peace.hostages == []
