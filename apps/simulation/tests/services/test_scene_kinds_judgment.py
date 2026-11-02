import pytest
from app.services.judgment_scene import build_judgment_package
from app.services.scene_kinds import interpret_scene_decision
from strategy_contracts.judgment import JudgmentNuance, JudgmentOutcome, JudgmentVerdict
from strategy_contracts.scene_exchange import SceneAction, SceneDecision
from tests.engine.judgments.builders import (
    SCENE_ID,
    captive_pending,
    governor_pending,
    judgment_scenario,
    judgment_world,
)


def _interpret(decision: SceneDecision, pending=None):
    world, scenario = judgment_world(), judgment_scenario()
    package = build_judgment_package(
        world, scenario, SCENE_ID, pending or captive_pending()
    )
    return interpret_scene_decision(decision, package, world, scenario)


def _choose(option_id: str | None, nuance_id: str | None = None) -> SceneDecision:
    return SceneDecision(
        action=SceneAction.CHOOSE_OPTION, option_id=option_id, nuance_id=nuance_id
    )


def test_continuing_to_talk_is_plain_talk() -> None:
    result = _interpret(SceneDecision(action=SceneAction.CONTINUE_TALK))
    assert (result.ending, result.reason) == (None, None)


def test_a_known_verdict_with_a_valid_nuance_ends_the_scene() -> None:
    result = _interpret(_choose("execute", "publicly"))
    assert result.ending == JudgmentOutcome(
        verdict=JudgmentVerdict.EXECUTE, nuance=JudgmentNuance.PUBLICLY
    )


def test_a_verdict_without_a_nuance_ends_the_scene() -> None:
    result = _interpret(_choose("release"))
    assert result.ending == JudgmentOutcome(verdict=JudgmentVerdict.RELEASE)


@pytest.mark.parametrize(
    ("option_id", "nuance_id"),
    [("banish", None), (None, None), ("execute", "for_life"), ("release", "nonsense")],
)
def test_an_unknown_verdict_or_mismatched_nuance_is_not_allowed(
    option_id: str | None, nuance_id: str | None
) -> None:
    result = _interpret(_choose(option_id, nuance_id))
    assert (result.ending, result.reason) == (None, "not_allowed")


def test_proposing_terms_is_not_allowed_in_a_judgment() -> None:
    decision = SceneDecision(action=SceneAction.PROPOSE_TERMS, duration_turns=4)
    assert _interpret(decision).reason == "not_allowed"


def test_a_governor_judgment_accepts_exile_stripped_of_title() -> None:
    result = _interpret(_choose("exile", "stripped_of_title"), governor_pending())
    assert result.ending == JudgmentOutcome(
        verdict=JudgmentVerdict.EXILE, nuance=JudgmentNuance.STRIPPED_OF_TITLE
    )
