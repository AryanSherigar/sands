"""Unit tests for the player action size cap."""

from app.turn.action_text_limit import truncate_action_text

MAX_CHARS = 10


def test_text_under_the_cap_is_unchanged() -> None:
    result = truncate_action_text("look around", 20)

    assert result.text == "look around"
    assert result.is_truncated is False


def test_text_exactly_at_the_cap_is_not_truncated() -> None:
    result = truncate_action_text("a" * MAX_CHARS, MAX_CHARS)

    assert result.text == "a" * MAX_CHARS
    assert result.is_truncated is False


def test_text_over_the_cap_keeps_the_start() -> None:
    result = truncate_action_text("abcdefghijklmno", MAX_CHARS)

    assert result.text == "abcdefghij"
    assert result.original_length == 15
    assert result.is_truncated is True


def test_surrounding_whitespace_is_stripped_before_counting() -> None:
    result = truncate_action_text("   " + "a" * MAX_CHARS + "   ", MAX_CHARS)

    assert result.text == "a" * MAX_CHARS
    assert result.original_length == MAX_CHARS
    assert result.is_truncated is False


def test_characters_are_counted_as_code_points() -> None:
    result = truncate_action_text("😀" * 12, MAX_CHARS)

    assert result.text == "😀" * MAX_CHARS
    assert result.original_length == 12


def test_whitespace_only_text_becomes_empty() -> None:
    result = truncate_action_text("   \n  ", MAX_CHARS)

    assert result.text == ""
    assert result.is_truncated is False
