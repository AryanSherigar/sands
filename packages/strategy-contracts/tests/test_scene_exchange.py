import pytest
from builders import make_negotiation_package
from pydantic import ValidationError
from strategy_contracts.limits import MAX_TEXT_CHARS
from strategy_contracts.scene import SceneStatus, SubmissionStatus
from strategy_contracts.scene_exchange import (
    InternalScenePackage,
    SceneAction,
    SceneDecision,
    SceneExchangeResult,
    SceneExchangeSubmission,
)


def _submission(**overrides) -> dict:
    body = {
        "sequence": 1,
        "player_text": "Let us make peace.",
        "leader_text": "Perhaps.",
        "decision": {"action": "continue_talk"},
    }
    return body | overrides


def test_submission_round_trips_with_a_proposal_duration() -> None:
    body = _submission(decision={"action": "propose_terms", "duration_turns": 8})
    parsed = SceneExchangeSubmission.model_validate(body)
    assert parsed.decision == SceneDecision(
        action=SceneAction.PROPOSE_TERMS, duration_turns=8
    )
    assert (
        SceneExchangeSubmission.model_validate_json(parsed.model_dump_json()) == parsed
    )


def test_scene_decision_tone_grade_defaults_to_neutral_and_accepts_valid_range() -> (
    None
):
    decision = SceneDecision(action=SceneAction.CONTINUE_TALK)
    assert decision.tone_grade == 2

    harsh = SceneDecision(action=SceneAction.REFUSE, tone_grade=5)
    assert harsh.tone_grade == 5

    with pytest.raises(ValidationError):
        SceneDecision(action=SceneAction.CONTINUE_TALK, tone_grade=6)

    with pytest.raises(ValidationError):
        SceneDecision(action=SceneAction.CONTINUE_TALK, tone_grade=-1)


@pytest.mark.parametrize(
    "overrides",
    [
        {"sequence": 0},
        {"player_text": ""},
        {"leader_text": "x" * (MAX_TEXT_CHARS + 1)},
        {"decision": {"action": "shrug"}},
        {"decision": {"action": "propose_terms", "duration_turns": 0}},
        {"extra": 1},
    ],
)
def test_invalid_submissions_are_rejected(overrides) -> None:
    with pytest.raises(ValidationError):
        SceneExchangeSubmission.model_validate(_submission(**overrides))


def test_result_and_package_wrapper_round_trip() -> None:
    result = SceneExchangeResult(
        status=SubmissionStatus.ACCEPTED,
        scene_status=SceneStatus.OPENED,
        exchanges_remaining=5,
    )
    assert SceneExchangeResult.model_validate_json(result.model_dump_json()) == result
    wrapper = InternalScenePackage.model_validate(
        {
            "package": make_negotiation_package(),
            "status": "opened",
            "exchanges_remaining": 6,
        }
    )
    assert wrapper.transcript == []
