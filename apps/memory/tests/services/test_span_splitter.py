"""Tests for app.services.span_splitter, a pure module with no I/O."""

from app.models.evidence import SpanDraft
from app.services.span_splitter import estimate_tokens, split_spans

DEFAULT_CHARS_PER_TOKEN = 4
DEFAULT_MAX_TOKENS = 50


def _assert_offsets_match_content(content: str, spans: list[SpanDraft]) -> None:
    for span in spans:
        assert content[span.start_offset : span.end_offset] == span.text


def _split(
    content: str,
    *,
    label_prefix: str = "S1",
    max_tokens: int = DEFAULT_MAX_TOKENS,
    chars_per_token: int = DEFAULT_CHARS_PER_TOKEN,
) -> list[SpanDraft]:
    return split_spans(
        content,
        label_prefix=label_prefix,
        max_tokens=max_tokens,
        chars_per_token=chars_per_token,
    )


def test_empty_content_returns_no_spans() -> None:
    assert _split("") == []


def test_whitespace_only_content_returns_no_spans() -> None:
    assert _split("   \n\n\t  \n") == []


def test_single_paragraph_produces_one_span() -> None:
    content = "A lone paragraph with no blank lines inside it."
    spans = _split(content)
    assert len(spans) == 1
    assert spans[0].text == content
    _assert_offsets_match_content(content, spans)


def test_blank_line_splits_paragraphs() -> None:
    content = "First paragraph.\n\nSecond paragraph."
    spans = _split(content)
    assert [span.text for span in spans] == ["First paragraph.", "Second paragraph."]
    _assert_offsets_match_content(content, spans)


def test_multiple_blank_lines_between_paragraphs() -> None:
    content = "First.\n\n\n\nSecond."
    spans = _split(content)
    assert [span.text for span in spans] == ["First.", "Second."]
    _assert_offsets_match_content(content, spans)


def test_whitespace_only_line_counts_as_blank() -> None:
    content = "First.\n   \nSecond."
    spans = _split(content)
    assert [span.text for span in spans] == ["First.", "Second."]
    _assert_offsets_match_content(content, spans)


def test_crlf_line_endings_split_paragraphs() -> None:
    content = "First.\r\n\r\nSecond."
    spans = _split(content)
    assert [span.text for span in spans] == ["First.", "Second."]
    _assert_offsets_match_content(content, spans)


def test_leading_and_trailing_whitespace_excluded_from_span_text() -> None:
    content = "  \n  Padded paragraph.  \n\n"
    spans = _split(content)
    assert len(spans) == 1
    assert spans[0].text == "Padded paragraph."
    _assert_offsets_match_content(content, spans)


def test_multiline_paragraph_stays_one_span_when_within_budget() -> None:
    content = "Line one of a paragraph\nthat continues on line two."
    spans = _split(content)
    assert len(spans) == 1
    assert spans[0].text == content
    _assert_offsets_match_content(content, spans)


def test_ordinals_increase_across_whole_content() -> None:
    content = "One.\n\nTwo.\n\nThree."
    spans = _split(content)
    assert [span.ordinal for span in spans] == [1, 2, 3]


def test_labels_use_prefix_and_ordinal() -> None:
    content = "One.\n\nTwo."
    spans = _split(content, label_prefix="S41")
    assert [span.label for span in spans] == ["S41.1", "S41.2"]


def test_long_paragraph_splits_on_sentence_boundaries() -> None:
    sentence = "Word " * 8 + "ends here. "
    content = (sentence * 5).strip()
    spans = _split(content, max_tokens=10, chars_per_token=4)
    assert len(spans) > 1
    for span in spans:
        assert span.token_count <= 10
    _assert_offsets_match_content(content, spans)
    recombined_non_whitespace = "".join("".join(span.text.split()) for span in spans)
    original_non_whitespace = "".join(content.split())
    assert recombined_non_whitespace == original_non_whitespace


def test_sentence_boundary_handles_closing_quote() -> None:
    content = 'He said "stop." Then he left the room and walked away slowly into dusk.'
    spans = _split(content, max_tokens=5, chars_per_token=4)
    assert len(spans) > 1
    for span in spans:
        assert span.token_count <= 5
    _assert_offsets_match_content(content, spans)


def test_single_long_sentence_splits_on_whitespace() -> None:
    content = "word " * 40
    content = content.strip()
    spans = _split(content, max_tokens=5, chars_per_token=4)
    assert len(spans) > 1
    for span in spans:
        assert span.token_count <= 5
    _assert_offsets_match_content(content, spans)
    recombined = "".join(span.text.replace(" ", "") for span in spans)
    assert recombined == content.replace(" ", "")


def test_giant_single_word_hard_split_by_characters() -> None:
    content = "x" * 100
    spans = _split(content, max_tokens=5, chars_per_token=4)
    assert len(spans) > 1
    for span in spans:
        assert span.token_count <= 5
    _assert_offsets_match_content(content, spans)
    assert "".join(span.text for span in spans) == content


def test_never_truncates_non_whitespace_content() -> None:
    content = (
        "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu.\n\n"
        "Nu xi omicron pi rho sigma tau upsilon phi chi psi omega, the end!"
    )
    spans = _split(content, max_tokens=6, chars_per_token=4)
    _assert_offsets_match_content(content, spans)
    recombined_non_whitespace = "".join("".join(span.text.split()) for span in spans)
    original_non_whitespace = "".join(content.split())
    assert recombined_non_whitespace == original_non_whitespace


def test_unicode_text_is_handled() -> None:
    content = "Café naïve résumé — 日本語も大丈夫。"
    spans = _split(content)
    assert len(spans) == 1
    assert spans[0].text == content
    _assert_offsets_match_content(content, spans)


def test_estimate_tokens_rounds_up() -> None:
    assert estimate_tokens("abcde", 4) == 2
    assert estimate_tokens("abcd", 4) == 1
    assert estimate_tokens("", 4) == 0


def test_ordinal_continuity_across_split_paragraph() -> None:
    content = "First para stays small.\n\n" + ("Word " * 40).strip()
    spans = _split(content, max_tokens=5, chars_per_token=4)
    ordinals = [span.ordinal for span in spans]
    assert ordinals == list(range(1, len(spans) + 1))
