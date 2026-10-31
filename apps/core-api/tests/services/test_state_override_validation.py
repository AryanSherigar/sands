"""Unit tests for app/services/state_override_validation.py."""

import pytest
from app.exceptions.playthrough_exceptions import InvalidStateOverrideError
from app.services.state_override_validation import (
    merge_state_overrides,
    validate_state_overrides,
)

CARD_ID = "11111111-1111-1111-1111-111111111111"
STATE_SCHEMA: dict[str, object] = {
    "lantern_oil": {"type": "number", "initial": 8, "min": 0, "max": 10},
    "has_key": {"type": "boolean", "initial": False},
    "time_of_day": {"type": "enum", "options": ["dawn", "day", "night"]},
    "mood": {"type": "string"},
    "player": {
        "type": "object",
        "fields": {"health": {"type": "number", "min": 0, "max": 100}},
    },
    "inventory": {"type": "list", "item_type": "string"},
}
ENTITIES: list[dict[str, object]] = [
    {"entity_id": CARD_ID, "attributes_schema": {"stamina": {"type": "number"}}}
]


def test_valid_overrides_are_returned_unchanged():
    overrides = {"lantern_oil": 2, "has_key": True, "time_of_day": "night"}

    assert validate_state_overrides(STATE_SCHEMA, ENTITIES, overrides) == overrides


def test_nested_value_is_addressed_by_dotted_path():
    result = validate_state_overrides(STATE_SCHEMA, ENTITIES, {"player.health": 40})

    assert result == {"player.health": 40}


def test_empty_overrides_are_valid():
    assert validate_state_overrides(STATE_SCHEMA, ENTITIES, {}) == {}


@pytest.mark.parametrize(
    "overrides",
    [
        {"nonsense": 1},
        {"setup": {"role": "mage"}},
        {"player.mana": 3},
        {"lantern_oil.extra": 1},
        {"": 1},
    ],
)
def test_unknown_keys_are_rejected(overrides: dict[str, object]):
    with pytest.raises(InvalidStateOverrideError) as raised:
        validate_state_overrides(STATE_SCHEMA, ENTITIES, overrides)

    assert raised.value.status_code == 422


def test_card_values_are_rejected_with_their_own_reason():
    with pytest.raises(InvalidStateOverrideError, match="card"):
        validate_state_overrides(STATE_SCHEMA, ENTITIES, {f"{CARD_ID}.stamina": 2})


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("lantern_oil", -1),
        ("lantern_oil", 11),
        ("player.health", 101),
        ("lantern_oil", "5"),
        ("lantern_oil", True),
        ("has_key", "yes"),
        ("has_key", 1),
        ("mood", 3),
        ("time_of_day", "dusk"),
    ],
)
def test_values_that_do_not_fit_the_field_are_rejected(key: str, value: object):
    with pytest.raises(InvalidStateOverrideError, match=key):
        validate_state_overrides(STATE_SCHEMA, ENTITIES, {key: value})


@pytest.mark.parametrize("key", ["player", "inventory"])
def test_groups_and_lists_cannot_be_preset(key: str):
    with pytest.raises(InvalidStateOverrideError):
        validate_state_overrides(STATE_SCHEMA, ENTITIES, {key: {}})


def test_one_bad_entry_rejects_the_whole_set():
    with pytest.raises(InvalidStateOverrideError):
        validate_state_overrides(
            STATE_SCHEMA, ENTITIES, {"lantern_oil": 3, "has_key": "maybe"}
        )


def test_merge_sets_top_level_and_nested_values_without_mutating_the_input():
    seeded = {"lantern_oil": 8, "player": {"health": 90, "mana": 5}, "setup": {}}

    merged = merge_state_overrides(
        seeded, {"lantern_oil": 2, "player.health": 10, "has_key": True}
    )

    assert merged == {
        "lantern_oil": 2,
        "player": {"health": 10, "mana": 5},
        "setup": {},
        "has_key": True,
    }
    assert seeded["lantern_oil"] == 8
    assert seeded["player"] == {"health": 90, "mana": 5}


def test_merge_creates_missing_parent_groups():
    assert merge_state_overrides({}, {"player.health": 4}) == {"player": {"health": 4}}
