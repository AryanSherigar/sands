"""Tests for app.services.entity_tagger, a pure module with no I/O."""

from uuid import uuid4

from app.repositories.entity_repo import normalize_alias
from app.services.entity_tagger import build_alias_index, tag_entities


def test_unique_alias_is_tagged() -> None:
    entity_id = uuid4()
    index = build_alias_index([(normalize_alias("Elowen"), entity_id)])
    assert tag_entities("Elowen walked into the tavern.", index) == [entity_id]


def test_ambiguous_alias_tags_nothing() -> None:
    first_id = uuid4()
    second_id = uuid4()
    index = build_alias_index(
        [
            (normalize_alias("the guard"), first_id),
            (normalize_alias("the guard"), second_id),
        ]
    )
    assert tag_entities("The guard nodded.", index) == []


def test_whole_word_match_excludes_substring() -> None:
    entity_id = uuid4()
    index = build_alias_index([(normalize_alias("Ann"), entity_id)])
    assert tag_entities("The Annual meeting starts now.", index) == []


def test_whole_word_match_allows_possessive() -> None:
    entity_id = uuid4()
    index = build_alias_index([(normalize_alias("Ann"), entity_id)])
    assert tag_entities("Ann's sword gleamed.", index) == [entity_id]


def test_multi_word_alias_matches_irregular_whitespace_and_case() -> None:
    entity_id = uuid4()
    index = build_alias_index([(normalize_alias("Old Stone Bridge"), entity_id)])
    text = "They crossed the   OLD   STONE\nBRIDGE at dawn."
    assert tag_entities(text, index) == [entity_id]


def test_punctuation_adjacent_alias_matches() -> None:
    entity_id = uuid4()
    index = build_alias_index([(normalize_alias("Ann"), entity_id)])
    assert tag_entities("A note about (Ann) was left.", index) == [entity_id]
    assert tag_entities("A note about Ann, was left.", index) == [entity_id]


def test_empty_index_tags_nothing() -> None:
    assert tag_entities("Anything at all.", {}) == []


def test_deduped_and_sorted_by_str() -> None:
    first_id = uuid4()
    second_id = uuid4()
    index = build_alias_index(
        [
            (normalize_alias("Elowen"), first_id),
            (normalize_alias("The Watcher"), second_id),
        ]
    )
    text = "Elowen spoke to Elowen again, then to the Watcher."
    result = tag_entities(text, index)
    assert result == sorted({first_id, second_id}, key=str)


def test_build_alias_index_groups_ids_per_alias() -> None:
    first_id = uuid4()
    second_id = uuid4()
    index = build_alias_index(
        [
            ("the guard", first_id),
            ("the guard", second_id),
            ("elowen", first_id),
        ]
    )
    assert index == {"the guard": {first_id, second_id}, "elowen": {first_id}}
