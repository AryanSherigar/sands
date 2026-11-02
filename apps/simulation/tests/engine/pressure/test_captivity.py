from app.engine.diplomacy.prisoners import handle_prisoner
from app.engine.pressure.captivity import captive_drain, tick_captivity
from app.models.orders import HandlePrisonerOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.enums import TroopType

from tests.engine.pressure.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.peace
HOME = WRATHFUL_RIVAL


def _captive(world, prisoner_id: str = "prisoner_1", count: int = 100) -> PrisonerState:
    prisoner = PrisonerState(
        id=prisoner_id,
        held_by_id=PLAYER,
        origin_faction_id=HOME,
        kind=PrisonerKind.TROOPS,
        troop_count=count,
        origin_battle_id="battle_1",
        troops_by_type={TroopType.INFANTRY: count},
    )
    world.prisoners.append(prisoner)
    return prisoner


def _stability(world) -> int:
    return world.factions[HOME].stability


def test_held_captives_drain_their_home_factions_stability() -> None:
    world = make_world()
    _captive(world)
    before = _stability(world)

    tick_captivity(world, SCENARIO)

    assert _stability(world) < before


def test_drain_grows_the_longer_captives_are_held() -> None:
    world = make_world()
    _captive(world)
    tick_captivity(world, SCENARIO)
    early = captive_drain(world, SCENARIO, HOME)

    world.clock.turn += 8
    late = captive_drain(world, SCENARIO, HOME)

    assert late > early


def test_more_captives_drain_more() -> None:
    few = make_world()
    many = make_world()
    _captive(few, count=20)
    _captive(many, "prisoner_1", count=200)
    _captive(many, "prisoner_2", count=200)
    for world in (few, many):
        tick_captivity(world, SCENARIO)
        world.clock.turn += 4

    assert captive_drain(many, SCENARIO, HOME) > captive_drain(few, SCENARIO, HOME)


def test_drain_is_capped_per_turn() -> None:
    world = make_world()
    _captive(world, count=100000)
    tick_captivity(world, SCENARIO)
    world.clock.turn += 50

    assert captive_drain(world, SCENARIO, HOME) == TUNING.captive_drain_cap


def test_freeing_the_captive_ends_the_drain() -> None:
    world = make_world()
    add_war(world)
    _captive(world)
    tick_captivity(world, SCENARIO)
    order = HandlePrisonerOrder(
        faction_id=PLAYER, prisoner_id="prisoner_1", action="release"
    )
    handle_prisoner(world, SCENARIO, order)
    before = _stability(world)

    tick_captivity(world, SCENARIO)

    assert _stability(world) == before


def test_legacy_peace_ruleset_does_not_drain() -> None:
    world = make_world()
    world.peace_ruleset = 1
    _captive(world)
    before = _stability(world)

    tick_captivity(world, SCENARIO)

    assert _stability(world) == before
    assert world.prisoners[0].held_since_turn is None


def test_executing_a_captive_rallies_their_home() -> None:
    world = make_world()
    add_war(world)
    _captive(world)
    world.factions[HOME].stability = 50
    for army in world.armies.values():
        if army.owner_id == HOME:
            army.morale = 50
    order = HandlePrisonerOrder(
        faction_id=PLAYER, prisoner_id="prisoner_1", action="execute"
    )

    handle_prisoner(world, SCENARIO, order)

    assert _stability(world) == 50 + TUNING.martyr_stability_rally
    morales = [a.morale for a in world.armies.values() if a.owner_id == HOME]
    assert morales
    assert all(m == 50 + TUNING.martyr_morale_rally for m in morales)


def test_no_rally_under_legacy_peace_ruleset() -> None:
    world = make_world()
    world.peace_ruleset = 1
    add_war(world)
    _captive(world)
    world.factions[HOME].stability = 50
    order = HandlePrisonerOrder(
        faction_id=PLAYER, prisoner_id="prisoner_1", action="execute"
    )

    handle_prisoner(world, SCENARIO, order)

    assert _stability(world) == 50


def test_a_realm_with_captives_in_enemy_hands_accepts_terms_more_easily() -> None:
    from app.engine.negotiation import acceptance_range

    bare = make_world()
    held = make_world()
    _captive(held)
    tick_captivity(held, SCENARIO)
    held.clock.turn += 6

    plain = acceptance_range(bare, SCENARIO, PLAYER, HOME)
    pressed = acceptance_range(held, SCENARIO, PLAYER, HOME)

    assert pressed.accept_at < plain.accept_at


def test_the_talks_shift_is_zero_under_the_legacy_ruleset() -> None:
    from app.engine.negotiation import acceptance_range

    bare = make_world()
    held = make_world()
    held.peace_ruleset = 1
    _captive(held)
    held.clock.turn += 6

    assert (
        acceptance_range(held, SCENARIO, PLAYER, HOME).accept_at
        == acceptance_range(bare, SCENARIO, PLAYER, HOME).accept_at
    )
