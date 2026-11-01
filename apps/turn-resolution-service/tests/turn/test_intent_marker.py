import pytest
from app.turn import intent_marker


def test_text_without_a_marker_is_untouched() -> None:
    text = "She nods.\n\n"

    assert intent_marker.extract_intent_markers(text) == (text, [])


def test_a_marker_paragraph_is_removed_and_parsed() -> None:
    cleaned, pairs = intent_marker.extract_intent_markers(
        "[INTENT: recruit_target=ritsu]"
    )

    assert cleaned == ""
    assert pairs == [("recruit_target", "ritsu")]


def test_a_marker_on_the_last_line_of_a_paragraph_keeps_the_prose() -> None:
    text = "[NARRATOR]\nShe nods slowly.\n[INTENT: recruit_target=ritsu]"

    cleaned, pairs = intent_marker.extract_intent_markers(text)

    assert cleaned == "[NARRATOR]\nShe nods slowly."
    assert pairs == [("recruit_target", "ritsu")]


def test_the_paragraph_separator_survives_when_prose_remains() -> None:
    cleaned, _ = intent_marker.extract_intent_markers("Text.\n[INTENT: a=b]\n\n")

    assert cleaned == "Text.\n\n"


def test_several_pairs_and_loose_spacing_and_case_are_accepted() -> None:
    _, pairs = intent_marker.extract_intent_markers(
        "[intent : Train_Who = Rosell ,train_stat=ingenuity]"
    )

    assert pairs == [("train_who", "rosell"), ("train_stat", "ingenuity")]


@pytest.mark.parametrize("body", ["no equals", "a=", "=b", "a=b c", "a=b;c=d"])
def test_malformed_pairs_are_dropped(body: str) -> None:
    _, pairs = intent_marker.extract_intent_markers(f"[INTENT: {body}]")

    assert pairs == []


def test_a_marker_inside_a_sentence_is_left_alone() -> None:
    text = 'He says "write [INTENT: a=b] on it".'

    assert intent_marker.extract_intent_markers(text) == (text, [])


def test_function_calls_target_the_group_and_the_last_value_wins() -> None:
    calls = intent_marker.pairs_to_function_calls(
        [("recruit_target", "ritsu"), ("recruit_target", "charlotte")], "intent"
    )

    assert len(calls) == 1
    assert calls[0].name == "set_field"
    assert calls[0].args == {"path": "intent.recruit_target", "value": "charlotte"}
