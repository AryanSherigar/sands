from app.engine.diplomacy.phase import TimePhase
from app.engine.outrage.ledger import raise_outrage, tick_outrage
from app.engine.outrage.status import is_enraged, is_mobilized, outrage_of
from strategy_contracts.scene import OutrageLevel

from tests.engine.diplomacy.builders import run_phase
from tests.engine.outrage.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    enrage,
    make_world,
)

TUNING = SCENARIO.tuning.outrage


def test_raising_outrage_records_who_caused_it() -> None:
    world = make_world()

    enrage(world, level=OutrageLevel.OFFENDED)

    state = outrage_of(world, WRATHFUL_RIVAL)
    assert state is not None
    assert state.level == OutrageLevel.OFFENDED
    assert state.target_faction_id == PLAYER


def test_legacy_worlds_and_disabled_scenarios_stay_calm() -> None:
    legacy = make_world()
    legacy.outrage_ruleset = 0
    enrage(legacy)
    quiet = make_world()
    quiet_scenario = SCENARIO.model_copy(deep=True)
    quiet_scenario.toggles.is_outrage_enabled = False
    raise_outrage(
        quiet,
        quiet_scenario,
        faction_id=WRATHFUL_RIVAL,
        offender_id=PLAYER,
        level=OutrageLevel.ENRAGED,
    )

    assert legacy.outrage == []
    assert quiet.outrage == []


def test_a_lower_level_never_cools_an_angrier_one() -> None:
    world = make_world()
    enrage(world)

    enrage(world, level=OutrageLevel.ANNOYED)

    assert is_enraged(world, WRATHFUL_RIVAL)


def test_only_outraged_and_enraged_mobilize() -> None:
    world = make_world()
    enrage(world, level=OutrageLevel.OFFENDED)
    assert not is_mobilized(world, WRATHFUL_RIVAL)

    enrage(world, level=OutrageLevel.OUTRAGED)

    assert is_mobilized(world, WRATHFUL_RIVAL)


def test_outrage_leaves_humiliation_memory_on_the_leader() -> None:
    world = make_world()

    enrage(world)

    expected = 4 * TUNING.humiliation_per_level
    assert world.pressure.humiliation[WRATHFUL_RIVAL] == expected


def test_enraged_fades_one_step_per_period_then_clears() -> None:
    world = make_world()
    enrage(world)

    for _ in range(TUNING.enraged_turns):
        world.clock.turn += 1
        tick_outrage(world, SCENARIO)
    state = outrage_of(world, WRATHFUL_RIVAL)

    assert state is not None
    assert state.level == OutrageLevel.OUTRAGED


def test_mobilization_outlasts_the_first_fade() -> None:
    world = make_world()
    enrage(world, level=OutrageLevel.OUTRAGED)

    world.clock.turn += TUNING.enraged_turns
    tick_outrage(world, SCENARIO)
    state = outrage_of(world, WRATHFUL_RIVAL)

    assert state is not None
    assert state.level == OutrageLevel.OFFENDED
    assert is_mobilized(world, WRATHFUL_RIVAL)


def test_a_calmed_unmobilized_faction_leaves_the_ledger() -> None:
    world = make_world()
    enrage(world, level=OutrageLevel.ANNOYED)

    world.clock.turn += TUNING.enraged_turns
    tick_outrage(world, SCENARIO)

    assert outrage_of(world, WRATHFUL_RIVAL) is None


def test_time_phase_fades_outrage_each_period() -> None:
    world = make_world()
    enrage(world)
    world.clock.turn += TUNING.enraged_turns

    result = run_phase(TimePhase(), world)

    state = outrage_of(result.world, WRATHFUL_RIVAL)
    assert state is not None
    assert state.level == OutrageLevel.OUTRAGED
    assert "outrage_faded" in [event.kind for event in result.events]
