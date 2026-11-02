from app.engine.diplomacy.prisoners import handle_prisoner
from app.engine.pressure.mercy import mercy_amount, mercy_total
from app.engine.pressure.shocks import record_shock
from app.engine.pressure.will import compute_will
from app.models.orders import HandlePrisonerOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.enums import TroopType
from strategy_contracts.pressure import ShockKind

from tests.engine.diplomacy.builders import set_traits
from tests.engine.pressure.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.peace
FREED = WRATHFUL_RIVAL


def _captive(world, count: int = 100) -> PrisonerState:
    prisoner = PrisonerState(
        id="prisoner_1",
        held_by_id=PLAYER,
        origin_faction_id=FREED,
        kind=PrisonerKind.TROOPS,
        troop_count=count,
        origin_battle_id="battle_1",
        troops_by_type={TroopType.INFANTRY: count},
    )
    world.prisoners.append(prisoner)
    return prisoner


def _release(world) -> None:
    order = HandlePrisonerOrder(
        faction_id=PLAYER, prisoner_id="prisoner_1", action="release"
    )
    handle_prisoner(world, SCENARIO, order)


def _world(traits: list[str]):
    world = make_world()
    world.pressure_ruleset = 1
    add_war(world)
    set_traits(world, FREED, traits)
    return world


def test_release_raises_releaser_reputation() -> None:
    world = _world(["pragmatic"])
    _captive(world)
    before = world.factions[PLAYER].reputation

    _release(world)

    assert world.factions[PLAYER].reputation == before + TUNING.release_reputation_gain


def test_release_eases_freed_factions_will() -> None:
    world = _world(["pragmatic"])
    _captive(world)
    before = compute_will(world, SCENARIO, FREED).value

    _release(world)
    reading = compute_will(world, SCENARIO, FREED)

    assert reading.factors["mercy"] < 0
    assert reading.value < before


def test_honorable_ruler_values_mercy_more_than_proud_one() -> None:
    honorable = _world(["honorable"])
    proud = _world(["proud"])
    for world in (honorable, proud):
        _captive(world)

    assert mercy_amount(honorable, SCENARIO, honorable.prisoners[0]) > mercy_amount(
        proud, SCENARIO, proud.prisoners[0]
    )


def test_desperate_faction_values_mercy_more_than_confident_one() -> None:
    desperate = _world(["pragmatic"])
    confident = _world(["pragmatic"])
    desperate.factions[FREED].stability = 10
    confident.factions[FREED].stability = 100
    for world in (desperate, confident):
        _captive(world)

    assert mercy_amount(desperate, SCENARIO, desperate.prisoners[0]) > mercy_amount(
        confident, SCENARIO, confident.prisoners[0]
    )


def test_bigger_release_earns_more_than_a_small_one() -> None:
    world = _world(["pragmatic"])
    large = _captive(world, count=500)
    small = large.model_copy(update={"id": "prisoner_2", "troop_count": 20})

    assert mercy_amount(world, SCENARIO, large) > mercy_amount(world, SCENARIO, small)


def test_mercy_fades_to_nothing_over_its_duration() -> None:
    world = _world(["pragmatic"])
    _captive(world)
    _release(world)
    fresh = mercy_total(world, SCENARIO, FREED)

    world.clock.turn += TUNING.mercy_duration_turns // 2
    midway = mercy_total(world, SCENARIO, FREED)
    world.clock.turn += TUNING.mercy_duration_turns

    assert fresh > midway > 0
    assert mercy_total(world, SCENARIO, FREED) == 0


def test_release_without_a_war_still_earns_reputation_but_no_mercy() -> None:
    world = make_world()
    world.pressure_ruleset = 1
    _captive(world)
    before = world.factions[PLAYER].reputation

    _release(world)

    assert world.pressure.mercies == []
    assert world.factions[PLAYER].reputation == before + TUNING.release_reputation_gain


def test_mercy_ends_with_the_war() -> None:
    world = _world(["pragmatic"])
    _captive(world)
    _release(world)
    world.wars.clear()

    assert mercy_total(world, SCENARIO, FREED) == 0


def _ruler_captive(world) -> PrisonerState:
    ruler = PrisonerState(
        id="prisoner_ruler",
        held_by_id=PLAYER,
        origin_faction_id=FREED,
        kind=PrisonerKind.CHARACTER,
        character_id=world.factions[FREED].leader_id,
    )
    world.prisoners.append(ruler)
    return ruler


def test_freeing_a_ruler_earns_more_mercy_than_freeing_any_noble() -> None:
    world = _world(["pragmatic"])
    ruler = _ruler_captive(world)
    noble = ruler.model_copy(update={"id": "prisoner_noble", "character_id": "x"})

    assert mercy_amount(world, SCENARIO, ruler) > mercy_amount(world, SCENARIO, noble)


def test_the_ruler_captured_shock_persists_after_the_ruler_is_freed() -> None:
    world = _world(["pragmatic"])
    ruler = _ruler_captive(world)
    record_shock(world, SCENARIO, ShockKind.RULER_CAPTURED, FREED, "war_1")
    held = compute_will(world, SCENARIO, FREED)

    handle_prisoner(
        world,
        SCENARIO,
        HandlePrisonerOrder(faction_id=PLAYER, prisoner_id=ruler.id, action="release"),
    )
    freed = compute_will(world, SCENARIO, FREED)

    assert freed.factors["shocks"] == held.factors["shocks"]
    assert freed.factors["mercy"] < 0
    assert freed.value <= held.value


def test_expired_mercy_records_are_dropped_from_the_world() -> None:
    from app.engine.pressure.captivity import tick_captivity

    world = _world(["pragmatic"])
    _captive(world)
    _release(world)
    assert len(world.pressure.mercies) == 1

    world.clock.turn += TUNING.mercy_duration_turns
    tick_captivity(world, SCENARIO)

    assert world.pressure.mercies == []
