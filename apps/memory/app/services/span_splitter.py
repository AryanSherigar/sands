"""Splits raw content into token-budgeted SpanDraft chunks. Pure, no I/O."""

import math
import re

from app.models.evidence import SpanDraft

_CLOSING_PUNCTUATION = "\"'" + chr(0x2019) + chr(0x201D) + ")]"
_SENTENCE_TERMINATOR_PATTERN = re.compile(
    r"[.!?]+[" + re.escape(_CLOSING_PUNCTUATION) + r"]*(?=\s)"
)
_WORD_PATTERN = re.compile(r"\S+")

Offset = tuple[int, int]


def estimate_tokens(text: str, chars_per_token: int) -> int:
    if not text:
        return 0
    return math.ceil(len(text) / chars_per_token)


def split_spans(
    content: str, label_prefix: str, max_tokens: int, chars_per_token: int
) -> list[SpanDraft]:
    if not content.strip():
        return []
    drafts: list[SpanDraft] = []
    ordinal = 1
    for paragraph_start, paragraph_end in _paragraph_offsets(content):
        chunks = _split_paragraph(
            content, paragraph_start, paragraph_end, max_tokens, chars_per_token
        )
        for chunk_start, chunk_end in chunks:
            drafts.append(
                _build_span_draft(
                    content,
                    chunk_start,
                    chunk_end,
                    ordinal,
                    label_prefix,
                    chars_per_token,
                )
            )
            ordinal += 1
    return drafts


def _build_span_draft(
    content: str,
    start: int,
    end: int,
    ordinal: int,
    label_prefix: str,
    chars_per_token: int,
) -> SpanDraft:
    text = content[start:end]
    return SpanDraft(
        ordinal=ordinal,
        start_offset=start,
        end_offset=end,
        text=text,
        token_count=estimate_tokens(text, chars_per_token),
        label=f"{label_prefix}.{ordinal}",
    )


def _paragraph_offsets(content: str) -> list[Offset]:
    return [_trim_run(content, start, end) for start, end in _paragraph_runs(content)]


def _paragraph_runs(content: str) -> list[Offset]:
    runs: list[Offset] = []
    current: Offset | None = None
    offset = 0
    for line in content.splitlines(keepends=True):
        line_end = offset + len(line)
        current = _extend_run(line, offset, line_end, current, runs)
        offset = line_end
    if current is not None:
        runs.append(current)
    return runs


def _extend_run(
    line: str,
    line_start: int,
    line_end: int,
    current: Offset | None,
    runs: list[Offset],
) -> Offset | None:
    if line.strip() == "":
        if current is not None:
            runs.append(current)
        return None
    if current is None:
        return (line_start, line_end)
    return (current[0], line_end)


def _trim_run(content: str, run_start: int, run_end: int) -> Offset:
    raw = content[run_start:run_end]
    lstripped = raw.lstrip()
    leading_len = len(raw) - len(lstripped)
    stripped = lstripped.rstrip()
    start = run_start + leading_len
    return start, start + len(stripped)


def _split_paragraph(
    content: str, start: int, end: int, max_tokens: int, chars_per_token: int
) -> list[Offset]:
    if estimate_tokens(content[start:end], chars_per_token) <= max_tokens:
        return [(start, end)]
    sentences = _find_sentence_offsets(content, start, end)
    return _pack_sentences(content, sentences, max_tokens, chars_per_token)


def _find_sentence_offsets(content: str, start: int, end: int) -> list[Offset]:
    text = content[start:end]
    offsets: list[Offset] = []
    cursor = 0
    for match in _SENTENCE_TERMINATOR_PATTERN.finditer(text):
        sentence_end = match.end()
        offsets.append((start + cursor, start + sentence_end))
        cursor = _skip_whitespace(text, sentence_end)
    if cursor < len(text):
        offsets.append((start + cursor, end))
    return offsets


def _skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _pack_sentences(
    content: str, sentences: list[Offset], max_tokens: int, chars_per_token: int
) -> list[Offset]:
    chunks: list[Offset] = []
    pending: Offset | None = None
    for sentence in sentences:
        pending, produced = _absorb_sentence(
            content, pending, sentence, max_tokens, chars_per_token
        )
        chunks.extend(produced)
    if pending is not None:
        chunks.append(pending)
    return chunks


def _absorb_sentence(
    content: str,
    pending: Offset | None,
    sentence: Offset,
    max_tokens: int,
    chars_per_token: int,
) -> tuple[Offset | None, list[Offset]]:
    sentence_tokens = estimate_tokens(
        content[sentence[0] : sentence[1]], chars_per_token
    )
    if sentence_tokens > max_tokens:
        produced = [pending] if pending is not None else []
        produced.extend(
            _split_sentence_by_words(
                content, sentence[0], sentence[1], max_tokens, chars_per_token
            )
        )
        return None, produced
    if pending is None:
        return sentence, []
    merged_tokens = estimate_tokens(content[pending[0] : sentence[1]], chars_per_token)
    if merged_tokens <= max_tokens:
        return (pending[0], sentence[1]), []
    return sentence, [pending]


def _find_word_offsets(content: str, start: int, end: int) -> list[Offset]:
    text = content[start:end]
    return [
        (start + match.start(), start + match.end())
        for match in _WORD_PATTERN.finditer(text)
    ]


def _split_sentence_by_words(
    content: str, start: int, end: int, max_tokens: int, chars_per_token: int
) -> list[Offset]:
    words = _find_word_offsets(content, start, end)
    chunks: list[Offset] = []
    pending: Offset | None = None
    for word in words:
        pending, produced = _absorb_word(
            content, pending, word, max_tokens, chars_per_token
        )
        chunks.extend(produced)
    if pending is not None:
        chunks.append(pending)
    return chunks


def _absorb_word(
    content: str,
    pending: Offset | None,
    word: Offset,
    max_tokens: int,
    chars_per_token: int,
) -> tuple[Offset | None, list[Offset]]:
    word_tokens = estimate_tokens(content[word[0] : word[1]], chars_per_token)
    if word_tokens > max_tokens:
        produced = [pending] if pending is not None else []
        produced.extend(
            _split_word_by_chars(content, word[0], word[1], max_tokens, chars_per_token)
        )
        return None, produced
    if pending is None:
        return word, []
    merged_tokens = estimate_tokens(content[pending[0] : word[1]], chars_per_token)
    if merged_tokens <= max_tokens:
        return (pending[0], word[1]), []
    return word, [pending]


def _split_word_by_chars(
    content: str, start: int, end: int, max_tokens: int, chars_per_token: int
) -> list[Offset]:
    max_chars = max(1, max_tokens * chars_per_token)
    chunks: list[Offset] = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + max_chars, end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end
    return chunks
