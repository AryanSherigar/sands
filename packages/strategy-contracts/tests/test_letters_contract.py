import pytest
from pydantic import ValidationError
from strategy_contracts.letters import (
    DEFAULT_LETTER_COOLDOWN_TURNS,
    LetterTopic,
    LetterTuning,
)
from strategy_contracts.scenario import Tuning


def test_letters_are_off_by_default_with_a_six_turn_cooldown() -> None:
    tuning = LetterTuning()
    assert tuning.is_enabled is False
    assert tuning.cooldown_turns == DEFAULT_LETTER_COOLDOWN_TURNS == 6


def test_a_scenario_tuning_carries_default_letter_tuning() -> None:
    assert Tuning().letters == LetterTuning()


def test_cooldown_must_be_at_least_one_turn() -> None:
    with pytest.raises(ValidationError):
        LetterTuning(cooldown_turns=0)


def test_topics_are_the_closed_set() -> None:
    assert {topic.value for topic in LetterTopic} == {
        "courtesy",
        "warning",
        "border_dispute",
    }
