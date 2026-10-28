"""Thematic content-tag vocabulary shown on the scenario page.

Distinct from ``Scenario.content_tag``, the single required age rating.
"""

CONTENT_TAG_VOCABULARY: tuple[str, ...] = (
    "noir-atmosphere",
    "moral-ambiguity",
    "investigation",
    "political-intrigue",
    "survival-pressure",
    "psychological-tension",
    "cozy-tone",
    "dark-humour",
    "romance",
    "found-family",
    "graphic-violence",
    "strong-language",
    "horror-themes",
    "heavy-themes",
)

MAX_CONTENT_TAGS = 5


def validate_content_tags(tags: list[str] | None) -> list[str] | None:
    """Reject unknown tags, duplicates and more than MAX_CONTENT_TAGS, keeping order."""
    if tags is None:
        return tags
    unknown = [tag for tag in tags if tag not in CONTENT_TAG_VOCABULARY]
    if unknown:
        raise ValueError(f"unknown content_tags: {unknown}")
    if len(set(tags)) != len(tags):
        raise ValueError("content_tags must not contain duplicates")
    if len(tags) > MAX_CONTENT_TAGS:
        raise ValueError(f"at most {MAX_CONTENT_TAGS} content_tags are allowed")
    return tags
