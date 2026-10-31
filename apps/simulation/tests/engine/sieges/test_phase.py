from app.engine.sieges.phase import SiegePhase
from app.models.world_events import PhaseName

from tests.engine.sieges.builders import (
    add_resolved_battle,
    make_siege_world,
    run_phase,
)


def test_phase_is_named_sieges() -> None:
    assert SiegePhase().name is PhaseName.SIEGES


def test_phase_is_a_noop_at_ruleset_zero() -> None:
    world = make_siege_world()
    world.siege_ruleset = 0
    add_resolved_battle(world)

    result = run_phase(SiegePhase(), world)

    assert result.world.sieges == []
    assert result.events == []


def test_phase_starts_a_siege_after_a_won_battle() -> None:
    world = make_siege_world()
    add_resolved_battle(world)

    result = run_phase(SiegePhase(), world)

    assert len(result.world.sieges) == 1
    assert [event.kind for event in result.events] == [
        "siege_started",
        "siege_progressed",
    ]
    assert {event.phase for event in result.events} == {PhaseName.SIEGES}


def test_phase_is_idempotent_for_the_same_input() -> None:
    world = make_siege_world()
    add_resolved_battle(world)

    first = run_phase(SiegePhase(), world)
    second = run_phase(SiegePhase(), world)

    assert first.world.model_dump() == second.world.model_dump()
    assert first.events == second.events
