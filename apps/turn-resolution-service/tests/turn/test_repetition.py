"""Unit tests for app/turn/repetition.py."""

from app.turn.repetition import (
    novelty_score,
    repeated_opener,
    repeated_phrases,
    top_phrases,
)

SPEAKER = "The ceiling speaker plays soft music."
CARPET = "Grey carpet runs down the thirty-metre corridor."


def test_a_phrase_in_two_of_the_turns_is_reported() -> None:
    turns = [
        f"{SPEAKER} A door clicks.",
        "Rain taps the window. Nothing else moves.",
        f"You wait. {SPEAKER}",
    ]
    assert "ceiling speaker" in repeated_phrases(turns)


def test_a_phrase_used_in_only_one_turn_is_not_reported() -> None:
    turns = [SPEAKER, "A door clicks.", "Rain taps the window."]
    assert repeated_phrases(turns) == []


def test_overlapping_variants_of_one_phrase_are_collapsed() -> None:
    turns = [CARPET, CARPET, "Something else."]
    found = repeated_phrases(turns)
    assert any("carpet" in phrase for phrase in found)
    assert any("thirty-metre" in phrase for phrase in found)
    assert not any(
        phrase != other and phrase in other for phrase in found for other in found
    )
    assert len([phrase for phrase in found if "carpet" in phrase]) == 1


def test_phrases_made_only_of_function_words_are_ignored() -> None:
    turns = ["It is in the end.", "It is in the end.", "Other words here."]
    assert repeated_phrases(turns) == []


def test_the_list_is_capped_and_ordered_by_how_many_turns_use_it() -> None:
    turns = [
        "alpha beta gamma. delta epsilon zeta. eta theta iota.",
        "alpha beta gamma. delta epsilon zeta. eta theta iota.",
        "alpha beta gamma. delta epsilon zeta.",
    ]
    found = repeated_phrases(turns, limit=2)
    assert len(found) == 2
    assert found == ["alpha beta", "delta epsilon"]


def test_repeated_opener_needs_the_last_two_turns_to_match() -> None:
    assert repeated_opener(["You walk.", "You wait."]) == "You"
    assert repeated_opener(["You walk.", "The door opens."]) is None
    assert repeated_opener(["You walk."]) is None


def test_identical_turns_have_no_novelty_and_distinct_turns_have_a_lot() -> None:
    same = [SPEAKER + " " + CARPET] * 4
    distinct = [
        "One quiet room holds a lamp.",
        "Rain taps against a high window.",
        "Someone coughs on another floor.",
        "A drawer slides shut by itself.",
    ]
    assert novelty_score(same) < 0.1
    assert novelty_score(distinct) > 0.9


def test_top_phrases_counts_turns_across_the_whole_run() -> None:
    turns = [SPEAKER, SPEAKER, "Other.", SPEAKER]
    counts = dict(top_phrases(turns, limit=5))
    assert counts["ceiling speaker"] == 3


def test_the_report_summarises_a_run() -> None:
    from app.turn.repetition import summarize

    turns = [
        f"You hear the {SPEAKER}",
        f"You see {SPEAKER}",
        f"A door clicks. {SPEAKER}",
    ]
    report = summarize(turns)
    assert report.turns == 3
    assert report.most_common_opener == "You"
    assert report.opener_share == 2 / 3
    assert report.average_words > 0
    assert ("ceiling speaker", 3) in report.top_phrases


def test_closing_share_counts_turns_that_end_with_the_same_words() -> None:
    from app.turn.repetition import closing_repeat_share

    formula = "The phone stays silent while the folder waits."
    turns = [
        f"One. {formula}",
        "Two. The phone stays silent while a Log waits.",
        "Three. The phone stays silent while it waits.",
        "Four. Someone laughs once.",
    ]
    assert closing_repeat_share(turns) == 3 / 4
    assert closing_repeat_share(turns[:2]) == 0.0
    assert closing_repeat_share([]) == 0.0
