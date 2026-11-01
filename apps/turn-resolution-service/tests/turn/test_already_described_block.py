"""The "Already Described" block: wording the narrator should not reuse this turn."""

import uuid

from app.models.turn import RecentTurn
from app.turn import context_assembly as ca

PARTICIPANT = uuid.UUID("00000000-0000-0000-0000-000000000009")


def _turn(number: int, narration: str) -> RecentTurn:
    return RecentTurn(
        turn_number=number,
        participant_id=PARTICIPANT,
        action_mode="do",
        action_text="I wait.",
        narration_text=narration,
    )


def test_the_block_lists_phrases_reused_in_the_recent_turns() -> None:
    turns = [
        _turn(1, "The ceiling speaker hums. You wait."),
        _turn(2, "Rain falls. The ceiling speaker keeps humming."),
        _turn(3, "A phone rings. The ceiling speaker is still on."),
    ]

    block = ca.build_already_described_block(turns)

    assert block.startswith("## Already Described")
    assert "ceiling speaker" in block
    assert "unless something about them has changed" in block


def test_the_block_asks_for_a_new_first_word_after_two_matching_openers() -> None:
    turns = [_turn(1, "You walk."), _turn(2, "You stop.")]

    block = ca.build_already_described_block(turns)

    assert 'different word than "You"' in block


def test_no_repetition_means_no_block() -> None:
    turns = [_turn(1, "Rain taps the glass."), _turn(2, "A drawer slides shut.")]

    assert ca.build_already_described_block(turns) == ""
    assert ca.build_already_described_block([]) == ""


def test_only_the_recent_window_is_inspected(monkeypatch) -> None:
    monkeypatch.setattr(ca.settings, "repetition_window_turns", 2)
    turns = [
        _turn(1, "The ceiling speaker hums."),
        _turn(2, "The ceiling speaker hums."),
        _turn(3, "A phone rings somewhere."),
        _turn(4, "Rain taps the glass."),
    ]

    assert ca.build_already_described_block(turns) == ""


def test_the_list_is_capped(monkeypatch) -> None:
    monkeypatch.setattr(ca.settings, "repetition_phrase_limit", 1)
    text = "Alpha beta here. Gamma delta there."
    block = ca.build_already_described_block([_turn(1, text), _turn(2, text)])

    assert block.count(";") == 0
