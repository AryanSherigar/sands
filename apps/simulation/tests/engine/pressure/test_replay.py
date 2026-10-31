from app.engine.ai.headless import run_headless
from app.engine.hashing import world_hash
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.will import compute_will
from app.models.world_player import PlayerRuler
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns_expanded

SCENARIO = load_three_crowns_expanded()
RULER = PlayerRuler(
    name="Valdren", trait_ids=["honorable", "cautious"], ambition_ids=["ambition_peace"]
)
TURNS = 12
SEEDS = (3, 11)


def test_headless_games_replay_to_identical_hashes_and_pressure_state() -> None:
    for seed in SEEDS:
        first = run_headless(SCENARIO, seed, TURNS, RULER)
        second = run_headless(SCENARIO, seed, TURNS, RULER)

        assert first.final_hash == second.final_hash
        assert first.final_world.pressure == second.final_world.pressure


def test_readings_stay_bounded_across_a_long_ai_game() -> None:
    world = run_headless(SCENARIO, SEEDS[0], TURNS, RULER).final_world
    assert world is not None

    for faction_id in world.factions:
        strain = compute_strain(world, SCENARIO, faction_id).value
        will = compute_will(world, SCENARIO, faction_id)
        assert 0 <= strain <= 100
        assert 0 <= will.floor <= will.value <= 100 or will.value == 0


def test_pressure_state_survives_a_document_round_trip() -> None:
    world = run_headless(SCENARIO, SEEDS[1], TURNS, RULER).final_world
    assert world is not None

    restored = WorldState.model_validate(world.model_dump(mode="json"))

    assert world_hash(restored) == world_hash(world)
    assert restored.pressure == world.pressure
