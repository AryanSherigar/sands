from app.engine.pressure.rumors import file_rumors
from app.engine.rng import derive_rng
from app.models.world_diplomacy import EnvoyState
from app.models.world_state import WorldState
from strategy_contracts.pressure import PressureBand, RumorTopic
from strategy_contracts.scene import OutrageLevel

from tests.engine.diplomacy.builders import set_traits
from tests.engine.outrage.builders import (
    PLAYER,
    WRATHFUL_RIVAL,
    enrage,
    make_world,
)
from tests.engine.outrage.builders import (
    SCENARIO as BASE_SCENARIO,
)

CALM_HINT = 0


def _scenario():
    scenario = BASE_SCENARIO.model_copy(deep=True)
    scenario.tuning.pressure.rumor_report_percent = 100
    scenario.tuning.pressure.wrong_hint_base_percent = CALM_HINT
    return scenario


def _world(level: OutrageLevel = OutrageLevel.ENRAGED) -> WorldState:
    world = make_world()
    set_traits(world, PLAYER, ["pragmatic"])
    world.envoys.append(
        EnvoyState(id="envoy_1", from_faction_id=PLAYER, at_faction_id=WRATHFUL_RIVAL)
    )
    enrage(world, level=level)
    return world


def _rage_rumors(world: WorldState):
    return [r for r in world.pressure.rumors if r.topic is RumorTopic.RAGE]


def _file(world: WorldState) -> None:
    file_rumors(world, _scenario(), derive_rng(11, 1, "pressure"))


def test_an_envoy_hears_of_a_rulers_rage_even_at_peace() -> None:
    world = _world()

    _file(world)

    (rumor,) = _rage_rumors(world)
    assert rumor.band is PressureBand.VERY_HIGH
    assert rumor.line_key == "rage.very_high"
    assert rumor.about_faction_id == WRATHFUL_RIVAL


def test_a_merely_annoyed_ruler_is_not_worth_a_report() -> None:
    world = _world(OutrageLevel.ANNOYED)

    _file(world)

    assert _rage_rumors(world) == []


def test_legacy_worlds_hear_no_rage_rumors() -> None:
    world = _world()
    world.outrage_ruleset = 0

    _file(world)

    assert _rage_rumors(world) == []
