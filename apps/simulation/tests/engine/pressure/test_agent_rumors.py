from app.engine.pressure.agents import (
    agent_wrong_chance,
    reported_band,
    soothing_shift,
)
from app.engine.pressure.rumors import file_rumors
from app.engine.rng import derive_rng
from app.models.world_diplomacy import AgentState, EnvoyState
from strategy_contracts.agents import AgentTrait, AgentTuning
from strategy_contracts.pressure import PressureBand, RumorTopic

from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)
from tests.engine.pressure.builders import SCENARIO as BASE_SCENARIO
from tests.engine.pressure.test_effects import _exhaust

TUNING = AgentTuning()
LOYALTY = 50


def _agent(*traits: AgentTrait, bribed_by: str | None = None) -> AgentState:
    return AgentState(
        name="Aldous", traits=list(traits), loyalty=LOYALTY, bribed_by=bribed_by
    )


def _scenario(very_high: bool = False):
    scenario = BASE_SCENARIO.model_copy(deep=True)
    scenario.tuning.agents.is_enabled = True
    scenario.tuning.pressure.rumor_report_percent = 100
    scenario.tuning.pressure.wrong_hint_base_percent = 0
    if very_high:
        scenario.tuning.pressure.band_thresholds = [-4, -3, -2, -1]
    return scenario


def _world(*agents: AgentState | None):
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=CAUTIOUS_RIVAL)
    _exhaust(world, WRATHFUL_RIVAL)
    senders = (PLAYER, CAUTIOUS_RIVAL)
    for index, agent in enumerate(agents):
        world.envoys.append(
            EnvoyState(
                id=f"envoy_{index + 1}",
                from_faction_id=senders[index],
                at_faction_id=WRATHFUL_RIVAL,
                agent=agent,
            )
        )
    return world


def _rng():
    return derive_rng(11, 1, "pressure")


def _by_envoy(world, topic: RumorTopic) -> dict[str, PressureBand]:
    return {
        rumor.envoy_id: rumor.band
        for rumor in world.pressure.rumors
        if rumor.topic is topic
    }


def test_soothing_shift_lowers_danger_topics_and_floors_at_very_low() -> None:
    assert soothing_shift(PressureBand.HIGH, RumorTopic.WILL, 2) is PressureBand.LOW
    assert (
        soothing_shift(PressureBand.LOW, RumorTopic.THREAT, 5) is PressureBand.VERY_LOW
    )


def test_soothing_shift_raises_weakness_topics_and_caps_at_very_high() -> None:
    assert (
        soothing_shift(PressureBand.MEDIUM, RumorTopic.STRAIN, 1) is PressureBand.HIGH
    )
    assert (
        soothing_shift(PressureBand.HIGH, RumorTopic.HEALTH, 5)
        is PressureBand.VERY_HIGH
    )


def test_honest_agent_lowers_wrong_chance() -> None:
    assert agent_wrong_chance(40, _agent(AgentTrait.HONEST), TUNING) == 25


def test_incompetent_agent_raises_wrong_chance() -> None:
    assert agent_wrong_chance(40, _agent(AgentTrait.INCOMPETENT), TUNING) == 60


def test_wrong_chance_is_clamped() -> None:
    assert agent_wrong_chance(5, _agent(AgentTrait.HONEST), TUNING) == 0
    assert agent_wrong_chance(95, _agent(AgentTrait.INCOMPETENT), TUNING) == 100


def test_bribed_agent_reports_two_steps_soother() -> None:
    bribed = _agent(AgentTrait.PIOUS, bribed_by=WRATHFUL_RIVAL)

    result = reported_band(PressureBand.VERY_HIGH, RumorTopic.WILL, bribed, TUNING)

    assert result is PressureBand.MEDIUM


def test_deceitful_agent_reports_one_step_soother() -> None:
    result = reported_band(
        PressureBand.HIGH, RumorTopic.WILL, _agent(AgentTrait.DECEITFUL), TUNING
    )

    assert result is PressureBand.MEDIUM


def test_plain_agent_reports_the_band_unchanged() -> None:
    result = reported_band(
        PressureBand.HIGH, RumorTopic.WILL, _agent(AgentTrait.PIOUS), TUNING
    )

    assert result is PressureBand.HIGH


def test_bribed_agent_files_nothing_when_poisoned_band_is_unremarkable() -> None:
    bribed = _agent(AgentTrait.PIOUS, bribed_by=WRATHFUL_RIVAL)
    world = _world(bribed)

    file_rumors(world, _scenario(very_high=True), _rng())

    assert _by_envoy(world, RumorTopic.WILL) == {}
    assert _by_envoy(world, RumorTopic.STRAIN) == {"envoy_1": PressureBand.VERY_HIGH}


def test_bribed_rumor_is_recorded_as_wrong() -> None:
    bribed = _agent(AgentTrait.PIOUS, bribed_by=WRATHFUL_RIVAL)
    world = _world(bribed)

    file_rumors(world, _scenario(), _rng())

    strain = [r for r in world.pressure.rumors if r.topic is RumorTopic.STRAIN]
    assert strain and all(r.is_hint_wrong for r in strain)


def test_honest_second_envoy_contradicts_bribed_first() -> None:
    bribed = _agent(AgentTrait.PIOUS, bribed_by=WRATHFUL_RIVAL)
    world = _world(bribed, _agent(AgentTrait.HONEST))

    file_rumors(world, _scenario(), _rng())

    strain = _by_envoy(world, RumorTopic.STRAIN)
    assert strain["envoy_1"] is not strain["envoy_2"]
    assert strain["envoy_2"] is PressureBand.HIGH


def test_disabled_agents_keep_corroboration_behavior() -> None:
    scenario = _scenario()
    scenario.tuning.agents.is_enabled = False
    scenario.tuning.pressure.wrong_hint_base_percent = 100
    bribed = _agent(AgentTrait.PIOUS, bribed_by=WRATHFUL_RIVAL)
    world = _world(bribed, None)

    file_rumors(world, scenario, _rng())

    second = [r for r in world.pressure.rumors if r.envoy_id == "envoy_2"]
    assert second and all(not r.is_hint_wrong for r in second)


def test_destroyed_target_files_nothing_with_agents_enabled() -> None:
    world = _world(_agent(AgentTrait.HONEST))
    world.factions[WRATHFUL_RIVAL].is_destroyed = True

    file_rumors(world, _scenario(), _rng())

    assert world.pressure.rumors == []
