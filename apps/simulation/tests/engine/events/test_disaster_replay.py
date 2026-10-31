import pytest
from app.engine.ai.headless import OBSERVER_FACTION_ID, run_headless
from app.models.world_player import PlayerRuler
from strategy_contracts.event_catalog import DISASTER_EVENTS
from strategy_contracts.examples import load_three_crowns_expanded

RULER = PlayerRuler(
    name="Valdren", trait_ids=["honorable", "cautious"], ambition_ids=["ambition_peace"]
)
TURNS = 12
FULL_PERCENT = 100
HARVEST_START_MONTH = 8
SWEEP_SEEDS = range(1, 13)
SWEEP_TURNS = 8
DISASTER_IDS = {event.id for event in DISASTER_EVENTS}


def _forced_scenario():
    scenario = load_three_crowns_expanded()
    scenario.tuning.event_frequency_percent = FULL_PERCENT
    scenario.tuning.start_month = HARVEST_START_MONTH
    scenario.events = [
        event.model_copy(update={"chance_percent": FULL_PERCENT})
        for event in DISASTER_EVENTS
    ]
    return scenario


def _npc_disaster_memories(world):
    return [
        memory
        for memory in world.event_memories
        if memory.template_id in DISASTER_IDS
        and memory.subject_id != OBSERVER_FACTION_ID
    ]


def test_forced_disasters_replay_to_the_same_hash_and_memories() -> None:
    scenario = _forced_scenario()

    first = run_headless(scenario, 7, TURNS, RULER)
    second = run_headless(scenario, 7, TURNS, RULER)

    assert first.final_hash == second.final_hash
    assert first.final_world.event_memories == second.final_world.event_memories
    assert _npc_disaster_memories(first.final_world)


@pytest.mark.parametrize("seed", SWEEP_SEEDS)
def test_disaster_runs_complete_without_error(seed: int) -> None:
    report = run_headless(_forced_scenario(), seed, SWEEP_TURNS, RULER)

    assert report.turns_run > 0
