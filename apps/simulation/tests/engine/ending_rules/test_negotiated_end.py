from app.engine.ending_rules.negotiated_end import is_negotiated_end
from app.engine.ending_rules.streaks import advance_ending_streaks

from tests.engine.ending_rules.builders import (
    CAUTIOUS_RIVAL,
    add_truce,
    add_war,
    make_world,
    scenario_with,
)

SCENARIO = scenario_with(negotiated_min_truce_turns=8)


def _peaceful_after_war():
    world = make_world()
    add_war(world)
    advance_ending_streaks(world, SCENARIO)
    world.wars.clear()
    return world


def test_no_negotiated_end_before_any_war() -> None:
    world = make_world()
    add_truce(world, expires_in=20, guarantor_ids=[CAUTIOUS_RIVAL])
    assert not is_negotiated_end(world, SCENARIO)


def test_negotiated_end_needs_guaranteed_truce_of_min_length() -> None:
    world = _peaceful_after_war()
    add_truce(world, expires_in=8, guarantor_ids=[CAUTIOUS_RIVAL])
    assert is_negotiated_end(world, SCENARIO)


def test_short_truce_is_not_enough() -> None:
    world = _peaceful_after_war()
    add_truce(world, expires_in=7, guarantor_ids=[CAUTIOUS_RIVAL])
    assert not is_negotiated_end(world, SCENARIO)


def test_unguaranteed_truce_is_not_enough() -> None:
    world = _peaceful_after_war()
    add_truce(world, expires_in=20, guarantor_ids=[])
    assert not is_negotiated_end(world, SCENARIO)


def test_negotiated_end_false_while_any_war_active() -> None:
    world = _peaceful_after_war()
    add_truce(world, expires_in=20, guarantor_ids=[CAUTIOUS_RIVAL])
    add_war(world, war_id="war_2")
    assert not is_negotiated_end(world, SCENARIO)
