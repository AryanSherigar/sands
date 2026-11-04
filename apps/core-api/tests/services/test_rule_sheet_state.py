import pytest
from app.exceptions.base import BaseAppException
from app.exceptions.sheet_rule_exceptions import ReservedStateKeyError
from app.services.expression_validation import (
    validate_expression_field_references,
    validate_mutation_paths,
)
from app.services.rule_sheet_state import (
    build_schema_extension,
    validate_reserved_roots,
    with_rule_sheet_roots,
)

TOOLS_ON = ["rule_sheet"]


class _Rejected(BaseAppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=422)


def _rule(key: str, **overrides) -> dict[str, object]:
    base = {"key": key, "initial_status": "intact", "is_ai_flaggable": False}
    base.update(overrides)
    return base


@pytest.mark.parametrize("root", ["rule_status", "rule_flags"])
def test_creator_declared_roots_are_reserved_while_the_tool_is_on(root: str) -> None:
    with pytest.raises(ReservedStateKeyError):
        validate_reserved_roots({root: {"type": "object"}}, TOOLS_ON)


def test_the_roots_are_free_while_the_tool_is_off() -> None:
    validate_reserved_roots({"rule_status": {"type": "object"}}, [])


def test_extension_declares_a_hidden_status_enum_per_rule() -> None:
    extension = build_schema_extension(
        [_rule("r1"), _rule("r2", initial_status="unrevealed")]
    )

    status = extension["rule_status"]
    assert status["hidden"] is True
    assert status["fields"]["r2"]["initial"] == "unrevealed"
    assert status["fields"]["r1"]["options"] == [
        "unrevealed",
        "intact",
        "active_threat",
        "violated",
        "corrupted",
    ]
    assert "rule_flags" not in extension


def test_extension_declares_a_hidden_flag_only_for_flaggable_rules() -> None:
    extension = build_schema_extension([_rule("r1"), _rule("r2", is_ai_flaggable=True)])

    flags = extension["rule_flags"]
    assert flags["hidden"] is True
    assert list(flags["fields"]) == ["r2"]
    assert flags["fields"]["r2"] == {"type": "boolean", "initial": False}


def test_no_rules_means_no_extension() -> None:
    assert build_schema_extension([]) == {}


def test_validation_schema_is_untouched_while_the_tool_is_off() -> None:
    schema = {"clock": {"type": "number"}}

    assert with_rule_sheet_roots(schema, []) is schema


def test_expressions_may_reference_rule_status_keys_when_the_tool_is_on() -> None:
    schema = with_rule_sheet_roots({}, TOOLS_ON)

    validate_expression_field_references(
        {"field": "rule_status.r2", "op": "==", "value": "violated"},
        schema,
        {},
        _Rejected,
    )


def test_expressions_may_not_reference_rule_status_when_the_tool_is_off() -> None:
    with pytest.raises(_Rejected):
        validate_expression_field_references(
            {"field": "rule_status.r2", "op": "==", "value": "violated"},
            with_rule_sheet_roots({}, []),
            {},
            _Rejected,
        )


def test_mutations_may_target_status_and_flag_leaves_when_the_tool_is_on() -> None:
    schema = with_rule_sheet_roots({}, TOOLS_ON)

    validate_mutation_paths(["rule_status.r2", "rule_flags.r2"], schema, {}, _Rejected)


@pytest.mark.parametrize(
    "path", ["rule_status.R2", "rule_status.r2.extra", "rule_status.bad key"]
)
def test_malformed_status_paths_are_still_rejected(path: str) -> None:
    with pytest.raises(_Rejected):
        validate_mutation_paths(
            [path], with_rule_sheet_roots({}, TOOLS_ON), {}, _Rejected
        )
