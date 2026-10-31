from app.engine.pressure.bands import ORDERED_BANDS, to_band
from app.engine.pressure.rumors import file_rumors
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.will import compute_will
from app.engine.rng import derive_rng
from app.models.world_diplomacy import EnvoyState
from strategy_contracts.pressure import PressureBand, RumorTopic

from tests.engine.diplomacy.builders import set_traits
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)
from tests.engine.pressure.builders import (
    SCENARIO as BASE_SCENARIO,
)
from tests.engine.pressure.test_effects import _exhaust


def _scenario(report: int = 100, wrong: int = 0):
    scenario = BASE_SCENARIO.model_copy(deep=True)
    scenario.tuning.pressure.rumor_report_percent = report
    scenario.tuning.pressure.wrong_hint_base_percent = wrong
    return scenario


def _world():
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=CAUTIOUS_RIVAL)
    _exhaust(world, WRATHFUL_RIVAL)
    set_traits(world, PLAYER, ["pragmatic"])
    world.envoys.append(
        EnvoyState(id="envoy_1", from_faction_id=PLAYER, at_faction_id=WRATHFUL_RIVAL)
    )
    return world


def _rng():
    return derive_rng(11, 1, "pressure")


def _true_band(world, scenario, topic: RumorTopic) -> PressureBand:
    reading = (
        compute_will(world, scenario, WRATHFUL_RIVAL)
        if topic is RumorTopic.WILL
        else compute_strain(world, scenario, WRATHFUL_RIVAL)
    )
    return to_band(reading.value, scenario.tuning.pressure)


def test_rumor_names_true_band_when_hint_cannot_be_wrong() -> None:
    world, scenario = _world(), _scenario()

    file_rumors(world, scenario, _rng())

    rumors = {r.topic: r for r in world.pressure.rumors}
    assert rumors, "exhausted rival should produce at least one rumor"
    for topic, rumor in rumors.items():
        assert rumor.band is _true_band(world, scenario, topic)
        assert rumor.is_hint_wrong is False
        assert rumor.line_key == f"{topic.value}.{rumor.band.value}"
        assert (rumor.observer_id, rumor.about_faction_id) == (PLAYER, WRATHFUL_RIVAL)


def test_wrong_hint_is_adjacent_band_toward_the_middle_and_recorded() -> None:
    world, scenario = _world(), _scenario(wrong=100)

    file_rumors(world, scenario, _rng())

    assert world.pressure.rumors
    for rumor in world.pressure.rumors:
        true_band = _true_band(world, scenario, rumor.topic)
        gap = ORDERED_BANDS.index(true_band) - ORDERED_BANDS.index(rumor.band)
        assert rumor.is_hint_wrong is True
        assert abs(gap) == 1
        assert abs(ORDERED_BANDS.index(rumor.band) - 2) < abs(
            ORDERED_BANDS.index(true_band) - 2
        )


def test_replay_reproduces_identical_rumors() -> None:
    scenario = _scenario(report=50, wrong=50)
    first, second = _world(), _world()

    file_rumors(first, scenario, _rng())
    file_rumors(second, scenario, _rng())

    assert first.pressure.rumors == second.pressure.rumors


def test_no_rumor_when_every_band_is_medium() -> None:
    world, scenario = _world(), _scenario()
    scenario.tuning.pressure.band_thresholds = [-2, -1, 101, 102]

    file_rumors(world, scenario, _rng())

    assert world.pressure.rumors == []


def test_no_rumor_when_report_check_fails() -> None:
    world, scenario = _world(), _scenario(report=0)

    file_rumors(world, scenario, _rng())

    assert world.pressure.rumors == []


def test_no_rumor_about_a_faction_at_peace_or_destroyed() -> None:
    peaceful = make_world()
    peaceful.envoys.append(
        EnvoyState(id="envoy_1", from_faction_id=PLAYER, at_faction_id=CAUTIOUS_RIVAL)
    )
    ruined = _world()
    ruined.factions[WRATHFUL_RIVAL].is_destroyed = True

    file_rumors(peaceful, _scenario(), _rng())
    file_rumors(ruined, _scenario(), _rng())

    assert peaceful.pressure.rumors == []
    assert ruined.pressure.rumors == []


def test_rage_topic_is_never_filed_in_this_slice() -> None:
    world, scenario = _world(), _scenario()

    file_rumors(world, scenario, _rng())

    assert RumorTopic.RAGE not in {r.topic for r in world.pressure.rumors}


def test_second_source_converges_on_the_true_band() -> None:
    world, scenario = _world(), _scenario(wrong=100)
    world.envoys.append(
        EnvoyState(
            id="envoy_2", from_faction_id=CAUTIOUS_RIVAL, at_faction_id=WRATHFUL_RIVAL
        )
    )

    file_rumors(world, scenario, _rng())

    second = [r for r in world.pressure.rumors if r.envoy_id == "envoy_2"]
    assert second and all(not r.is_hint_wrong for r in second)


def test_old_rumors_are_pruned() -> None:
    world, scenario = _world(), _scenario()
    file_rumors(world, scenario, _rng())
    world.clock.turn += 50
    world.envoys.clear()

    file_rumors(world, scenario, _rng())

    assert world.pressure.rumors == []


def test_envoy_reports_a_high_threat_band_in_peacetime() -> None:
    world = make_world()
    world.coalition.atrocities[CAUTIOUS_RIVAL] = 60
    world.envoys.append(
        EnvoyState(id="envoy_1", from_faction_id=PLAYER, at_faction_id=CAUTIOUS_RIVAL)
    )

    file_rumors(world, _scenario(), _rng())

    [rumor] = world.pressure.rumors
    assert rumor.topic is RumorTopic.THREAT
    assert rumor.band in {PressureBand.HIGH, PressureBand.VERY_HIGH}
