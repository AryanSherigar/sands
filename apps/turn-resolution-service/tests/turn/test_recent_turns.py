"""Unit tests for app/turn/recent_turns.py."""

import uuid
from types import SimpleNamespace

from app.models.turn import RecentTurn
from app.turn.recent_turns import (
    actor_label,
    fit_recent_text,
    last_say_utterance,
    render_recent_turns,
    to_recent_turn,
)


def _turn(
    number: int,
    action: str = "act",
    narration: str = "narrate",
    participant_id: uuid.UUID | None = None,
    mode: str = "do",
) -> RecentTurn:
    return RecentTurn(
        turn_number=number,
        participant_id=participant_id,
        action_mode=mode,
        action_text=action,
        narration_text=narration,
    )


def test_single_participant_keeps_the_plain_player_label() -> None:
    pid = uuid.uuid4()

    assert actor_label(pid, {pid: "Alice"}) == "Player"
    assert actor_label(pid, {}) == "Player"


def test_multiplayer_uses_each_turns_display_name() -> None:
    alice, bob = uuid.uuid4(), uuid.uuid4()
    names = {alice: "Alice", bob: "Bob"}

    text = render_recent_turns(
        [
            _turn(1, "I open the door.", "It creaks.", alice),
            _turn(2, "I peer in.", "Darkness.", bob),
        ],
        names,
    )

    assert text == (
        "Alice: I open the door.\nNarrator: It creaks.\n"
        "Bob: I peer in.\nNarrator: Darkness."
    )


def test_unknown_participant_falls_back_to_player() -> None:
    names = {uuid.uuid4(): "Alice", uuid.uuid4(): "Bob"}

    assert actor_label(uuid.uuid4(), names) == "Player"
    assert actor_label(None, names) == "Player"


def test_fit_recent_text_keeps_newest_turns_in_order() -> None:
    turns = [_turn(i, f"a{i}", f"n{i}") for i in range(1, 6)]
    one_turn = len("Player: a1\nNarrator: n1")

    text = fit_recent_text(turns, {}, max_chars=2 * (one_turn + 1))

    assert text == "Player: a4\nNarrator: n4\nPlayer: a5\nNarrator: n5"


def test_fit_recent_text_cuts_a_single_oversized_turn_to_its_tail() -> None:
    turns = [_turn(1, "a" * 50, "END-OF-NARRATION")]

    text = fit_recent_text(turns, {}, max_chars=20)

    assert len(text) == 20
    assert text.endswith("END-OF-NARRATION")


def test_fit_recent_text_of_nothing_is_empty() -> None:
    assert fit_recent_text([], {}, max_chars=100) == ""


def test_last_say_utterance_is_the_newest_say_action() -> None:
    turns = [
        _turn(1, "Hello there", mode="say"),
        _turn(2, "I draw my sword", mode="do"),
        _turn(3, "  Bring the key  ", mode="say"),
        _turn(4, "I wait", mode="do"),
    ]

    assert last_say_utterance(turns, 100) == "Bring the key"
    assert last_say_utterance(turns, 5) == "Bring"
    assert last_say_utterance([_turn(1, mode="do")], 100) == ""


def test_to_recent_turn_maps_a_turn_log_and_tolerates_null_narration() -> None:
    row = SimpleNamespace(
        turn_number=4,
        participant_id=None,
        action_mode="say",
        action_text="Hi",
        narration_text=None,
    )

    turn = to_recent_turn(row)

    assert (turn.turn_number, turn.narration_text, turn.action_mode) == (4, "", "say")
