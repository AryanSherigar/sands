from app.engine.diplomacy.phase import TimePhase
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.engine.succession.phase import tick_succession
from app.models.world_events import PhaseName
from app.models.world_state import WorldState
from hypothesis import given, settings
from hypothesis import strategies as st
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import HealthBand, HeirSetup

from tests.engine.succession.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_succession_world,
    tuned,
)

CERTAIN_DEATH = {band: 1000 for band in HealthBand}
FOCUSED_TURNS = 40


def _rng(world: WorldState):
    return derive_rng(world.rng.seed, world.clock.turn, PhaseName.TIME.value)


def _deadly() -> StrategyScenario:
    return tuned(SCENARIO, death_per_mille=CERTAIN_DEATH, max_death_per_mille=1000)


def test_phase_order_age_then_roll_then_crisis() -> None:
    world = make_succession_world()
    world.clock.start_month = 12
    world.clock.turn = 1
    rival = world.leaders[world.factions[WRATHFUL_RIVAL].leader_id]
    age_before = rival.age

    events = tick_succession(world, _deadly(), _rng(world))

    kinds = [event.kind for event in events]
    assert kinds.count("ruler_died") == 2
    assert rival.age == age_before + 1
    assert world.leaders[world.factions[PLAYER].leader_id].is_alive
    assert all(event.phase is PhaseName.TIME for event in events)


def test_legacy_worlds_do_nothing() -> None:
    world = make_succession_world()
    world.succession_ruleset = 0

    assert tick_succession(world, _deadly(), _rng(world)) == []


def test_time_phase_runs_succession() -> None:
    world = make_succession_world()
    context = PhaseContext(
        scenario=_deadly(),
        orders=(),
        rng=_rng(world),
        resolved_outcomes={},
        recorded_answers={},
    )

    result = TimePhase().run(world.model_copy(deep=True), context)

    assert [event.kind for event in result.events].count("ruler_died") == 2


def _seat_holder_is_alive(world: WorldState, faction_id: str) -> bool:
    leader_id = world.factions[faction_id].leader_id
    return leader_id is not None and world.leaders[leader_id].is_alive


@given(
    chance=st.integers(min_value=0, max_value=1000),
    has_heir=st.booleans(),
    seed=st.integers(min_value=1, max_value=10_000),
)
@settings(max_examples=25, deadline=None)
def test_no_faction_ever_without_seat_holder(
    chance: int, has_heir: bool, seed: int
) -> None:
    world = make_succession_world()
    world.rng.seed = seed
    scenario = tuned(
        SCENARIO,
        death_per_mille={band: chance for band in HealthBand},
        max_death_per_mille=1000,
    )
    if has_heir:
        for setup in scenario.leaders:
            setup.heir = HeirSetup(
                id=f"heir_of_{setup.id}"[:40],
                name="Heir",
                trait_ids=["cruel", "proud"],
                ambition_ids=list(setup.ambition_ids[:1]),
                age=20,
            )
    for _ in range(FOCUSED_TURNS):
        world.clock.turn += 1
        tick_succession(world, scenario, _rng(world))
        for faction_id in (PLAYER, CAUTIOUS_RIVAL, WRATHFUL_RIVAL):
            assert _seat_holder_is_alive(world, faction_id)
