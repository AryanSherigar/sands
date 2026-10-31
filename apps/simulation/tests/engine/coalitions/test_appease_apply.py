from app.engine.coalitions.appease import apply_appease
from app.engine.coalitions.phase import lift_member_opinion_penalty
from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.opinion import opinion_of
from app.models.orders import AppeaseCoalitionOrder
from app.models.world_state import WorldState
from strategy_contracts.coalition import ClaimCessionOffer, GoldOffer, PactOffer
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.terms import NonAggressionTerm

from tests.engine.coalitions.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_coalition_world,
)
from tests.engine.diplomacy.builders import queue_npc_order, run_phase

TUNING = SCENARIO.tuning.coalition
ENOUGH_GOLD = 500


def _order(offer, member_id: str = WRATHFUL_RIVAL) -> AppeaseCoalitionOrder:
    return AppeaseCoalitionOrder(faction_id=PLAYER, member_id=member_id, offer=offer)


def _rich_world() -> WorldState:
    world = make_coalition_world()
    world.factions[PLAYER].treasury = ENOUGH_GOLD * 2
    return world


def _members(world: WorldState) -> list[str]:
    return (
        world.coalition.coalitions[0].member_ids if world.coalition.coalitions else []
    )


def _opinion(world: WorldState, holder_id: str) -> int:
    leader = world.leaders[world.factions[holder_id].leader_id]
    return opinion_of(leader, world.factions[PLAYER].leader_id)


def _claimed_region(world: WorldState) -> str:
    capital = world.factions[PLAYER].capital_region_id
    owned = sorted(k for k, r in world.regions.items() if r.owner_id == PLAYER)
    region_id = next(key for key in owned if key != capital)
    world.regions[region_id].claimant_ids = [WRATHFUL_RIVAL]
    return region_id


def test_accepted_gold_moves_treasury_and_member_leaves() -> None:
    world = _rich_world()
    before_player = world.factions[PLAYER].treasury
    before_member = world.factions[WRATHFUL_RIVAL].treasury

    events = apply_appease(world, SCENARIO, _order(GoldOffer(amount=ENOUGH_GOLD)))

    assert world.factions[PLAYER].treasury == before_player - ENOUGH_GOLD
    assert world.factions[WRATHFUL_RIVAL].treasury == before_member + ENOUGH_GOLD
    assert WRATHFUL_RIVAL not in _members(world)
    assert "coalition_appeased" in [event.kind for event in events]


def test_accepted_pact_creates_commitment_and_member_leaves() -> None:
    world = _rich_world()
    world.coalition.coalitions[0].member_ids = [WRATHFUL_RIVAL, CAUTIOUS_RIVAL]
    resentment_free = _order(PactOffer(duration_turns=TUNING.appease_max_pact_turns))
    world.leaders[world.factions[WRATHFUL_RIVAL].leader_id].opinions.clear()

    apply_appease(world, SCENARIO, resentment_free)

    pacts = [c for c in world.commitments if isinstance(c.term, NonAggressionTerm)]
    assert len(pacts) == 1
    assert WRATHFUL_RIVAL not in _members(world)


def test_accepted_cession_transfers_region_without_conquest() -> None:
    world = _rich_world()
    region_id = _claimed_region(world)
    world.regions[region_id].wealth = ENOUGH_GOLD
    conquests = len(world.coalition.conquests)
    standing = world.factions[PLAYER].model_copy(deep=True)
    world.grounds.append(_claim_ground(world, region_id))

    apply_appease(world, SCENARIO, _order(ClaimCessionOffer(region_id=region_id)))

    assert world.regions[region_id].owner_id == WRATHFUL_RIVAL
    assert WRATHFUL_RIVAL not in world.regions[region_id].claimant_ids
    assert len(world.coalition.conquests) == conquests
    assert world.factions[PLAYER].reputation == standing.reputation
    assert not [
        g
        for g in world.grounds
        if g.kind is GroundKind.CLAIM and g.region_id == region_id
    ]


def _claim_ground(world: WorldState, region_id: str):
    from app.engine.diplomacy.grounds import grant_ground

    return grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.CLAIM,
        holder_faction_id=WRATHFUL_RIVAL,
        target_faction_id=PLAYER,
        region_id=region_id,
    )


def test_lifting_a_penalty_touches_only_that_member() -> None:
    world = _rich_world()
    coalition = world.coalition.coalitions[0]
    cautious_before = _opinion(world, CAUTIOUS_RIVAL)
    wrathful_before = _opinion(world, WRATHFUL_RIVAL)

    lift_member_opinion_penalty(world, coalition, WRATHFUL_RIVAL)

    assert (
        _opinion(world, WRATHFUL_RIVAL)
        == wrathful_before + TUNING.member_opinion_penalty
    )
    assert _opinion(world, CAUTIOUS_RIVAL) == cautious_before


