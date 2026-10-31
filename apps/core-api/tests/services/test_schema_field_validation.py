import pytest
from app.exceptions.schema_field_exceptions import SchemaFieldValidationError
from app.exceptions.tool_exceptions import ToolNotEnabledError
from app.services.schema_field_validation import (
    strip_initial_random,
    validate_schema_fields,
)

TOOLS_ON = ["rule_checks"]


def _rule(**overrides) -> dict[str, object]:
    base = {"type": "enum", "options": ["r4", "r6"], "initial_random": ["r4", "r6"]}
    base.update(overrides)
    return base


@pytest.mark.parametrize("value", ["yes", 1, None, ["x"]])
def test_hidden_must_be_a_boolean(value) -> None:
    schema = {"secret": {"type": "number", "hidden": value}}

    with pytest.raises(SchemaFieldValidationError):
        validate_schema_fields(schema, [])


def test_hidden_boolean_values_are_accepted_on_nested_fields() -> None:
    schema = {
        "group": {
            "type": "object",
            "fields": {"inner": {"type": "number", "hidden": True}},
        },
        "other": {"type": "number", "hidden": False},
    }

    validate_schema_fields(schema, [])


def test_valid_initial_random_is_accepted_with_the_tool_on() -> None:
    validate_schema_fields({"rule": _rule()}, TOOLS_ON)


@pytest.mark.parametrize(
    "field",
    [
        _rule(initial_random=[]),
        _rule(initial_random="r4"),
        _rule(initial_random=["r9"]),
        _rule(initial_random=["r4", "r4"]),
        _rule(initial_random=[4]),
        {"type": "number", "initial_random": ["r4"]},
    ],
)
def test_malformed_initial_random_is_rejected_with_the_tool_on(field) -> None:
    with pytest.raises(SchemaFieldValidationError):
        validate_schema_fields({"rule": field}, TOOLS_ON)


def test_new_initial_random_is_refused_with_the_tool_off() -> None:
    with pytest.raises(ToolNotEnabledError):
        validate_schema_fields({"rule": _rule()}, [], previous_schema={})


def test_changed_initial_random_is_refused_with_the_tool_off() -> None:
    previous = {"rule": _rule(initial_random=["r4"])}

    with pytest.raises(ToolNotEnabledError):
        validate_schema_fields({"rule": _rule()}, [], previous_schema=previous)


def test_leftover_initial_random_does_not_block_unrelated_edits() -> None:
    previous = {"rule": _rule()}
    edited = {"rule": _rule(), "note": {"type": "string"}}

    validate_schema_fields(edited, [], previous_schema=previous)


def test_strip_initial_random_removes_it_at_every_depth_without_mutating() -> None:
    schema = {
        "rule": _rule(),
        "group": {"type": "object", "fields": {"door": _rule()}},
    }

    stripped = strip_initial_random(schema)

    assert "initial_random" not in stripped["rule"]
    assert "initial_random" not in stripped["group"]["fields"]["door"]
    assert stripped["rule"]["options"] == ["r4", "r6"]
    assert "initial_random" in schema["rule"]
