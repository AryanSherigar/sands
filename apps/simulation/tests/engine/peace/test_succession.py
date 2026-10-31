import pytest
from app.engine.peace.hostages import hold_hostage
from app.engine.peace.succession import (
    leader_died,
    renew_treaty,
    repudiate_treaty,
)
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import TruceState
from strategy_contracts.peace import PeaceTier
from strategy_contracts.terms import HostageTerm

from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    kill_leader,
    make_world,
)

TUNING = SCENARIO.tuning.peace
DIPLOMACY = SCENARIO.tuning.diplomacy


def _signed(world, tier: PeaceTier = PeaceTier.GENERATION) -> TruceState:
    first, second = sorted((PLAYER, WRATHFUL_RIVAL))
    truce = TruceState(
        id="truce_1",
        faction_a=first,
        faction_b=second,
        expires_turn=world.clock.turn + TUNING.tier_turns[tier],
        signed_turn=world.clock.turn,
        tier=tier,
        signatory_leader_ids=[
            world.factions[first].leader_id,
            world.factions[second].leader_id,
        ],
    )
    world.truces.append(truce)
    return truce


def _friendly(scenario=SCENARIO):
    scenario = scenario.model_copy(deep=True)
    scenario.negotiation.base_accept = -100
    return scenario


def test_leader_death_lapses_a_signed_truce_to_short() -> None:
    world = make_world()
    truce = _signed(world)
    dead = world.factions[WRATHFUL_RIVAL].leader_id

    events = kill_leader(world, SCENARIO, dead)

    assert truce.tier is TUNING.renewal_short_tier
    assert truce.expires_turn == world.clock.turn + TUNING.tier_turns[truce.tier]
    assert truce.is_fragile
    assert world.peace.lapses[0].original_tier is PeaceTier.GENERATION
    assert [event.kind for event in events] == ["treaty_lapsed"]


def test_unrelated_leader_death_changes_nothing() -> None:
    world = make_world()
    truce = _signed(world)
    outsider = world.factions[CAUTIOUS_RIVAL].leader_id
    before = world.model_dump_json()

    events = leader_died(world, SCENARIO, outsider)

    assert events == []
    assert world.model_dump_json() == before
    assert truce.tier is PeaceTier.GENERATION


def test_second_death_call_is_a_noop() -> None:
    world = make_world()
    _signed(world)
    dead = world.factions[WRATHFUL_RIVAL].leader_id
    leader_died(world, SCENARIO, dead)
    after_first = world.model_dump_json()

    events = leader_died(world, SCENARIO, dead)

    assert events == []
    assert world.model_dump_json() == after_first


def test_hostage_is_released_when_the_treaty_lapses() -> None:
    world = make_world()
    truce = _signed(world)
    term = HostageTerm(
        giver_id=WRATHFUL_RIVAL,
        holder_id=PLAYER,
        leader_id=world.factions[WRATHFUL_RIVAL].leader_id,
        duration_turns=50,
    )
    hold_hostage(world, term, truce.id)

    leader_died(world, SCENARIO, world.factions[PLAYER].leader_id)

    assert world.peace.hostages == []


def test_renewal_restores_the_tier_when_the_counterpart_accepts() -> None:
    world = make_world()
    truce = _signed(world)
    leader_died(world, SCENARIO, world.factions[WRATHFUL_RIVAL].leader_id)

    renew_treaty(world, _friendly(), truce.id, WRATHFUL_RIVAL)

    assert truce.tier is PeaceTier.GENERATION
    assert truce.expires_turn == world.clock.turn + TUNING.tier_turns[truce.tier]
    assert world.peace.lapses == []


def test_renewal_is_refused_by_a_hostile_counterpart() -> None:
    world = make_world()
    truce = _signed(world)
    leader_died(world, SCENARIO, world.factions[WRATHFUL_RIVAL].leader_id)
    hostile = SCENARIO.model_copy(deep=True)
    hostile.negotiation.base_accept = 500

    with pytest.raises(CampaignProgressError) as error:
        renew_treaty(world, hostile, truce.id, WRATHFUL_RIVAL)

    assert error.value.code == "renewal_refused"
    assert truce.tier is TUNING.renewal_short_tier


def test_renewal_needs_a_lapse() -> None:
    world = make_world()
    truce = _signed(world)

    with pytest.raises(CampaignProgressError) as error:
        renew_treaty(world, _friendly(), truce.id, WRATHFUL_RIVAL)

    assert error.value.code == "no_lapse"


def test_repudiation_is_a_reduced_cost_breach() -> None:
    world = make_world()
    truce = _signed(world)
    leader_died(world, SCENARIO, world.factions[WRATHFUL_RIVAL].leader_id)
    before = world.factions[WRATHFUL_RIVAL].reputation

    repudiate_treaty(world, SCENARIO, truce.id, WRATHFUL_RIVAL)

    expected = DIPLOMACY.breach_reputation_cost * TUNING.repudiation_cost_percent // 100
    assert world.factions[WRATHFUL_RIVAL].reputation == before - expected
    assert world.truces == []
    assert world.peace.lapses == []
    assert [mark.faction_id for mark in world.oathbreakers] == [WRATHFUL_RIVAL]