def test_leaving_restores_the_leavers_opinion() -> None:
    world = _rich_world()
    before = _opinion(world, WRATHFUL_RIVAL)

    apply_appease(world, SCENARIO, _order(GoldOffer(amount=ENOUGH_GOLD)))

    assert _opinion(world, WRATHFUL_RIVAL) == before + TUNING.member_opinion_penalty


def test_broken_promise_ground_removed_for_leaver_only() -> None:
    world = _rich_world()

    apply_appease(world, SCENARIO, _order(GoldOffer(amount=ENOUGH_GOLD)))

    holders = {
        g.holder_faction_id
        for g in world.grounds
        if g.kind is GroundKind.BROKEN_PROMISE and g.target_faction_id == PLAYER
    }
    assert WRATHFUL_RIVAL not in holders


def test_member_who_never_held_a_ground_still_leaves() -> None:
    world = _rich_world()
    world.grounds = [g for g in world.grounds if g.holder_faction_id != WRATHFUL_RIVAL]

    apply_appease(world, SCENARIO, _order(GoldOffer(amount=ENOUGH_GOLD)))

    assert WRATHFUL_RIVAL not in _members(world)


def test_refusal_charges_nothing_and_sets_cooldown() -> None:
    world = _rich_world()
    before = world.factions[PLAYER].treasury

    events = apply_appease(world, SCENARIO, _order(GoldOffer(amount=1)))

    assert world.factions[PLAYER].treasury == before
    assert WRATHFUL_RIVAL in _members(world)
    assert world.coalition.appease_cooldowns[f"{PLAYER}:{WRATHFUL_RIVAL}"] == (
        world.clock.turn + TUNING.appease_cooldown_turns
    )
    assert [event.kind for event in events] == ["coalition_appease_refused"]


def test_leaving_sets_a_rejoin_lockout() -> None:
    world = _rich_world()

    apply_appease(world, SCENARIO, _order(GoldOffer(amount=ENOUGH_GOLD)))

    assert world.coalition.rejoin_lockouts[f"{PLAYER}:{WRATHFUL_RIVAL}"] == (
        world.clock.turn + TUNING.appease_rejoin_lockout_turns
    )


def test_dropping_below_min_members_ends_the_coalition() -> None:
    world = _rich_world()

    events = apply_appease(world, SCENARIO, _order(GoldOffer(amount=ENOUGH_GOLD)))

    assert world.coalition.coalitions == []
    assert "coalition_ended_conceded" in [event.kind for event in events]
    assert _opinion(world, CAUTIOUS_RIVAL) is not None


def test_events_do_not_leak_price_or_value() -> None:
    world = _rich_world()

    events = apply_appease(world, SCENARIO, _order(GoldOffer(amount=ENOUGH_GOLD)))

    for event in events:
        assert set(event.cause.inputs) <= {"offer", "members"}


def test_second_offer_after_the_coalition_ended_fails_without_charge() -> None:
    world = _rich_world()
    first = _order(GoldOffer(amount=ENOUGH_GOLD))
    second = _order(GoldOffer(amount=ENOUGH_GOLD), CAUTIOUS_RIVAL)
    queued = queue_npc_order(queue_npc_order(world, SCENARIO, first), SCENARIO, second)

    result = run_phase(DiplomacyPhase(), queued)

    expected = world.factions[PLAYER].treasury - ENOUGH_GOLD
    assert result.world.factions[PLAYER].treasury == expected


def test_treasury_dropped_since_acceptance_fails_without_payment() -> None:
    world = _rich_world()
    queued = queue_npc_order(world, SCENARIO, _order(GoldOffer(amount=ENOUGH_GOLD)))
    queued.factions[PLAYER].treasury = 1

    result = run_phase(DiplomacyPhase(), queued)

    assert result.world.factions[PLAYER].treasury == 1
    assert WRATHFUL_RIVAL in _members(result.world)


def test_destroyed_member_order_fails_without_charge() -> None:
    world = _rich_world()
    queued = queue_npc_order(world, SCENARIO, _order(GoldOffer(amount=ENOUGH_GOLD)))
    treasury = queued.factions[PLAYER].treasury
    queued.factions[WRATHFUL_RIVAL].is_destroyed = True
    queued.coalition.coalitions[0].member_ids = [CAUTIOUS_RIVAL]

    result = run_phase(DiplomacyPhase(), queued)

    assert result.world.factions[PLAYER].treasury == treasury
