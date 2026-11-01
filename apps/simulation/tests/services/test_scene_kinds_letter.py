from app.engine.letters.arming import arm_letter
from app.engine.letters.constants import LETTER_COOLER, LETTER_WARMER
from app.services.letter_scene import build_letter_package
from app.services.scene_kinds import interpret_scene_decision
from strategy_contracts.scene import ChoiceOutcome
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from tests.engine.letters.builders import letter_scenario, letter_world, set_opinion


def _setup():
    world = letter_world()
    set_opinion(world, 1)
    scenario = letter_scenario()
    arm_letter(world, scenario)
    package = build_letter_package(
        world,
        scenario,
        world.progress.pending_scene_id,
        world.progress.pending_letter,
    )
    return world, scenario, package


def _interpret(decision: SceneDecision):
    world, scenario, package = _setup()
    return interpret_scene_decision(decision, package, world, scenario)


def test_a_known_option_ends_the_scene_with_that_choice() -> None:
    result = _interpret(
        SceneDecision(action=SceneAction.CHOOSE_OPTION, option_id=LETTER_WARMER)
    )
    assert result.ending == ChoiceOutcome(option_id=LETTER_WARMER)
    assert result.reason is None


def test_another_known_option_is_honoured() -> None:
    result = _interpret(
        SceneDecision(action=SceneAction.CHOOSE_OPTION, option_id=LETTER_COOLER)
    )
    assert result.ending == ChoiceOutcome(option_id=LETTER_COOLER)


def test_an_unknown_option_ends_nothing_and_says_why() -> None:
    result = _interpret(
        SceneDecision(action=SceneAction.CHOOSE_OPTION, option_id="gift_gold")
    )
    assert result.ending is None
    assert result.reason == "not_allowed"


def test_a_missing_option_id_ends_nothing() -> None:
    result = _interpret(SceneDecision(action=SceneAction.CHOOSE_OPTION))
    assert result.ending is None
    assert result.reason == "not_allowed"


def test_propose_terms_is_not_allowed_in_a_letter() -> None:
    result = _interpret(
        SceneDecision(action=SceneAction.PROPOSE_TERMS, duration_turns=8)
    )
    assert result.ending is None
    assert result.proposal is None
    assert result.reason == "not_allowed"


def test_continue_talk_leaves_the_letter_open() -> None:
    result = _interpret(SceneDecision(action=SceneAction.CONTINUE_TALK))
    assert result.ending is None
