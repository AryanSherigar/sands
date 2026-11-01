"""The narrator's intent marker: a final `[INTENT: key=value, ...]` line.

Some scenarios have the narrator signal story milestones (a recruit agreeing, a
policy adopted) by ending its reply with one marker line instead of calling
`set_field`: a small narrator at low thinking effort follows a text format
every turn (it already writes the [MOOD: ...] and speaker tags) but rarely
calls a tool. The marker is stripped before the player or the audio step sees
it, then applied as ordinary `set_field` mutations so the usual validation,
enum checks and tool-call logging all apply.
"""

import re

import structlog
from google.genai import types

logger = structlog.get_logger()

EVENT_INTENT_PAIR_REJECTED = "intent_marker_pair_rejected"
PARAGRAPH_SEPARATOR = "\n\n"
TOOL_SET_FIELD = "set_field"

_MARKER_LINE = re.compile(
    r"^[ \t]*\[\s*INTENT\s*:([^\]\n]*)\][ \t]*(?:\r?\n|$)",
    re.IGNORECASE | re.MULTILINE,
)
_PAIR = re.compile(r"^\s*([a-z][a-z0-9_]*)\s*=\s*([a-z0-9_]+)\s*$", re.IGNORECASE)


def extract_intent_markers(text: str) -> tuple[str, list[tuple[str, str]]]:
    """The text without its marker lines, and the key/value pairs they held."""
    pairs: list[tuple[str, str]] = []
    for match in _MARKER_LINE.finditer(text):
        pairs.extend(_parse_pairs(match.group(1)))
    if not pairs and _MARKER_LINE.search(text) is None:
        return text, pairs
    cleaned = _MARKER_LINE.sub("", text)
    if not cleaned.strip():
        return "", pairs
    separator = PARAGRAPH_SEPARATOR if text.endswith(PARAGRAPH_SEPARATOR) else ""
    return cleaned.rstrip() + separator, pairs


def _parse_pairs(body: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for piece in body.split(","):
        match = _PAIR.match(piece)
        if match is None:
            logger.warning(EVENT_INTENT_PAIR_REJECTED, piece=piece.strip()[:40])
            continue
        pairs.append((match.group(1).lower(), match.group(2).lower()))
    return pairs


def pairs_to_function_calls(
    pairs: list[tuple[str, str]], group: str
) -> list[types.FunctionCall]:
    """One `set_field` call per pair, on `<group>.<key>`; later pairs for the
    same key win."""
    latest = dict(pairs)
    return [
        types.FunctionCall(
            name=TOOL_SET_FIELD, args={"path": f"{group}.{key}", "value": value}
        )
        for key, value in latest.items()
    ]
