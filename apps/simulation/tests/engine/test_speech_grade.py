import pytest
from app.engine.speech_grade import (
    apply_speech_outcome,
    deterministic_fallback_outcome,
    graded_outcome,
    morale_delta_from_scores,
)
from pydantic import ValidationError
from strategy_contracts.scene import BattleSpeechOutcome, SpeechRubric

from tests.engine.battles.builders import battle_fixture

TOP = {rubric: 5 for rubric in SpeechRubric}
BOTTOM = {rubric: 0 for rubric in SpeechRubric}


def test_perfect_and_worst_speeches_hit_the_bounds() -> None:
    assert morale_delta_from_scores(TOP) == 15
    assert morale_delta_from_scores(BOTTOM) == -15


def test_missing_scores_count_as_zero() -> None:
    assert morale_delta_from_scores({}) == -15


def test_fitting_the_rulers_character_moves_morale_more_than_other_rubrics() -> None:
    character = BOTTOM | {SpeechRubric.FITS_RULER_CHARACTER: 5}
    fears = BOTTOM | {SpeechRubric.ADDRESSES_FEARS: 5}
    assert morale_delta_from_scores(character) > morale_delta_from_scores(fears)


def test_a_better_score_never_lowers_morale() -> None:
    previous = -16
    for score in range(6):
        delta = morale_delta_from_scores(BOTTOM | {SpeechRubric.PROMISES_MADE: score})
        assert delta >= previous
        previous = delta


def test_fallback_is_a_neutral_outcome() -> None:
    outcome = deterministic_fallback_outcome()
    assert (outcome.morale_delta_percent, outcome.rubric_scores) == (0, {})


def test_contract_rejects_out_of_range_values() -> None:
    with pytest.raises(ValidationError):
        BattleSpeechOutcome(morale_delta_percent=16)
    with pytest.raises(ValidationError):
        BattleSpeechOutcome(
            morale_delta_percent=0, rubric_scores={SpeechRubric.PROMISES_MADE: 6}
        )


def test_applying_an_outcome_changes_morale_and_records_the_change() -> None:
    world, _ = battle_fixture()
    world.armies["army_a"].morale = 95
    changes = apply_speech_outcome(world, "army_a", graded_outcome(TOP))
    assert world.armies["army_a"].morale == 100
    assert (changes[0].path, changes[0].before, changes[0].after) == (
        "armies.army_a.morale",
        95,
        100,
    )
