"""Maps accepted-mutation dotted paths and values into DB-comparable literals. Pure, no I/O."""

import json
from uuid import UUID

from app.models.ingest import AcceptedDeltaItem

_ENTITY_ATTRIBUTE_PATH_SEGMENT_COUNT = 2


def parse_entity_attribute_path(path: str) -> tuple[UUID, str] | None:
    segments = path.split(".")
    if len(segments) != _ENTITY_ATTRIBUTE_PATH_SEGMENT_COUNT:
        return None
    entity_segment, attribute_segment = segments
    if not attribute_segment:
        return None
    try:
        entity_id = UUID(entity_segment)
    except ValueError:
        return None
    return entity_id, attribute_segment


def canonical_value(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


def is_noop_value(current_literals: list[str | None], new_literal: str) -> bool:
    if not current_literals:
        return False
    return all(literal == new_literal for literal in current_literals)


def describe_roll(item: AcceptedDeltaItem) -> str | None:
    """One line for a resolved check, or None when the detail is unusable."""
    check_type = item.detail.get("check_type")
    difficulty_class = item.detail.get("difficulty_class")
    is_success = item.detail.get("is_success")
    if not isinstance(check_type, str) or not check_type:
        return None
    if not isinstance(item.after, int) or not isinstance(difficulty_class, int):
        return None
    if not isinstance(is_success, bool):
        return None
    outcome = "success" if is_success else "failure"
    return f"{check_type}: rolled {item.after} against DC {difficulty_class}, {outcome}"
