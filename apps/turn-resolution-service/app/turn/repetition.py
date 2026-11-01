"""Finds the wording the narrator keeps reusing, so the prompt can ask it to move on.

Pure text analysis: no I/O and no model call. The same functions score a finished
run (scripts/repetition_report.py) and build the per-turn "already described" list.
"""

import re
from collections import Counter
from collections.abc import Sequence

from pydantic import BaseModel

MIN_PHRASE_WORDS = 2
MAX_PHRASE_WORDS = 3
MIN_CONTENT_WORDS = 2
NOVELTY_WINDOW = 3
CLOSING_LEAD_WORDS = 3
NOVELTY_NGRAM = 3
DEFAULT_PHRASE_LIMIT = 8
DEFAULT_MIN_TURNS = 2
SHARED_CONTENT_LIMIT = 0.5

_WORD = re.compile(r"[a-z0-9]+(?:['\-][a-z0-9]+)*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")
_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "his",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "no",
        "not",
        "of",
        "on",
        "or",
        "our",
        "she",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "they",
        "this",
        "to",
        "up",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "will",
        "with",
        "you",
        "your",
    ]
)


def _words(sentence: str) -> list[str]:
    return _WORD.findall(sentence.lower())


def _sentences(text: str) -> list[list[str]]:
    return [words for part in _SENTENCE_END.split(text) if (words := _words(part))]


def _is_phrase(words: Sequence[str]) -> bool:
    if words[0] in _STOPWORDS or words[-1] in _STOPWORDS:
        return False
    return sum(1 for word in words if word not in _STOPWORDS) >= MIN_CONTENT_WORDS


def _turn_phrases(text: str) -> set[str]:
    phrases: set[str] = set()
    for words in _sentences(text):
        for size in range(MIN_PHRASE_WORDS, MAX_PHRASE_WORDS + 1):
            for start in range(len(words) - size + 1):
                window = words[start : start + size]
                if _is_phrase(window):
                    phrases.add(" ".join(window))
    return phrases


def _content_words(phrase: str) -> set[str]:
    return {word for word in phrase.split() if word not in _STOPWORDS}


def _is_redundant(phrase: str, chosen: Sequence[str], seen_words: set[str]) -> bool:
    padded = f" {phrase} "
    if any(padded in f" {other} " or f" {other} " in padded for other in chosen):
        return True
    content = _content_words(phrase)
    return len(content & seen_words) / len(content) >= SHARED_CONTENT_LIMIT


def _ranked_phrases(turns: Sequence[str], min_turns: int) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for text in turns:
        counts.update(_turn_phrases(text))
    ranked = [(phrase, count) for phrase, count in counts.items() if count >= min_turns]
    ranked.sort(key=lambda item: (-item[1], len(item[0].split()), item[0]))
    return ranked


def top_phrases(
    turns: Sequence[str],
    limit: int = DEFAULT_PHRASE_LIMIT,
    min_turns: int = DEFAULT_MIN_TURNS,
) -> list[tuple[str, int]]:
    """Phrases with the number of turns that use them, overlapping variants collapsed."""
    chosen: list[tuple[str, int]] = []
    seen_words: set[str] = set()
    for phrase, count in _ranked_phrases(turns, min_turns):
        if len(chosen) >= limit:
            break
        if _is_redundant(phrase, [item[0] for item in chosen], seen_words):
            continue
        chosen.append((phrase, count))
        seen_words |= _content_words(phrase)
    return chosen


def repeated_phrases(
    turns: Sequence[str],
    limit: int = DEFAULT_PHRASE_LIMIT,
    min_turns: int = DEFAULT_MIN_TURNS,
) -> list[str]:
    return [phrase for phrase, _ in top_phrases(turns, limit, min_turns)]


def opener_word(text: str) -> str:
    match = re.match(r"\W*([\w'\-]+)", text)
    return match.group(1) if match else ""


def repeated_opener(turns: Sequence[str]) -> str | None:
    """The first word of the last two turns when it is the same, else None."""
    if len(turns) < 2:
        return None
    last, before = opener_word(turns[-1]), opener_word(turns[-2])
    return last if last and last.lower() == before.lower() else None


def _trigrams(text: str) -> set[tuple[str, ...]]:
    grams: set[tuple[str, ...]] = set()
    for words in _sentences(text):
        for start in range(len(words) - NOVELTY_NGRAM + 1):
            grams.add(tuple(words[start : start + NOVELTY_NGRAM]))
    return grams


def novelty_score(turns: Sequence[str], window: int = NOVELTY_WINDOW) -> float:
    """1.0 when no turn reuses a three-word run from the previous `window` turns,
    0.0 when every turn is a copy."""
    scores: list[float] = []
    for index in range(1, len(turns)):
        current = _trigrams(turns[index])
        if not current:
            continue
        earlier: set[tuple[str, ...]] = set()
        for previous in turns[max(0, index - window) : index]:
            earlier |= _trigrams(previous)
        scores.append(1 - len(current & earlier) / len(current))
    return sum(scores) / len(scores) if scores else 1.0


def _closing_lead(text: str) -> str:
    sentences = _SENTENCE_END.split(text.strip())
    last = next((part for part in reversed(sentences) if _words(part)), "")
    return " ".join(_words(last)[:CLOSING_LEAD_WORDS])


def closing_repeat_share(turns: Sequence[str], min_turns: int = 3) -> float:
    """Share of turns whose last sentence starts with words that at least
    `min_turns` turns also end on: the formula a narrator falls into."""
    leads = Counter(_closing_lead(text) for text in turns)
    repeated = sum(
        count for lead, count in leads.items() if lead and count >= min_turns
    )
    return repeated / len(turns) if turns else 0.0


class RepetitionReport(BaseModel):
    turns: int
    average_words: int
    novelty: float
    closing_share: float
    most_common_opener: str
    opener_share: float
    top_phrases: list[tuple[str, int]]


def summarize(turns: Sequence[str]) -> RepetitionReport:
    openers = Counter(opener_word(text).lower() for text in turns)
    opener, opener_count = openers.most_common(1)[0] if turns else ("", 0)
    words = [len(text.split()) for text in turns]
    return RepetitionReport(
        turns=len(turns),
        average_words=round(sum(words) / len(words)) if words else 0,
        novelty=round(novelty_score(turns), 3),
        closing_share=round(closing_repeat_share(turns), 2),
        most_common_opener=opener.capitalize(),
        opener_share=opener_count / len(turns) if turns else 0.0,
        top_phrases=top_phrases(turns, limit=DEFAULT_PHRASE_LIMIT, min_turns=3),
    )
