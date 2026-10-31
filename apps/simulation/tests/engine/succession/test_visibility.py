from app.engine.pressure.rumors import file_rumors
from app.engine.rng import derive_rng
from app.models.api_world_view import OwnFactionView, RivalView
from app.models.world_diplomacy import EnvoyState
from app.models.world_state import WorldState
from strategy_contracts.pressure import PressureBand, RumorTopic
from strategy_contracts.scenario import StrategyScenario

from tests.engine.succession.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    leader_of,
    make_succession_world,
)


def _scenario(report: int = 100, wrong: int = 0) -> StrategyScenario:
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.pressure.rumor_report_percent = report
    scenario.tuning.pressure.wrong_hint_base_percent = wrong
    return scenario


def _world(rival_age: int) -> WorldState:
    world = make_succession_world()
    leader_of(world, WRATHFUL_RIVAL).age = rival_age
    world.envoys.append(
        EnvoyState(id="envoy_1", from_faction_id=PLAYER, at_faction_id=WRATHFUL_RIVAL)
    )
    return world


def _health_rumors(world: WorldState, scenario: StrategyScenario):
    file_rumors(world, scenario, derive_rng(11, 1, "pressure"))
    return [r for r in world.pressure.rumors if r.topic is RumorTopic.HEALTH]


def test_no_view_exposes_ruler_age_or_health() -> None:
    assert not {"ruler_age", "ruler_health"} & set(OwnFactionView.model_fields)
    assert not {"ruler_age", "ruler_health", "age", "health"} & set(
        RivalView.model_fields
    )


def test_failing_rival_reported_as_very_high_when_hint_cannot_be_wrong() -> None:
    world = _world(rival_age=80)

    (rumor,) = _health_rumors(world, _scenario())

    assert rumor.band is PressureBand.VERY_HIGH
    assert rumor.line_key == "health.very_high"
    assert rumor.about_faction_id == WRATHFUL_RIVAL
    assert rumor.is_hint_wrong is False


def test_wrong_hint_is_one_band_toward_the_middle() -> None:
    world = _world(rival_age=80)

    (rumor,) = _health_rumors(world, _scenario(wrong=100))

    assert rumor.band is PressureBand.HIGH
    assert rumor.is_hint_wrong is True


def test_robust_rival_produces_no_health_rumor() -> None:
    world = _world(rival_age=30)

    assert _health_rumors(world, _scenario()) == []


def test_health_rumors_are_reproducible_for_the_same_seed() -> None:
    first = _health_rumors(_world(rival_age=80), _scenario(report=60, wrong=40))
    second = _health_rumors(_world(rival_age=80), _scenario(report=60, wrong=40))

    assert [r.model_dump() for r in first] == [r.model_dump() for r in second]


def test_legacy_worlds_file_no_health_rumors() -> None:
    world = _world(rival_age=80)
    world.succession_ruleset = 0

    assert _health_rumors(world, _scenario()) == []
