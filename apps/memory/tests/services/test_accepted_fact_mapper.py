"""Tests for app.services.accepted_fact_mapper, a pure module with no I/O."""

from uuid import uuid4

from app.models.ingest import AcceptedDeltaItem
from app.services.accepted_fact_mapper import (
    canonical_value,
    describe_roll,
    is_noop_value,
    parse_entity_attribute_path,
)


def test_valid_entity_attribute_path_parses() -> None:
    entity_id = uuid4()
    path = f"{entity_id}.hp"
    assert parse_entity_attribute_path(path) == (entity_id, "hp")


def test_top_level_path_returns_none() -> None:
    assert parse_entity_attribute_path("player.hp") is None
    assert parse_entity_attribute_path("flags.x") is None


def test_deeper_path_returns_none() -> None:
    entity_id = uuid4()
    assert parse_entity_attribute_path(f"{entity_id}.stats.hp") is None


def test_bad_uuid_segment_returns_none() -> None:
    assert parse_entity_attribute_path("not-a-uuid.hp") is None


def test_empty_attribute_segment_returns_none() -> None:
    entity_id = uuid4()
    assert parse_entity_attribute_path(f"{entity_id}.") is None


def test_single_segment_returns_none() -> None:
    assert parse_entity_attribute_path("hp") is None


def test_canonical_value_sorts_keys() -> None:
    assert canonical_value({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_canonical_value_nested_dict_ordering_is_stable() -> None:
    value = {"z": {"y": 1, "x": {"c": 3, "b": 2}}, "a": [3, 1, 2]}
    first = canonical_value(value)
    second = canonical_value(value)
    assert first == second
    assert first == '{"a":[3,1,2],"z":{"x":{"b":2,"c":3},"y":1}}'


def test_canonical_value_none_becomes_json_null() -> None:
    assert canonical_value(None) == "null"


def test_canonical_value_uses_compact_separators() -> None:
    assert canonical_value([1, 2, 3]) == "[1,2,3]"


def test_is_noop_value_true_when_all_match() -> None:
    assert is_noop_value(["5", "5", "5"], "5") is True


def test_is_noop_value_false_when_any_differ() -> None:
    assert is_noop_value(["5", "6"], "5") is False


def test_is_noop_value_false_when_empty() -> None:
    assert is_noop_value([], "5") is False


def test_is_noop_value_handles_none_literal() -> None:
    assert is_noop_value([None, None], "null") is False
    assert is_noop_value(["null", "null"], "null") is True


def _roll_item(after: object, **detail: object) -> AcceptedDeltaItem:
    return AcceptedDeltaItem(kind="roll", key="check-1", after=after, detail=detail)


def test_describe_roll_renders_check_roll_difficulty_and_outcome() -> None:
    item = _roll_item(9, check_type="strength", difficulty_class=15, is_success=False)

    assert describe_roll(item) == "strength: rolled 9 against DC 15, failure"


def test_describe_roll_rejects_missing_or_mistyped_detail() -> None:
    assert describe_roll(_roll_item(9)) is None
    assert (
        describe_roll(
            _roll_item("9", check_type="strength", difficulty_class=15, is_success=True)
        )
        is None
    )
    assert (
        describe_roll(
            _roll_item(9, check_type="", difficulty_class=15, is_success=True)
        )
        is None
    )
