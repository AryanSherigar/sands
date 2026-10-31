from app.engine.diplomacy.phase import TimePhase
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.enums import TroopType

from tests.engine.outrage.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    enrage,
    make_world,
    set_axes,
)

CALCULATING = {"cunning": 3}
IMPULSIVE = {"cunning": 0}


def _hold(world, prisoner_id: str, origin: str = PLAYER) -> PrisonerState:
    prisoner = PrisonerState(
        id=prisoner_id,
        held_by_id=WRATHFUL_RIVAL,
        origin_faction_id=origin,
        kind=PrisonerKind.TROOPS,
        troop_count=10,
        origin_battle_id="battle_1",
        troops_by_type={TroopType.INFANTRY: 10},
    )
    world.prisoners.append(prisoner)
    return prisoner


def _scenario_with(world, axes: dict[str, int], per_turn: int | None = None):
    scenario = set_axes(world, SCENARIO, WRATHFUL_RIVAL, **axes)
    if per_turn is not None:
        scenario.tuning.outrage.held_prisoner_executions_per_turn = per_turn
    return scenario


def _tick(world, scenario):
    context = PhaseContext(
        scenario=scenario,
        orders=(),
        rng=derive_rng(world.rng.seed, world.clock.turn, TimePhase.name.value),
        resolved_outcomes={},
        recorded_answers={},
    )
    return TimePhase().run(world.model_copy(deep=True), context)


def test_an_enraged_uncalculating_captor_executes_a_held_prisoner() -> None:
    world = make_world()
    enrage(world)
    _hold(world, "prisoner_1")
    scenario = _scenario_with(world, IMPULSIVE)

    result = _tick(world, scenario)

    assert result.world.prisoners == []
    assert "prisoner_executed" in [event.kind for event in result.events]
    assert result.world.coalition.atrocities.get(WRATHFUL_RIVAL, 0) > 0


def test_a_calculating_captor_keeps_its_prisoners() -> None:
    world = make_world()
    enrage(world)
    _hold(world, "prisoner_1")
    scenario = _scenario_with(world, CALCULATING)

    result = _tick(world, scenario)

    assert len(result.world.prisoners) == 1


def test_an_unenraged_captor_keeps_its_prisoners() -> None:
    world = make_world()
    _hold(world, "prisoner_1")
    scenario = _scenario_with(world, IMPULSIVE)

    result = _tick(world, scenario)

    assert len(result.world.prisoners) == 1


def test_only_the_per_turn_cap_is_executed_oldest_first() -> None:
    world = make_world()
    enrage(world)
    _hold(world, "prisoner_2")
    _hold(world, "prisoner_1")
    scenario = _scenario_with(world, IMPULSIVE, per_turn=1)

    result = _tick(world, scenario)

    assert [item.id for item in result.world.prisoners] == ["prisoner_2"]


def test_a_legacy_outrage_world_does_not_execute_held_prisoners() -> None:
    world = make_world()
    enrage(world)
    world.outrage_ruleset = 1
    _hold(world, "prisoner_1")
    scenario = _scenario_with(world, IMPULSIVE)

    result = _tick(world, scenario)

    assert len(result.world.prisoners) == 1
