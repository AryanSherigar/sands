import json
import subprocess
import sys
from uuid import UUID

import pytest
from app.engine.movement import events
from app.engine.movement.phase import MovementPhase
from app.engine.pipeline import run_turn
from app.engine.world_init import new_world
from app.models.orders import QueuedOrder
from app.models.world_events import EventLogEntry, PhaseName, TurnStatus
from app.models.world_player import PlayerRuler
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.examples import load_three_crowns_expanded
from strategy_contracts.scenario import StrategyScenario

from tests.engine.movement.builders import halt_order, kinds, move_order
from tests.engine.toy_phases import toy_phases

PLAYTHROUGH_ID = UUID("55555555-5555-5555-5555-555555555555")
SEED = 20261104
SCENARIO = load_three_crowns_expanded()
PHASES = toy_phases({PhaseName.MOVEMENT: MovementPhase()})
WINTER_START_MONTH = 12
HOLD_TURNS = 12
GOLDEN_MARCH_HASHES = [
    "cdc137e1bf39367a8ace8889b4fab0b5fe0bd89d5b16abc1dcc1ea8cd74e0488",
    "5bf24583362700b8fa564790c84e3252ed20cb4b5e3af34771c01275e1ae23cd",
    "906db27422a8405db9ae1f51193bf8166d93246cf71f46d52213022424d9596b",
    "bc910cda20763e227104033f1a288f6123579d7b723e43787eaa19ede6adec77",
]


def _start(start_month: int | None = None) -> WorldState:
    ruler = PlayerRuler(
        name="Valdren",
        trait_ids=["honorable", "cautious"],
        ambition_ids=["ambition_peace"],
    )
    world = new_world(SCENARIO, PLAYTHROUGH_ID, SEED, "house_ashford", ruler)
    if start_month is not None:
        world.clock.start_month = start_month
    return world


def _set_status(world: WorldState, left: str, right: str, status) -> None:
    for relation in world.relations:
        if {relation.faction_a, relation.faction_b} == {left, right}:
            relation.status = status


def _turn(world: WorldState, orders: list[QueuedOrder]):
    result = run_turn(world, SCENARIO, orders, PHASES, {}, {})
    assert result.status is TurnStatus.RESOLVED
    return result.world, result.events


def _play(world, schedule: dict[int, list[QueuedOrder]], turns: int):
    history, log = [], []
    for turn in range(turns):
        world, turn_events = _turn(world, schedule.get(turn, []))
        history.append(world)
        log += turn_events
    return history, log


def _movement(log: list[EventLogEntry]) -> list[EventLogEntry]:
    return [entry for entry in log if entry.phase is PhaseName.MOVEMENT]


def test_a_road_march_on_the_ashford_map_takes_exactly_the_hand_computed_turns() -> (
    None
):
    order = move_order("o1", "army_ashford_2", "ashford", "house_ashford")
    spring, _ = _play(_start(), {0: [order]}, 1)
    winter, _ = _play(_start(WINTER_START_MONTH), {0: [order]}, 2)
    assert spring[0].armies["army_ashford_2"].location_id == "ashford"
    assert winter[0].armies["army_ashford_2"].location_id == "aldgate"
    assert winter[1].armies["army_ashford_2"].location_id == "ashford"


def test_the_cost_breakdown_a_player_would_read_is_in_the_event_log() -> None:
    order = move_order("o1", "army_ashford_2", "ashford", "house_ashford")
    _, log = _play(_start(WINTER_START_MONTH), {0: [order]}, 1)
    entry = next(e for e in _movement(log) if e.kind == events.ARMY_EN_ROUTE)
    assert entry.cause.inputs == {
        "base_cost": 100,
        "total_cost": 130,
        "adjust_road": -50,
        "adjust_winter": 50,
        "adjust_troop_mix": 30,
        "leg_progress": 100,
    }


def test_a_scripted_round_trip_follows_the_hand_computed_positions() -> None:
    schedule = {
        0: [move_order("o1", "army_ashford_2", "gull_point", "house_ashford")],
        2: [move_order("o2", "army_ashford_2", "aldgate", "house_ashford")],
    }
    history, _ = _play(_start(), schedule, 4)
    positions = [state.armies["army_ashford_2"].location_id for state in history]
    assert positions == ["aldgate", "gull_point", "gull_point", "aldgate"]


def test_an_army_is_stopped_at_the_border_of_a_neighbour_it_is_at_peace_with() -> None:
    order = move_order("o1", "army_ashford_1", "carrow_vale", "house_ashford")
    history, log = _play(_start(), {0: [order]}, 3)
    assert events.BORDER_CONFRONTATION in kinds(_movement(log))
    assert history[-1].armies["army_ashford_1"].location_id == "ashford"
    assert history[-1].pending_battles == []


