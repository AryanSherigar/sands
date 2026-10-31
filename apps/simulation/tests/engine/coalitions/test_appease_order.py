import pytest
from app.engine.coalitions.appease import validate_appease
from app.exceptions.command_exceptions import CommandError
from app.models.orders import AppeaseCoalitionOrder
from app.models.world_diplomacy import CommitmentState
from app.models.world_state import WorldState
from strategy_contracts.coalition import ClaimCessionOffer, GoldOffer, PactOffer
from strategy_contracts.terms import NonAggressionTerm

from tests.engine.coalitions.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_coalition_world,
    make_world,
)

GOLD = GoldOffer(amount=10)


def _order(offer=GOLD, member_id: str = WRATHFUL_RIVAL, faction_id: str = PLAYER):
    return AppeaseCoalitionOrder(
        faction_id=faction_id, member_id=member_id, offer=offer
    )


def _reason(world: WorldState, order: AppeaseCoalitionOrder) -> str:
    with pytest.raises(CommandError) as raised:
        validate_appease(world, SCENARIO, order)
    return raised.value.code


def _owned(world: WorldState, faction_id: str) -> list[str]:
    return sorted(k for k, r in world.regions.items() if r.owner_id == faction_id)


def test_valid_gold_offer_passes() -> None:
    world = make_coalition_world()
    world.factions[PLAYER].treasury = 100

    validate_appease(world, SCENARIO, _order())


def test_valid_pact_offer_passes() -> None:
    world = make_coalition_world()

    validate_appease(world, SCENARIO, _order(PactOffer(duration_turns=4)))


def test_valid_cession_passes() -> None:
    world = make_coalition_world()
    region_id = _claimed_region(world)

    validate_appease(world, SCENARIO, _order(ClaimCessionOffer(region_id=region_id)))


def _claimed_region(world: WorldState) -> str:
    capital = world.factions[PLAYER].capital_region_id
    region_id = next(key for key in _owned(world, PLAYER) if key != capital)
    world.regions[region_id].claimant_ids = [WRATHFUL_RIVAL]
    return region_id


def test_no_coalition_is_rejected() -> None:
    assert _reason(make_world(), _order()) == "no_coalition"


def test_non_member_is_rejected() -> None:
    world = make_coalition_world()
    world.coalition.coalitions[0].member_ids = [CAUTIOUS_RIVAL]

    assert _reason(world, _order()) == "not_member"


def test_cooldown_blocks_the_same_member() -> None:
    world = make_coalition_world()
    key = f"{PLAYER}:{WRATHFUL_RIVAL}"
    world.coalition.appease_cooldowns[key] = world.clock.turn + 2

    assert _reason(world, _order()) == "member_cooldown"


def test_unaffordable_gold_is_rejected() -> None:
    world = make_coalition_world()
    world.factions[PLAYER].treasury = 5

    assert _reason(world, _order()) == "cannot_afford"


def test_overlong_pact_is_rejected() -> None:
    world = make_coalition_world()
    order = AppeaseCoalitionOrder.model_construct(
        kind="appease_coalition",
        faction_id=PLAYER,
        member_id=WRATHFUL_RIVAL,
        offer=PactOffer.model_construct(kind="pact", duration_turns=99),
    )

    assert _reason(world, order) == "bad_offer"


def test_active_pact_blocks_a_pact_offer() -> None:
    world = make_coalition_world()
    world.commitments.append(
        CommitmentState(
            id="commitment_x",
            term=NonAggressionTerm(
                faction_a=sorted([PLAYER, WRATHFUL_RIVAL])[0],
                faction_b=sorted([PLAYER, WRATHFUL_RIVAL])[1],
                duration_turns=5,
            ),
            start_turn=world.clock.turn,
            end_turn=world.clock.turn + 5,
        )
    )

    assert _reason(world, _order(PactOffer(duration_turns=4))) == "pact_active"


def test_pact_offer_during_war_is_rejected() -> None:
    world = make_coalition_world()
    add_war(world, PLAYER, WRATHFUL_RIVAL)

    assert _reason(world, _order(PactOffer(duration_turns=4))) == "at_war"


def test_cession_of_unowned_region_is_rejected() -> None:
    world = make_coalition_world()
    other = _owned(world, CAUTIOUS_RIVAL)[0]

    assert _reason(world, _order(ClaimCessionOffer(region_id=other))) == "not_owned"


def test_cession_without_member_claim_is_rejected() -> None:
    world = make_coalition_world()
    capital = world.factions[PLAYER].capital_region_id
    region_id = next(key for key in _owned(world, PLAYER) if key != capital)
    world.regions[region_id].claimant_ids = []

    assert _reason(world, _order(ClaimCessionOffer(region_id=region_id))) == "no_claim"


def test_cession_of_the_capital_is_rejected() -> None:
    world = make_coalition_world()
    capital = world.factions[PLAYER].capital_region_id
    world.regions[capital].claimant_ids = [WRATHFUL_RIVAL]

    assert (
        _reason(world, _order(ClaimCessionOffer(region_id=capital))) == "capital_region"
    )
