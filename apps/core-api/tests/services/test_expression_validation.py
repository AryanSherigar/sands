"""Unit tests for shared expression field-reference validation."""

import pytest
from app.services.expression_validation import validate_expression_field_references


def _error_factory(message: str) -> ValueError:
    return ValueError(message)


def test_rejects_list_form_connective() -> None:
    expression = {"AND": [{"field": "x"}]}

    with pytest.raises(ValueError, match="must be a nested expression"):
        validate_expression_field_references(expression, {"x": {}}, {}, _error_factory)


def test_rejects_string_form_connective() -> None:
    expression = {"AND": "not-an-expression"}

    with pytest.raises(ValueError, match="must be a nested expression"):
        validate_expression_field_references(expression, {"x": {}}, {}, _error_factory)


def test_accepts_valid_nested_dict_connective() -> None:
    expression = {"field": "x", "AND": {"field": "x"}}

    validate_expression_field_references(expression, {"x": {}}, {}, _error_factory)


def test_rejects_multiple_connectives_at_one_node() -> None:
    expression = {"AND": {"field": "x"}, "OR": {"field": "x"}}

    with pytest.raises(ValueError, match="at most one connective"):
        validate_expression_field_references(expression, {"x": {}}, {}, _error_factory)


def test_rejects_unknown_field_reference() -> None:
    expression = {"field": "unknown_field"}

    with pytest.raises(ValueError, match="does not reference"):
        validate_expression_field_references(expression, {"x": {}}, {}, _error_factory)


def test_none_expression_is_a_no_op() -> None:
    validate_expression_field_references(None, {"x": {}}, {}, _error_factory)
