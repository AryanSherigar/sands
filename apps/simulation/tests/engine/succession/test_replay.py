from app.engine.ai.headless import run_headless
from app.models.world_player import PlayerRuler
from strategy_contracts.examples import load_three_crowns_expanded
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import HealthBand, HeirSetup

RULER = PlayerRuler(
    name="Valdren", trait_ids=["honorable", "cautious"], ambition_ids=["ambition_peace"]
)
TURNS = 12
SEEDS = (3, 11)
DEADLY_PER_MILLE = 150


def _scenario(with_heirs: bool) -> StrategyScenario:
    scenario = load_three_crowns_expanded()
    scenario.tuning.succession = scenario.tuning.succession.model_copy(
        update={"death_per_mille": {band: DEADLY_PER_MILLE for band in HealthBand}}
    )
    if with_heirs:
        for setup in scenario.leaders:
            setup.heir = HeirSetup(
                id=f"heir_of_{setup.id}"[:40],
                name="Heir",
                trait_ids=["cruel", "proud"],
                ambition_ids=list(setup.ambition_ids[:1]),
                age=24,
            )
    return scenario


def _deaths(world) -> int:
    return sum(1 for leader in world.leaders.values() if not leader.is_alive)


def test_runs_with_authored_heirs_replay_to_identical_hashes() -> None:
    scenario = _scenario(with_heirs=True)
    for seed in SEEDS:
        first = run_headless(scenario, seed, TURNS, RULER)
        second = run_headless(scenario, seed, TURNS, RULER)

        assert first.final_hash == second.final_hash
        assert first.final_world.leaders == second.final_world.leaders
        assert _deaths(first.final_world) > 0


def test_runs_with_no_heirs_replay_to_identical_hashes_and_crises() -> None:
    scenario = _scenario(with_heirs=False)
    for seed in SEEDS:
        first = run_headless(scenario, seed, TURNS, RULER)
        second = run_headless(scenario, seed, TURNS, RULER)

        assert first.final_hash == second.final_hash
        assert first.final_world.succession == second.final_world.succession
        assert _deaths(first.final_world) > 0


def test_every_faction_keeps_a_living_seat_holder_through_a_deadly_run() -> None:
    world = run_headless(
        _scenario(with_heirs=False), SEEDS[0], TURNS, RULER
    ).final_world

    for faction in world.factions.values():
        if faction.leader_id is not None and not faction.is_destroyed:
            assert world.leaders[faction.leader_id].is_alive
