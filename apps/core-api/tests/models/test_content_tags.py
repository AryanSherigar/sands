"""Unit tests for the thematic content-tag vocabulary and validator."""

import pytest
from app.models.content_tags import (
    CONTENT_TAG_VOCABULARY,
    MAX_CONTENT_TAGS,
    validate_content_tags,
)


def test_accepts_known_tags_and_keeps_the_chosen_order():
    tags = ["moral-ambiguity", "noir-atmosphere", "romance"]

    assert validate_content_tags(tags) == tags


def test_accepts_none_and_empty():
    assert validate_content_tags(None) is None
    assert validate_content_tags([]) == []


def test_rejects_unknown_tags():
    with pytest.raises(ValueError, match="unknown content_tags"):
        validate_content_tags(["noir-atmosphere", "not-a-tag"])


def test_rejects_duplicates():
    with pytest.raises(ValueError, match="duplicates"):
        validate_content_tags(["romance", "romance"])


def test_allows_exactly_the_maximum_and_rejects_one_more():
    at_limit = list(CONTENT_TAG_VOCABULARY[:MAX_CONTENT_TAGS])

    assert validate_content_tags(at_limit) == at_limit
    with pytest.raises(ValueError, match="at most"):
        validate_content_tags(list(CONTENT_TAG_VOCABULARY[: MAX_CONTENT_TAGS + 1]))
