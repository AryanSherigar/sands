"""The hard ceiling on TurnRequestInput.action_text."""

import uuid

import pytest
from app.config import settings
from app.models.turn import TurnRequestInput
from pydantic import ValidationError


def _input(action_text: str) -> TurnRequestInput:
    return TurnRequestInput(
        playthrough_id=uuid.uuid4(),
        participant_id=uuid.uuid4(),
        client_action_id=uuid.uuid4(),
        action_text=action_text,
    )


def test_action_text_at_the_hard_ceiling_is_accepted() -> None:
    turn_input = _input("a" * settings.turn_action_hard_max_chars)

    assert len(turn_input.action_text) == settings.turn_action_hard_max_chars


def test_action_text_over_the_hard_ceiling_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _input("a" * (settings.turn_action_hard_max_chars + 1))
