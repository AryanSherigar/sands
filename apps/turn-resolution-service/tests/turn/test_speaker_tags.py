"""Unit tests for speaker-tag stripping/parsing and paragraph buffering."""

from app.turn.speaker_tags import (
    NARRATOR_SPEAKER,
    SpeakerSpan,
    buffer_narration_paragraphs,
    flush_narration_paragraph_buffer,
    has_escalation_marker,
    parse_speaker_spans,
    strip_speaker_tags,
)


def test_strip_speaker_tags_removes_narrator_and_npc_tags() -> None:
    text = (
        "[NARRATOR]\nYou creep through the tavern door.\n\n"
        '[NPC: Grimjaw]\n"Get out of my tavern," he growls.'
    )

    cleaned = strip_speaker_tags(text)

    assert cleaned == (
        'You creep through the tavern door.\n\n"Get out of my tavern," he growls.'
    )


def test_strip_speaker_tags_leaves_untagged_text_unchanged() -> None:
    assert strip_speaker_tags("Just plain prose.") == "Just plain prose."


def test_parse_speaker_spans_attributes_narrator_and_npc() -> None:
    text = (
        "[NARRATOR]\nYou creep through the tavern door.\n\n"
        '[NPC: Grimjaw]\n"Get out of my tavern," he growls.'
    )

    spans = parse_speaker_spans(text)

    assert spans == [
        SpeakerSpan(NARRATOR_SPEAKER, "You creep through the tavern door."),
        SpeakerSpan("Grimjaw", '"Get out of my tavern," he growls.'),
    ]


def test_parse_speaker_spans_untagged_paragraph_falls_back_to_narrator() -> None:
    spans = parse_speaker_spans("No tag on this paragraph at all.")

    assert spans == [SpeakerSpan(NARRATOR_SPEAKER, "No tag on this paragraph at all.")]


def test_parse_speaker_spans_malformed_tag_falls_back_to_narrator() -> None:
    spans = parse_speaker_spans("[NPC missing closing bracket\nSome dialogue.")

    assert spans == [
        SpeakerSpan(NARRATOR_SPEAKER, "[NPC missing closing bracket\nSome dialogue.")
    ]


def test_parse_speaker_spans_skips_blank_paragraphs() -> None:
    spans = parse_speaker_spans("[NARRATOR]\nFirst.\n\n\n\n[NARRATOR]\nSecond.")

    assert spans == [
        SpeakerSpan(NARRATOR_SPEAKER, "First."),
        SpeakerSpan(NARRATOR_SPEAKER, "Second."),
    ]


def test_buffer_narration_paragraphs_holds_text_without_a_boundary() -> None:
    buffer, events = buffer_narration_paragraphs("", "[NARRATOR]\nNo boundary yet")

    assert buffer == "[NARRATOR]\nNo boundary yet"
    assert events == []


def test_buffer_narration_paragraphs_releases_on_double_newline() -> None:
    buffer, events = buffer_narration_paragraphs(
        "", "[NARRATOR]\nComplete paragraph.\n\n"
    )

    assert buffer == ""
    assert events == [
        ("narration_raw", "[NARRATOR]\nComplete paragraph.\n\n"),
        ("narration", "Complete paragraph.\n\n"),
    ]


def test_buffer_narration_paragraphs_releases_multiple_paragraphs_in_one_call() -> None:
    buffer, events = buffer_narration_paragraphs(
        "", "[NARRATOR]\nFirst.\n\n[NPC: Grimjaw]\nSecond.\n\n"
    )

    assert buffer == ""
    assert events == [
        ("narration_raw", "[NARRATOR]\nFirst.\n\n"),
        ("narration", "First.\n\n"),
        ("narration_raw", "[NPC: Grimjaw]\nSecond.\n\n"),
        ("narration", "Second.\n\n"),
    ]


def test_flush_narration_paragraph_buffer_emits_trailing_paragraph() -> None:
    events = flush_narration_paragraph_buffer("[NARRATOR]\nTrailing, no blank line.")

    assert events == [
        ("narration_raw", "[NARRATOR]\nTrailing, no blank line."),
        ("narration", "Trailing, no blank line."),
    ]


def test_flush_narration_paragraph_buffer_empty_buffer_emits_nothing() -> None:
    assert flush_narration_paragraph_buffer("") == []
    assert flush_narration_paragraph_buffer("   \n  ") == []


def test_strip_speaker_tags_removes_inline_tag_mid_paragraph() -> None:
    text = "The latch slides to bolt. [NARRATOR] From somewhere a door opens."

    assert strip_speaker_tags(text) == (
        "The latch slides to bolt. From somewhere a door opens."
    )


def test_strip_speaker_tags_removes_tag_at_paragraph_end() -> None:
    assert strip_speaker_tags("Silence settles. [NARRATOR]") == "Silence settles."


def test_strip_speaker_tags_is_case_insensitive_and_handles_many_tags() -> None:
    text = "[narrator]\nOne. [Npc: Voss] Two. [NARRATOR] Three."

    assert strip_speaker_tags(text) == "One. Two. Three."


def test_strip_speaker_tags_removes_escalation_on_its_own_line() -> None:
    text = "[NARRATOR]\nYou shout into the dark.\n[ESCALATION]\nAcknowledged."

    assert strip_speaker_tags(text) == "You shout into the dark.\nAcknowledged."


def test_strip_speaker_tags_joins_tag_inside_a_word_with_one_space() -> None:
    assert strip_speaker_tags("bo[NARRATOR]lt") == "bo lt"


def test_strip_speaker_tags_escalation_only_paragraph_becomes_empty() -> None:
    assert strip_speaker_tags("[ESCALATION]").strip() == ""


def test_parse_speaker_spans_splits_a_mid_paragraph_npc_tag() -> None:
    text = '[NARRATOR]\nHe turns. [NPC: Voss] "Evening." [NARRATOR] He leaves.'

    assert parse_speaker_spans(text) == [
        SpeakerSpan(NARRATOR_SPEAKER, "He turns."),
        SpeakerSpan("Voss", '"Evening."'),
        SpeakerSpan(NARRATOR_SPEAKER, "He leaves."),
    ]


def test_parse_speaker_spans_drops_escalation_marker_and_keeps_text() -> None:
    spans = parse_speaker_spans("[NARRATOR]\nYou shout.\n[ESCALATION]\nIt echoes.")

    assert spans == [SpeakerSpan(NARRATOR_SPEAKER, "You shout. It echoes.")]


def test_has_escalation_marker_detects_the_tag_anywhere() -> None:
    assert has_escalation_marker("[NARRATOR]\nText.\n[escalation]\nMore.")
    assert not has_escalation_marker("[NARRATOR]\nNo marker here.")


def test_buffer_releases_clean_narration_for_inline_tags() -> None:
    _, events = buffer_narration_paragraphs("", "Bolt. [NARRATOR] Door.\n\n")

    assert events == [
        ("narration_raw", "Bolt. [NARRATOR] Door.\n\n"),
        ("narration", "Bolt. Door.\n\n"),
    ]
