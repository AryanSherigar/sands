"""Matches free text against a scope's known aliases. Pure, no I/O."""

import re
from functools import cache
from uuid import UUID

_WHITESPACE_PATTERN = re.compile(r"\s+")
_UNAMBIGUOUS_MATCH_COUNT = 1


def normalize_text_for_matching(text: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", text.casefold()).strip()


def build_alias_index(aliases: list[tuple[str, UUID]]) -> dict[str, set[UUID]]:
    index: dict[str, set[UUID]] = {}
    for alias_normalized, entity_id in aliases:
        index.setdefault(alias_normalized, set()).add(entity_id)
    return index


def tag_entities(text: str, alias_index: dict[str, set[UUID]]) -> list[UUID]:
    if not alias_index:
        return []
    normalized_text = normalize_text_for_matching(text)
    matched_ids: set[UUID] = set()
    for alias, entity_ids in alias_index.items():
        if len(entity_ids) != _UNAMBIGUOUS_MATCH_COUNT:
            continue
        if not _could_match(alias, normalized_text):
            continue
        if _alias_pattern(alias).search(normalized_text):
            matched_ids.update(entity_ids)
    return sorted(matched_ids, key=str)


def _could_match(alias: str, normalized_text: str) -> bool:
    first_word = alias.split(" ", 1)[0]
    return first_word in normalized_text


@cache
def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)")
