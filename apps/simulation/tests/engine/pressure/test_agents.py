from app.engine.diplomacy.envoy import open_envoy
from app.engine.pressure.agents import (
    AGENT_NAMES,
    apply_pious_bonus,
    generate_agent,
)
from app.engine.rng import derive_rng
from app.models.orders import SendEnvoyOrder
from strategy_contracts.agents import AgentTrait, AgentTuning

from tests.engine.pressure.builders import CAUTIOUS_RIVAL, PLAYER, SCENARIO, make_world

MAX_LOYALTY = 100
SAMPLE_SIZE = 50


def _enabled_scenario():
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.agents.is_enabled = True
    return scenario


def _rng():
    return derive_rng(5, 1, "diplomacy")


def test_generate_agent_is_deterministic_for_same_seed_and_envoy() -> None:
    scenario = _enabled_scenario()

    first = generate_agent(scenario, _rng(), "envoy_1")
    second = generate_agent(scenario, _rng(), "envoy_1")

    assert first == second
    assert first.name in AGENT_NAMES
    assert len(first.traits) == 2
    assert first.bribed_by is None


def test_generate_agent_loyalty_within_bounds() -> None:
    scenario = _enabled_scenario()
    tuning = scenario.tuning.agents
    ceiling = min(MAX_LOYALTY, tuning.loyalty_max + tuning.pious_loyalty_bonus)

    for index in range(SAMPLE_SIZE):
        agent = generate_agent(scenario, _rng(), f"envoy_{index}")
        assert tuning.loyalty_min <= agent.loyalty <= ceiling


def test_generated_traits_never_pair_honest_with_deceitful() -> None:
    scenario = _enabled_scenario()

    for index in range(SAMPLE_SIZE):
        traits = set(generate_agent(scenario, _rng(), f"envoy_{index}").traits)
        assert not {AgentTrait.HONEST, AgentTrait.DECEITFUL} <= traits


def test_pious_agent_gets_loyalty_bonus() -> None:
    tuning = AgentTuning()

    assert apply_pious_bonus(50, [AgentTrait.PIOUS], tuning) == 65
    assert apply_pious_bonus(50, [AgentTrait.HONEST], tuning) == 50
    assert apply_pious_bonus(95, [AgentTrait.PIOUS], tuning) == MAX_LOYALTY


def test_open_envoy_without_agents_leaves_agent_none() -> None:
    world = make_world()
    order = SendEnvoyOrder(faction_id=PLAYER, target_faction_id=CAUTIOUS_RIVAL)

    open_envoy(world, order, SCENARIO, _rng())

    assert world.envoys[-1].agent is None


def test_open_envoy_with_agents_sets_agent() -> None:
    world = make_world()
    order = SendEnvoyOrder(faction_id=PLAYER, target_faction_id=CAUTIOUS_RIVAL)

    open_envoy(world, order, _enabled_scenario(), _rng())

    assert world.envoys[-1].agent is not None
