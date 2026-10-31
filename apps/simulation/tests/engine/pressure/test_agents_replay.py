import pytest
from app.engine.ai.headless import run_headless
from app.models.world_player import PlayerRuler
from strategy_contracts.examples import load_three_crowns_expanded

SEED = 11
TURNS = 16
RICH_TREASURY = 20000
RULER = PlayerRuler(
    name="Valdren", trait_ids=["honorable", "cautious"], ambition_ids=["ambition_peace"]
)


def _scenario(is_enabled: bool):
    scenario = load_three_crowns_expanded()
    scenario.tuning.agents.is_enabled = is_enabled
    for faction in scenario.factions:
        faction.treasury = RICH_TREASURY
    return scenario


@pytest.fixture(scope="module")
def first_run():
    return run_headless(_scenario(True), SEED, TURNS, RULER)


def test_same_seed_gives_same_agents_reports_and_bribes(first_run) -> None:
    second = run_headless(_scenario(True), SEED, TURNS, RULER)

    assert second.final_hash == first_run.final_hash
    assert second.final_world.envoys == first_run.final_world.envoys
    assert second.final_world.pressure.rumors == first_run.final_world.pressure.rumors


def test_a_rich_rival_actually_bribes_an_envoy_in_a_full_game(first_run) -> None:
    envoys = first_run.final_world.envoys

    assert any(envoy.agent for envoy in envoys)
    assert any(envoy.agent and envoy.agent.bribed_by for envoy in envoys)


def test_disabled_agents_leave_every_envoy_agentless() -> None:
    report = run_headless(_scenario(False), SEED, TURNS, RULER)

    assert report.final_world.envoys
    assert all(envoy.agent is None for envoy in report.final_world.envoys)
