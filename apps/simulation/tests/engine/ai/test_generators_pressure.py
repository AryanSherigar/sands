from app.engine.ai.generators.pressure import appease_candidates, mobilize_candidates
from app.models.orders import AppeaseCoalitionOrder, MobilizeOrder
from app.models.world_coalition import CoalitionState
from app.models.world_diplomacy import RelationState, WarState
from app.models.world_region import OccupationState
from strategy_contracts.coalition import ClaimCessionOffer, GoldOffer, PactOffer
from strategy_contracts.enums import RelationStatus
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

TUNING = SCENARIO.tuning.ai
HEALTHY_STABILITY = 80


def _war(world, enemy: str = PLAYER) -> None:
    low, high = sorted((CAUTIOUS_RIVAL, enemy))
    world.relations = [
        RelationState(
            faction_a=low, faction_b=high, status=RelationStatus.WAR, since_turn=0
        )
    ]
    world.wars.append(
        WarState(
            id="war_x", attacker_id=CAUTIOUS_RIVAL, defender_id=enemy, started_turn=0
        )
    )
    world.factions[CAUTIOUS_RIVAL].stability = HEALTHY_STABILITY


def _occupy_own_region(world, occupier: str = PLAYER) -> None:
    region = next(
        item for item in world.regions.values() if item.owner_id == CAUTIOUS_RIVAL
    )
    region.occupation = OccupationState(occupier_id=occupier, siege_progress=0)


def _mobilize(world):
    return mobilize_candidates(world, SCENARIO, CAUTIOUS_RIVAL)


def test_no_mobilization_in_peace() -> None:
    assert _mobilize(make_world()) == []


def test_a_war_offers_mobilization_at_a_friction_cost() -> None:
    world = make_world()
    _war(world)
    world.armies.clear()
    candidates = [
        item for item in _mobilize(world) if isinstance(item.order, MobilizeOrder)
    ]
    assert len(candidates) == 1
    assert candidates[0].category is ScoreCategory.ATTACK
    assert candidates[0].base_score in (
        -TUNING.mobilize_friction,
        TUNING.mobilize_cornered_bonus - TUNING.mobilize_friction,
    )


def test_an_occupied_home_region_corners_the_ruler() -> None:
    calm = make_world()
    _war(calm)
    pressed = make_world()
    _war(pressed)
    _occupy_own_region(pressed)
    calm_score = _mobilize(calm)[0].base_score
    pressed_score = _mobilize(pressed)[0].base_score
    assert pressed_score == TUNING.mobilize_cornered_bonus - TUNING.mobilize_friction
    assert pressed_score >= calm_score


def test_no_mobilization_at_or_below_the_stability_floor() -> None:
    world = make_world()
    _war(world)
    world.factions[CAUTIOUS_RIVAL].stability = TUNING.low_stability
    assert _mobilize(world) == []


def test_the_pressure_toggle_disables_both_generators() -> None:
    world = make_world()
    _war(world)
    scenario = SCENARIO.model_copy(deep=True)
    scenario.toggles.is_ai_pressure_enabled = False
    assert mobilize_candidates(world, scenario, CAUTIOUS_RIVAL) == []
    assert appease_candidates(world, scenario, CAUTIOUS_RIVAL) == []


def _coalition(world, members: list[str] | None = None) -> None:
    world.coalition.coalitions.append(
        CoalitionState(
            id="coalition_1",
            target_id=CAUTIOUS_RIVAL,
            member_ids=members or [WRATHFUL_RIVAL],
            formed_turn=0,
            expires_turn=99,
        )
    )


def _appeasements(world, scenario=SCENARIO):
    return appease_candidates(world, scenario, CAUTIOUS_RIVAL)


def test_no_coalition_means_no_appeasement() -> None:
    assert _appeasements(make_world()) == []


def test_a_coalition_member_is_offered_the_cheapest_covering_offer() -> None:
    world = make_world()
    _coalition(world)
    candidates = _appeasements(world)
    assert len(candidates) == 1
    order = candidates[0].order
    assert isinstance(order, AppeaseCoalitionOrder)
    assert order.member_id == WRATHFUL_RIVAL
    assert candidates[0].category is ScoreCategory.ALLY
    assert candidates[0].base_score == TUNING.appease_bonus
    assert isinstance(order.offer, PactOffer | GoldOffer | ClaimCessionOffer)


def test_a_member_with_an_active_pact_is_not_offered_another_pact() -> None:
    world = make_world()
    _coalition(world)
    first = _appeasements(world)[0].order
    assert isinstance(first.offer, PactOffer)
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.coalition.appease_pact_max_value = 0
    offer = _appeasements(world, scenario)[0].order.offer
    assert not isinstance(offer, PactOffer)


def test_the_capital_is_never_offered_as_a_cession() -> None:
    world = make_world()
    _coalition(world)
    capital_id = world.factions[CAUTIOUS_RIVAL].capital_region_id
    world.regions[capital_id].claimant_ids = [WRATHFUL_RIVAL]
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.coalition.appease_pact_max_value = 0
    world.factions[CAUTIOUS_RIVAL].treasury = 0
    assert _appeasements(world, scenario) == []


def test_the_price_never_reads_the_members_traits() -> None:
    first = make_world()
    second = make_world()
    _coalition(first)
    _coalition(second)
    leader_id = second.factions[WRATHFUL_RIVAL].leader_id
    second.leaders[leader_id].trait_ids = ["cautious", "honorable"]
    assert [item.order for item in _appeasements(first)] == [
        item.order for item in _appeasements(second)
    ]
