import pytest
from app.services.narrator_rules import (
    MAX_NARRATION_OUTPUT_TOKENS,
    MIN_NARRATION_OUTPUT_TOKENS,
    intent_marker_group_from_rules,
    narration_limit_from_rules,
)


def test_a_missing_limit_keeps_the_provider_default() -> None:
    assert narration_limit_from_rules({}) is None


def test_a_valid_limit_is_returned() -> None:
    assert narration_limit_from_rules({"narration_max_output_tokens": 1500}) == 1500


@pytest.mark.parametrize(
    "value",
    [
        MIN_NARRATION_OUTPUT_TOKENS - 1,
        MAX_NARRATION_OUTPUT_TOKENS + 1,
        0,
        -5,
        "1500",
        1500.5,
        True,
        [1500],
    ],
)
def test_an_invalid_limit_is_ignored(value: object) -> None:
    assert narration_limit_from_rules({"narration_max_output_tokens": value}) is None


def test_the_bounds_are_accepted() -> None:
    low = {"narration_max_output_tokens": MIN_NARRATION_OUTPUT_TOKENS}
    high = {"narration_max_output_tokens": MAX_NARRATION_OUTPUT_TOKENS}
    assert narration_limit_from_rules(low) == MIN_NARRATION_OUTPUT_TOKENS
    assert narration_limit_from_rules(high) == MAX_NARRATION_OUTPUT_TOKENS


SCHEMA = {
    "intent": {"type": "object", "fields": {"recruit_target": {"type": "string"}}},
    "funds": {"type": "number"},
}


def test_a_group_in_the_schema_is_returned() -> None:
    rules = {"intent_marker_group": "intent"}

    assert intent_marker_group_from_rules(rules, SCHEMA) == "intent"


def test_no_group_setting_means_no_marker() -> None:
    assert intent_marker_group_from_rules({}, SCHEMA) is None


@pytest.mark.parametrize("value", ["funds", "missing", "Intent", 3, True, ["intent"]])
def test_a_name_that_is_not_a_schema_group_is_ignored(value: object) -> None:
    assert (
        intent_marker_group_from_rules({"intent_marker_group": value}, SCHEMA) is None
    )
