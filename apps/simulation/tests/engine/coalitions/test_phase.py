from app.engine.coalitions.effects import coalition_shift
from app.engine.coalitions.phase import tick_coalitions
from app.engine.negotiation import acceptance_range
from app.engine.opinion import opinion_of

from tests.engine.coalitions.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_threat_world,
    make_world,
    resent,
)

TUNING = SCENARIO.tuning.coalition


def _kinds(events):
    return [event.kind for event in events]


def _hostile_world():
    world = make_threat_world()
    for _ in range(6):
        world.coalition.atrocities[PLAYER] = 10
    return world


def test_resentful_neighbours_form_a_coalition_against_a_threat() -> None:
    world = _hostile_world()

    events = tick_coalitions(world, SCENARIO)

    coalition = world.coalition.coalitions[0]
    assert coalition.target_id == PLAYER
    assert coalition.member_ids == sorted([CAUTIOUS_RIVAL, WRATHFUL_RIVAL])
    assert "coalition_formed" in _kinds(events)


def test_membership_lowers_opinion_and_grants_a_ground() -> None:
    world = _hostile_world()
    leader = world.leaders[world.factions[WRATHFUL_RIVAL].leader_id]
    before = opinion_of(leader, world.factions[PLAYER].leader_id)

    tick_coalitions(world, SCENARIO)

    after = opinion_of(leader, world.factions[PLAYER].leader_id)
    assert after == before - TUNING.member_opinion_penalty
    assert any(
        ground.holder_faction_id == WRATHFUL_RIVAL
        and ground.target_faction_id == PLAYER
        for ground in world.grounds
    )


def test_no_coalition_forms_without_resentment() -> None:
    world = make_world()
    world.coalition.atrocities[PLAYER] = 10

    assert tick_coalitions(world, SCENARIO) == []
    assert world.coalition.coalitions == []


def test_no_coalition_forms_below_the_join_threat() -> None:
    world = make_world()
    resent(world, WRATHFUL_RIVAL, PLAYER)
    resent(world, CAUTIOUS_RIVAL, PLAYER)

    assert tick_coalitions(world, SCENARIO) == []


def test_a_legacy_world_never_forms_coalitions() -> None:
    world = _hostile_world()
    world.coalition_ruleset = 0

    assert tick_coalitions(world, SCENARIO) == []


def test_a_coalition_ends_when_threat_falls_and_restores_opinion() -> None:
    world = _hostile_world()
    leader = world.leaders[world.factions[WRATHFUL_RIVAL].leader_id]
    tick_coalitions(world, SCENARIO)
    world.coalition.atrocities.clear()
    world.coalition.conquests.clear()

    events = tick_coalitions(world, SCENARIO)

    assert world.coalition.coalitions == []
    assert "coalition_ended_threat" in _kinds(events)
    assert not any(
        reason.cause.startswith("coalition:")
        for opinion in leader.opinions.values()
        for reason in opinion.reasons
    )


def test_a_coalition_is_renewed_at_expiry_while_threat_remains() -> None:
    world = _hostile_world()
    tick_coalitions(world, SCENARIO)
    coalition = world.coalition.coalitions[0]
    world.clock.turn = coalition.expires_turn

    events = tick_coalitions(world, SCENARIO)

    assert world.coalition.coalitions == [coalition]
    assert coalition.expires_turn == world.clock.turn + TUNING.duration_turns
    assert "coalition_renewed" in _kinds(events)


def test_a_war_between_members_splits_the_coalition() -> None:
    world = _hostile_world()
    tick_coalitions(world, SCENARIO)
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=CAUTIOUS_RIVAL)

    events = tick_coalitions(world, SCENARIO)

    assert world.coalition.coalitions == []
    assert "coalition_ended_split" in _kinds(events)


def test_warring_candidates_do_not_form_a_coalition() -> None:
    world = _hostile_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=CAUTIOUS_RIVAL)

    tick_coalitions(world, SCENARIO)

    assert world.coalition.coalitions == []


def test_peace_is_harder_for_the_target_with_a_member() -> None:
    world = _hostile_world()
    before = acceptance_range(world, SCENARIO, PLAYER, WRATHFUL_RIVAL).accept_at
    tick_coalitions(world, SCENARIO)

    after = acceptance_range(world, SCENARIO, PLAYER, WRATHFUL_RIVAL).accept_at

    assert after - before >= TUNING.peace_shift
    assert (
        coalition_shift(world, SCENARIO, PLAYER, WRATHFUL_RIVAL) == TUNING.peace_shift
    )


def test_shift_is_zero_for_non_members_and_other_directions() -> None:
    world = _hostile_world()
    tick_coalitions(world, SCENARIO)

    assert coalition_shift(world, SCENARIO, WRATHFUL_RIVAL, PLAYER) == 0
    assert coalition_shift(world, SCENARIO, PLAYER, PLAYER) == 0


def test_member_who_left_cannot_be_recruited_until_lockout_ends() -> None:
    from app.engine.coalitions.appease import apply_appease
    from app.models.orders import AppeaseCoalitionOrder
    from strategy_contracts.coalition import GoldOffer

    world = _hostile_world()
    tick_coalitions(world, SCENARIO)
    world.factions[PLAYER].treasury = 1000
    order = AppeaseCoalitionOrder(
        faction_id=PLAYER, member_id=WRATHFUL_RIVAL, offer=GoldOffer(amount=1000)
    )
    apply_appease(world, SCENARIO, order)
    resent(world, WRATHFUL_RIVAL, PLAYER)

    tick_coalitions(world, SCENARIO)

    assert all(WRATHFUL_RIVAL not in c.member_ids for c in world.coalition.coalitions)

    world.clock.turn += TUNING.appease_rejoin_lockout_turns
    tick_coalitions(world, SCENARIO)

    assert any(WRATHFUL_RIVAL in c.member_ids for c in world.coalition.coalitions)


def _hoarded_world(player_gold: int):
    world = make_world()
    for faction_id, faction in world.factions.items():
        faction.treasury = player_gold if faction_id == PLAYER else 0
    return world


def test_a_hoard_gives_neighbouring_rulers_a_pretext_for_war() -> None:
    world = _hoarded_world(player_gold=5000)

    tick_coalitions(world, SCENARIO)

    pretexts = [
        ground
        for ground in world.grounds
        if ground.target_faction_id == PLAYER and ground.kind.value == "broken_promise"
    ]
    assert pretexts
    assert all(ground.holder_faction_id != PLAYER for ground in pretexts)


def test_no_hoard_means_no_pretext() -> None:
    world = _hoarded_world(player_gold=0)

    tick_coalitions(world, SCENARIO)

    assert world.grounds == []
