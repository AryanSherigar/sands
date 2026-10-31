from app.engine.coalitions.phase import (
    COALITION_ENDED_CONCEDED,
    end_coalition,
    lift_member_opinion_penalty,
)
from app.engine.coalitions.registry import coalition_against
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.transfers import hand_over_region, pay_gold
from app.engine.opinion import opinion_of
from app.engine.pacts import has_active_pact, sign_pact
from app.engine.trait_axes import axis_totals
from app.exceptions.command_exceptions import CommandError
from app.models.orders import AppeaseCoalitionOrder
from app.models.world_coalition import CoalitionState, pair_key
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.coalition import (
    AppeaseOffer,
    ClaimCessionOffer,
    GoldOffer,
    PactOffer,
)
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.ids import FactionId
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import NonAggressionTerm, PayGoldTerm
from strategy_contracts.traits import TraitAxis


def member_price(
    world: WorldState,
    scenario: StrategyScenario,
    member_id: FactionId,
    target_id: FactionId,
) -> int:
    tuning = scenario.tuning.coalition
    leader = world.leaders[world.factions[member_id].leader_id]
    opinion = opinion_of(leader, world.factions[target_id].leader_id)
    resentment = max(0, tuning.join_opinion_below - opinion)
    totals = axis_totals(leader, scenario)
    price = tuning.appease_base_price + tuning.appease_opinion_weight * resentment
    price -= tuning.appease_caution_discount * totals.get(TraitAxis.CAUTION, 0)
    price += tuning.appease_pride_surcharge * totals.get(TraitAxis.PRIDE, 0)
    return max(0, price)


def offer_value(
    world: WorldState, scenario: StrategyScenario, offer: AppeaseOffer
) -> int:
    tuning = scenario.tuning.coalition
    if isinstance(offer, GoldOffer):
        return offer.amount * tuning.appease_gold_value_percent // FULL_SHARE_PERCENT
    if isinstance(offer, PactOffer):
        turns = min(offer.duration_turns, tuning.appease_max_pact_turns)
        return min(
            turns * tuning.appease_pact_value_per_turn, tuning.appease_pact_max_value
        )
    assert isinstance(offer, ClaimCessionOffer)
    return world.regions[offer.region_id].wealth // tuning.appease_cession_value_divisor


def does_member_accept(
    world: WorldState,
    scenario: StrategyScenario,
    member_id: FactionId,
    target_id: FactionId,
    offer: AppeaseOffer,
) -> bool:
    price = member_price(world, scenario, member_id, target_id)
    return offer_value(world, scenario, offer) >= price


HTTP_UNPROCESSABLE = 422


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def _is_at_war(world: WorldState, left_id: FactionId, right_id: FactionId) -> bool:
    return any(
        {war.attacker_id, war.defender_id} == {left_id, right_id} for war in world.wars
    )


def _validate_gold(world: WorldState, order: AppeaseCoalitionOrder) -> None:
    assert isinstance(order.offer, GoldOffer)
    if order.offer.amount > world.factions[order.faction_id].treasury:
        raise _reject("cannot_afford")


def _validate_pact(
    world: WorldState, scenario: StrategyScenario, order: AppeaseCoalitionOrder
) -> None:
    assert isinstance(order.offer, PactOffer)
    if order.offer.duration_turns > scenario.tuning.coalition.appease_max_pact_turns:
        raise _reject("bad_offer")
    if has_active_pact(world, order.faction_id, order.member_id):
        raise _reject("pact_active")
    if _is_at_war(world, order.faction_id, order.member_id):
        raise _reject("at_war")


def _validate_cession(world: WorldState, order: AppeaseCoalitionOrder) -> None:
    assert isinstance(order.offer, ClaimCessionOffer)
    region = world.regions.get(order.offer.region_id)
    if region is None or region.owner_id != order.faction_id:
        raise _reject("not_owned")
    if order.member_id not in region.claimant_ids:
        raise _reject("no_claim")
    if world.factions[order.faction_id].capital_region_id == order.offer.region_id:
        raise _reject("capital_region")


def validate_appease(
    world: WorldState, scenario: StrategyScenario, order: AppeaseCoalitionOrder
) -> None:
    if world.coalition_ruleset < 1:
        raise _reject("coalition_disabled")
    coalition = coalition_against(world, order.faction_id)
    if coalition is None:
        raise _reject("no_coalition")
    if order.member_id not in coalition.member_ids:
        raise _reject("not_member")
    cooldown = world.coalition.appease_cooldowns.get(
        pair_key(order.faction_id, order.member_id), 0
    )
    if cooldown > world.clock.turn:
        raise _reject("member_cooldown")
    if isinstance(order.offer, GoldOffer):
        _validate_gold(world, order)
    elif isinstance(order.offer, PactOffer):
        _validate_pact(world, scenario, order)
    else:
        _validate_cession(world, order)


COALITION_APPEASED = "coalition_appeased"
COALITION_APPEASE_REFUSED = "coalition_appease_refused"


def _deliver_offer(world: WorldState, order: AppeaseCoalitionOrder) -> None:
    offer = order.offer
    if isinstance(offer, GoldOffer):
        term = PayGoldTerm(
            payer_id=order.faction_id, payee_id=order.member_id, amount=offer.amount
        )
        pay_gold(world, term)
    elif isinstance(offer, PactOffer):
        first, second = sorted((order.faction_id, order.member_id))
        pact = NonAggressionTerm(
            faction_a=first, faction_b=second, duration_turns=offer.duration_turns
        )
        sign_pact(world, pact, None)
    else:
        hand_over_region(world, offer.region_id, order.faction_id, order.member_id)


def _drop_broken_promise_ground(
    world: WorldState, member_id: FactionId, target_id: FactionId
) -> None:
    world.grounds = [
        ground
        for ground in world.grounds
        if not (
            ground.kind is GroundKind.BROKEN_PROMISE
            and ground.holder_faction_id == member_id
            and ground.target_faction_id == target_id
        )
    ]


def _member_leaves(
    world: WorldState,
    scenario: StrategyScenario,
    coalition: CoalitionState,
    member_id: FactionId,
) -> None:
    key = pair_key(coalition.target_id, member_id)
    coalition.member_ids = [item for item in coalition.member_ids if item != member_id]
    lift_member_opinion_penalty(world, coalition, member_id)
    _drop_broken_promise_ground(world, member_id, coalition.target_id)
    lockout = scenario.tuning.coalition.appease_rejoin_lockout_turns
    world.coalition.rejoin_lockouts[key] = world.clock.turn + lockout


def apply_appease(
    world: WorldState, scenario: StrategyScenario, order: AppeaseCoalitionOrder
) -> list[EventLogEntry]:
    tuning = scenario.tuning.coalition
    coalition = coalition_against(world, order.faction_id)
    assert coalition is not None
    subjects = [order.faction_id, order.member_id]
    if not does_member_accept(
        world, scenario, order.member_id, order.faction_id, order.offer
    ):
        key = pair_key(order.faction_id, order.member_id)
        world.coalition.appease_cooldowns[key] = (
            world.clock.turn + tuning.appease_cooldown_turns
        )
        return [diplomacy_event(COALITION_APPEASE_REFUSED, subjects)]
    _deliver_offer(world, order)
    _member_leaves(world, scenario, coalition, order.member_id)
    events = [diplomacy_event(COALITION_APPEASED, subjects)]
    if len(coalition.member_ids) < tuning.min_members:
        events.append(end_coalition(world, coalition, COALITION_ENDED_CONCEDED))
    return events
