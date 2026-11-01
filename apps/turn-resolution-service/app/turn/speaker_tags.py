"""Speaker attribution for narration text: which paragraphs are narrator
prose vs. a named NPC's spoken dialogue, used to route text to distinct TTS
voices (app/turn/steps/narration_audio_generator.py).

Gemini is prompted (ai_orchestrator._BASE_DM_SYSTEM_PROMPT rule 9) to tag
each paragraph with a leading [NARRATOR] or [NPC: <Name>] line. Tag
stripping/parsing here operates on whole paragraphs, not a live token
stream -- ai_orchestrator.py buffers newbie-mode narration into complete
"\\n\\n"-delimited paragraphs before this module ever sees the text, so
(unlike mood.py's extract_mood_tag) there's no partial-buffer/streaming
case to handle here.
"""

import re
from typing import NamedTuple

NARRATOR_SPEAKER = "narrator"
PARAGRAPH_SEPARATOR = "\n\n"

_TAG_BODY = r"\[\s*(?:(NARRATOR)|NPC\s*:\s*([^\]]+?)|(ESCALATION))\s*\]"
_TAG_PATTERN = re.compile(rf"^\s*{_TAG_BODY}\s*\r?\n?", re.IGNORECASE)
_ANY_TAG_PATTERN = re.compile(rf"[ \t]*{_TAG_BODY}([ \t]*\r?\n?)", re.IGNORECASE)
_ESCALATION_PATTERN = re.compile(r"\[\s*ESCALATION\s*\]", re.IGNORECASE)


class SpeakerSpan(NamedTuple):
    """One paragraph's speaker attribution: NARRATOR_SPEAKER, or an NPC's
    exact name as written in its [NPC: Name] tag."""

    speaker: str
    text: str


def strip_speaker_tags(text: str) -> str:
    """Remove every [NARRATOR]/[NPC: Name]/[ESCALATION] tag wherever it
    appears, paragraph by paragraph -- paragraph breaks are preserved and text
    on either side of a mid-line tag is joined with one space."""
    cleaned = [_strip_paragraph(paragraph) for paragraph in _split(text)]
    return PARAGRAPH_SEPARATOR.join(cleaned)


def has_escalation_marker(text: str) -> bool:
    return _ESCALATION_PATTERN.search(text) is not None


def parse_speaker_spans(text: str) -> list[SpeakerSpan]:
    """Split narration text into ordered (speaker, text) spans, starting a new
    span at every NPC/NARRATOR tag even mid-paragraph.

    Untagged or malformed text is always attributed to NARRATOR_SPEAKER --
    this must never crash or drop text, since it feeds best-effort audio
    generation that must not block a turn.
    """
    spans: list[SpeakerSpan] = []
    for paragraph in _split(text):
        spans.extend(_parse_paragraph(paragraph))
    return spans


def _strip_paragraph(paragraph: str) -> str:
    without_leading_tag = _TAG_PATTERN.sub("", paragraph)
    joined = _ANY_TAG_PATTERN.sub(_replace_inline_tag, without_leading_tag)
    return joined.rstrip(" \t")


def _replace_inline_tag(match: re.Match[str]) -> str:
    text_before = match.string[: match.start()]
    if not text_before or text_before.endswith("\n"):
        return ""
    if match.group(4).endswith("\n"):
        return "\n"
    return " "


def _parse_paragraph(paragraph: str) -> list[SpeakerSpan]:
    spans: list[SpeakerSpan] = []
    speaker = NARRATOR_SPEAKER
    cursor = 0
    for match in _ANY_TAG_PATTERN.finditer(paragraph):
        _append_span(spans, speaker, paragraph[cursor : match.start()])
        speaker = _speaker_after_tag(match, speaker)
        cursor = match.end()
    _append_span(spans, speaker, paragraph[cursor:])
    return spans


def _speaker_after_tag(match: re.Match[str], current_speaker: str) -> str:
    if match.group(1):
        return NARRATOR_SPEAKER
    if match.group(2):
        return match.group(2).strip()
    return current_speaker


def _append_span(spans: list[SpeakerSpan], speaker: str, text: str) -> None:
    stripped = text.strip()
    if not stripped:
        return
    if spans and spans[-1].speaker == speaker:
        spans[-1] = SpeakerSpan(speaker, f"{spans[-1].text} {stripped}")
        return
    spans.append(SpeakerSpan(speaker, stripped))


def _split(text: str) -> list[str]:
    return text.split(PARAGRAPH_SEPARATOR)


def buffer_narration_paragraphs(
    paragraph_buffer: str, new_text: str
) -> tuple[str, list[tuple[str, str]]]:
    """Accumulate streamed narration text until full paragraphs are
    available, releasing each complete paragraph as a ("narration_raw",
    tagged) plus ("narration", clean) event pair -- the mechanism that lets
    the live SSE stream stay free of [NARRATOR]/[NPC: Name] markup while the
    audio step still sees it. Returns the (possibly non-empty) remaining
    buffer plus any events now ready to yield."""
    combined = paragraph_buffer + new_text
    events: list[tuple[str, str]] = []
    while PARAGRAPH_SEPARATOR in combined:
        paragraph, combined = combined.split(PARAGRAPH_SEPARATOR, 1)
        events.extend(_emit_paragraph(paragraph + PARAGRAPH_SEPARATOR))
    return combined, events


def flush_narration_paragraph_buffer(paragraph_buffer: str) -> list[tuple[str, str]]:
    """Release any trailing paragraph left in the buffer once the stream ends."""
    if not paragraph_buffer.strip():
        return []
    return _emit_paragraph(paragraph_buffer)


def _emit_paragraph(raw_paragraph: str) -> list[tuple[str, str]]:
    clean = strip_speaker_tags(raw_paragraph)
    events: list[tuple[str, str]] = [("narration_raw", raw_paragraph)]
    if clean.strip():
        events.append(("narration", clean))
    return events