def test_the_same_march_at_war_ends_in_a_pending_battle_at_the_enemy_region() -> None:
    world = _start()
    _set_status(world, "house_ashford", "house_carrow", RelationStatus.WAR)
    order = move_order("o1", "army_ashford_1", "carrow_vale", "house_ashford")
    history, log = _play(world, {0: [order]}, 3)
    final = history[-1]
    assert events.CONTACT_BATTLE in kinds(_movement(log))
    battle = final.pending_battles[0]
    assert battle.region_id == "carrow_vale"
    assert battle.attacker_army_ids == ["army_ashford_1"]
    assert "army_carrow_1" in battle.defender_army_ids
    assert final.armies["army_ashford_1"].location_id == "carrow_vale"


def test_run_turn_leaves_the_world_it_was_given_untouched() -> None:
    world = _start()
    snapshot = world.model_dump()
    order = move_order("o1", "army_ashford_2", "ashford", "house_ashford")
    _turn(world, [order])
    assert world.model_dump() == snapshot


def test_halting_in_the_pipeline_leaves_the_army_on_the_road() -> None:
    schedule = {
        0: [move_order("o1", "army_dunwick_1", "fenwatch", "house_dunwick")],
        1: [halt_order("o2", "army_dunwick_1", "house_dunwick")],
    }
    history, _ = _play(_start(), schedule, 4)
    march = history[-1].armies["army_dunwick_1"].march
    assert history[-1].armies["army_dunwick_1"].location_id == "dunwick"
    assert march.is_halted is True
    assert march.leg_progress == history[1].armies["army_dunwick_1"].march.leg_progress


def test_event_sequence_numbers_stay_gapless_with_movement_events() -> None:
    schedule = {0: [move_order("o1", "army_ashford_2", "gull_point", "house_ashford")]}
    _, log = _play(_start(), schedule, 6)
    assert [entry.seq for entry in log] == list(range(1, len(log) + 1))


def _scripted_game(
    scenario: StrategyScenario = SCENARIO,
) -> tuple[list[str], list[EventLogEntry]]:
    schedule = {
        0: [move_order("o1", "army_ashford_2", "gull_point", "house_ashford")],
        2: [move_order("o2", "army_ashford_2", "aldgate", "house_ashford")],
        3: [move_order("o3", "army_dunwick_1", "fenwatch", "house_dunwick")],
    }
    world = _start()
    hashes: list[str] = []
    log: list[EventLogEntry] = []
    for turn in range(HOLD_TURNS):
        result = run_turn(world, scenario, schedule.get(turn, []), PHASES, {}, {})
        world = result.world
        hashes.append(result.world_hash)
        log += result.events
    return hashes, log


def test_a_scripted_game_replays_to_identical_hashes_and_events() -> None:
    first_hashes, first_log = _scripted_game()
    second_hashes, second_log = _scripted_game()
    assert first_hashes == second_hashes
    assert first_log == second_log


def test_a_changed_tuning_value_diverges_at_the_turn_marching_starts() -> None:
    baseline, _ = _scripted_game()
    movement = SCENARIO.tuning.movement.model_copy(
        update={"budget_per_turn": SCENARIO.tuning.movement.budget_per_turn + 1}
    )
    tuning = SCENARIO.tuning.model_copy(update={"movement": movement})
    altered, _ = _scripted_game(SCENARIO.model_copy(update={"tuning": tuning}))
    differing = [
        turn
        for turn, pair in enumerate(zip(baseline, altered, strict=True))
        if pair[0] != pair[1]
    ]
    assert differing[0] == 0


def test_a_scripted_game_matches_its_recorded_golden_hashes() -> None:
    # NOTE: update deliberately when movement rules, tuning defaults or the world
    # schema change; an accidental mismatch means replays of old games break.
    hashes, _ = _scripted_game()
    assert hashes[: len(GOLDEN_MARCH_HASHES)] == GOLDEN_MARCH_HASHES


def test_hashes_are_identical_in_a_fresh_interpreter() -> None:
    code = (
        "import sys, json; sys.path.insert(0, '.');"
        "from tests.engine.movement.test_scenarios import _scripted_game;"
        "print(json.dumps(_scripted_game()[0]))"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env={"PYTHONHASHSEED": "12345"},
    )
    assert json.loads(completed.stdout) == _scripted_game()[0]


@pytest.mark.parametrize("turns", [1, 5, 11])
def test_a_long_run_never_leaves_an_army_between_two_places(turns: int) -> None:
    schedule = {0: [move_order("o1", "army_ashford_2", "gull_point", "house_ashford")]}
    history, _ = _play(_start(), schedule, turns)
    for army in history[-1].armies.values():
        assert army.location_id in history[-1].regions
