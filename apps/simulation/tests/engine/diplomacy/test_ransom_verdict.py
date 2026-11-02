import pytest
from app.engine.diplomacy.prisoners import (
    PRISONER_RANSOM_COUNTERED,
    PRISONER_RANSOM_REFUSED,
    handle_prisoner,
    ransom_price,
)
from app.engine.diplomacy.ransom_verdict import (
    RansomResponse,
    ransom_verdict,
    ransom_willingness,
)
from app.models.orders import HandlePrisonerOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.enums import TroopType

from tests.engine.diplomacy.builders import set_traits
from tests.engine.peace.builders import PLAYER, SCENARIO, WRATHFUL_RIVAL, make_world

ORIGIN = WRATHFUL_RIVAL
TUNING = SCENARIO.tuning.peace
CALM = 100
RICH = 100000


def _scenario(**peace_fields: int):
    peace = TUNING.model_copy(update=peace_fields)
    tuning = SCENARIO.tuning.model_copy(update={"peace": peace})
    return SCENARIO.model_copy(update={"tuning": tuning})


def _troops(world, prisoner_id: str = "prisoner_1", count: int = 100):
    prisoner = PrisonerState(
        id=prisoner_id,
        held_by_id=PLAYER,
        origin_faction_id=ORIGIN,
        kind=PrisonerKind.TROOPS,
        troop_count=count,
        origin_battle_id="battle_1",
        troops_by_type={TroopType.INFANTRY: count},
    )
    world.prisoners.append(prisoner)
    return prisoner


def _calm_world(traits: list[str] | None = None):
    world = make_world()
    world.factions[ORIGIN].stability = CALM
    world.factions[ORIGIN].treasury = RICH
    set_traits(world, ORIGIN, traits or ["pragmatic"])
    return world


def _verdict(world, prisoner, scenario=SCENARIO):
    return ransom_verdict(
        world, scenario, prisoner, ransom_price(prisoner, scenario.tuning.peace)
    )


def test_a_calm_realm_haggles_rather_than_paying_full_price() -> None:
    world = _calm_world()
    prisoner = _troops(world)

    verdict = _verdict(world, prisoner)

    assert verdict.response is RansomResponse.HAGGLE
    price = ransom_price(prisoner, TUNING)
    assert 0 < verdict.counter_gold < price


def test_a_realm_in_turmoil_pays_the_full_price() -> None:
    world = _calm_world()
    world.factions[ORIGIN].stability = 0
    prisoner = _troops(world)

    assert _verdict(world, prisoner).response is RansomResponse.ACCEPT


def test_a_realm_that_barely_values_the_captive_refuses() -> None:
    world = _calm_world()
    prisoner = _troops(world)
    scenario = _scenario(ransom_base_percent=0, ransom_haggle_floor_percent=60)

    assert _verdict(world, prisoner, scenario).response is RansomResponse.REFUSE


def test_honorable_ruler_is_more_willing_than_a_proud_one() -> None:
    honorable = _calm_world(["honorable"])
    proud = _calm_world(["proud"])
    first = _troops(honorable)
    second = _troops(proud)

    assert ransom_willingness(honorable, SCENARIO, first) > ransom_willingness(
        proud, SCENARIO, second
    )


def test_more_captives_in_enemy_hands_raise_willingness() -> None:
    few = _calm_world()
    many = _calm_world()
    _troops(few, "prisoner_1", 50)
    _troops(many, "prisoner_1", 50)
    _troops(many, "prisoner_2", 400)
    for world in (few, many):
        world.prisoners[0].held_since_turn = 0
        world.clock.turn = 10

    assert ransom_willingness(many, SCENARIO, many.prisoners[0]) > ransom_willingness(
        few, SCENARIO, few.prisoners[0]
    )


def test_a_captured_ruler_is_worth_more_than_a_troop_contingent() -> None:
    world = _calm_world()
    troops = _troops(world)
    ruler_id = world.factions[ORIGIN].leader_id
    ruler = PrisonerState(
        id="prisoner_ruler",
        held_by_id=PLAYER,
        origin_faction_id=ORIGIN,
        kind=PrisonerKind.CHARACTER,
        character_id=ruler_id,
    )
    world.prisoners.append(ruler)

    assert ransom_willingness(world, SCENARIO, ruler) > ransom_willingness(
        world, SCENARIO, troops
    )


def test_an_empty_treasury_caps_the_counter_at_what_they_can_pay() -> None:
    world = _calm_world()
    world.factions[ORIGIN].stability = 0
    world.factions[ORIGIN].treasury = 30
    prisoner = _troops(world, count=100)

    verdict = _verdict(world, prisoner)

    assert verdict.response is RansomResponse.HAGGLE
    assert verdict.counter_gold == 30


def test_a_penniless_realm_refuses_outright() -> None:
    world = _calm_world()
    world.factions[ORIGIN].treasury = 0
    prisoner = _troops(world)

    assert _verdict(world, prisoner).response is RansomResponse.REFUSE


def test_a_greedy_ruler_haggles_even_when_willing_to_pay_in_full() -> None:
    world = _calm_world(["pragmatic"])
    world.factions[ORIGIN].stability = 0
    prisoner = _troops(world)
    willingness = ransom_willingness(world, SCENARIO, prisoner)
    scenario = _scenario(ransom_greed_accept_step=willingness)

    assert _verdict(world, prisoner, scenario).response is RansomResponse.HAGGLE


def _order(action: str = "ransom") -> HandlePrisonerOrder:
    return HandlePrisonerOrder(
        faction_id=PLAYER, prisoner_id="prisoner_1", action=action
    )


def test_a_refused_ransom_changes_nothing_but_the_log() -> None:
    world = _calm_world()
    world.factions[ORIGIN].treasury = 0
    _troops(world)
    holder_before = world.factions[PLAYER].treasury

    events = handle_prisoner(world, SCENARIO, _order())

    assert [event.kind for event in events] == [PRISONER_RANSOM_REFUSED]
    assert len(world.prisoners) == 1
    assert world.factions[PLAYER].treasury == holder_before
    assert world.peace.ransom_counters == []


def test_a_haggle_queues_a_counter_offer_and_keeps_the_captive() -> None:
    world = _calm_world()
    prisoner = _troops(world)
    holder_before = world.factions[PLAYER].treasury

    events = handle_prisoner(world, SCENARIO, _order())

    assert [event.kind for event in events] == [PRISONER_RANSOM_COUNTERED]
    assert len(world.prisoners) == 1
    assert world.factions[PLAYER].treasury == holder_before
    counter = world.peace.ransom_counters[0]
    assert (counter.prisoner_id, counter.holder_id) == (prisoner.id, PLAYER)


def test_haggling_again_replaces_the_pending_counter() -> None:
    world = _calm_world()
    _troops(world)

    handle_prisoner(world, SCENARIO, _order())
    handle_prisoner(world, SCENARIO, _order())

    assert len(world.peace.ransom_counters) == 1


def test_legacy_ruleset_still_ransoms_automatically() -> None:
    world = make_world()
    world.peace_ruleset = 1
    _troops(world)

    handle_prisoner(world, SCENARIO, _order())

    assert world.prisoners == []


@pytest.mark.parametrize("action", ["release", "execute"])
def test_other_actions_never_consult_the_verdict(action: str) -> None:
    world = _calm_world()
    _troops(world)

    handle_prisoner(world, SCENARIO, _order(action))

    assert world.prisoners == []
    assert world.peace.ransom_counters == []
