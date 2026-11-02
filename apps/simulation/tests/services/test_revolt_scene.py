from app.engine.revolt.arming import arm_revolt_talk
from app.services.revolt_scene import build_revolt_talk_package
from app.services.scene_kinds import interpret_scene_decision
from strategy_contracts.scene import ChoiceOutcome, ChoiceSpec, SceneType
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from tests.engine.revolt.test_revolt_talk import (
    GOLD,
    HOME,
    _negotiate,
    _scenario,
    _world,
)


def _setup(treasury: int = GOLD):
    scenario = _scenario()
    world = _negotiate(_world(), scenario).world
    world.factions["house_a"].treasury = treasury
    arm_revolt_talk(world, scenario)
    package = build_revolt_talk_package(
        world,
        scenario,
        world.progress.pending_scene_id,
        world.progress.pending_revolt_talk,
    )
    return world, scenario, package


def _choose(option_id: str):
    world, scenario, package = _setup()
    decision = SceneDecision(action=SceneAction.CHOOSE_OPTION, option_id=option_id)
    return interpret_scene_decision(decision, package, world, scenario)


def test_the_package_offers_the_menu_and_defaults_to_words_alone() -> None:
    _, _, package = _setup()
    spec = package.allowed_outcomes[0]
    assert package.scene_type is SceneType.REVOLT_TALK
    assert isinstance(spec, ChoiceSpec)
    assert {option.id for option in spec.options} >= {"charter", "no_terms"}
    assert package.default_outcome == ChoiceOutcome(option_id="no_terms")
    assert HOME.title() in package.situation.summary


def test_unaffordable_relief_is_not_on_the_menu() -> None:
    _, _, package = _setup(treasury=10)
    spec = package.allowed_outcomes[0]
    assert "relief_large" not in {option.id for option in spec.options}


def test_a_menu_option_ends_the_scene() -> None:
    result = _choose("charter")
    assert result.ending == ChoiceOutcome(option_id="charter")


def test_an_invented_option_is_not_allowed() -> None:
    result = _choose("hand_over_the_crown")
    assert result.ending is None
    assert result.reason == "not_allowed"
