from app.engine.pressure.bands import to_band
from app.engine.pressure.rumors import file_rumors
from app.engine.rng import derive_rng
from app.models.world_coalition import CoalitionState
from app.models.world_diplomacy import EnvoyState
from strategy_contracts.pressure import PressureBand, RumorTopic

from tests.engine.coalitions.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)
from tests.engine.diplomacy.builders import set_traits

SURE_REPORT = 100
NEVER_WRONG = 0


def _scenario(wrong: int = NEVER_WRONG):
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.pressure.rumor_report_percent = SURE_REPORT
    scenario.tuning.pressure.wrong_hint_base_percent = wrong
    return scenario


def _world_with_envoy_at(faction_id: str, members: list[str]):
    world = make_world()
    if members:
        world.coalition.coalitions.append(
            CoalitionState(
                id="coalition_1",
                target_id=faction_id,
                member_ids=members,
                formed_turn=world.clock.turn,
                expires_turn=world.clock.turn + 10,
            )
        )
    world.envoys.append(
        EnvoyState(id="envoy_1", from_faction_id=PLAYER, at_faction_id=faction_id)
    )
    return world


def _coalition_rumors(world):
    return [r for r in world.pressure.rumors if r.topic is RumorTopic.COALITION]


def _rng():
    return derive_rng(11, 1, "pressure")


def test_envoy_reports_a_coalition_gathered_against_the_host() -> None:
    world = _world_with_envoy_at(WRATHFUL_RIVAL, [CAUTIOUS_RIVAL])
    scenario = _scenario()

    file_rumors(world, scenario, _rng())

    [rumor] = _coalition_rumors(world)
    others = len([f for f in world.factions if f != WRATHFUL_RIVAL])
    expected = to_band(1 * 100 // others, scenario.tuning.pressure)
    assert (rumor.about_faction_id, rumor.band) == (WRATHFUL_RIVAL, expected)
    assert rumor.line_key == f"coalition.{expected.value}"
    assert rumor.is_hint_wrong is False


def test_no_coalition_means_no_coalition_rumor() -> None:
    world = _world_with_envoy_at(WRATHFUL_RIVAL, [])

    file_rumors(world, _scenario(), _rng())

    assert _coalition_rumors(world) == []


def test_a_hint_can_be_wrong_by_one_band_toward_the_middle() -> None:
    world = _world_with_envoy_at(WRATHFUL_RIVAL, [CAUTIOUS_RIVAL, PLAYER])
    set_traits(world, PLAYER, ["pragmatic"])

    file_rumors(world, _scenario(wrong=100), _rng())

    [rumor] = _coalition_rumors(world)
    assert rumor.is_hint_wrong is True
    assert rumor.band is not PressureBand.VERY_HIGH


def test_a_world_without_coalitions_files_no_coalition_rumor() -> None:
    world = _world_with_envoy_at(WRATHFUL_RIVAL, [CAUTIOUS_RIVAL])
    world.coalition_ruleset = 0

    file_rumors(world, _scenario(), _rng())

    assert _coalition_rumors(world) == []
