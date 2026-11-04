import pytest
from app.exceptions.tool_exceptions import UnknownToolError
from app.tools.registry import (
    TOOLS,
    close_over_requires,
    dependents_of,
    validate_known,
)


def test_registry_declares_the_five_tools_in_stable_order() -> None:
    assert list(TOOLS) == [
        "rule_checks",
        "rule_sheet",
        "status_hud",
        "atmosphere",
        "composure",
    ]


def test_atmosphere_requires_status_hud() -> None:
    assert TOOLS["atmosphere"].requires == ("status_hud",)


def test_close_over_requires_adds_requirement_and_reports_it() -> None:
    closed, auto_added = close_over_requires(["atmosphere"])

    assert closed == ["status_hud", "atmosphere"]
    assert auto_added == ["status_hud"]


def test_close_over_requires_returns_registry_order_and_drops_duplicates() -> None:
    closed, auto_added = close_over_requires(["composure", "rule_checks", "composure"])

    assert closed == ["rule_checks", "composure"]
    assert auto_added == []


def test_close_over_requires_does_not_report_requirement_already_listed() -> None:
    closed, auto_added = close_over_requires(["atmosphere", "status_hud"])

    assert closed == ["status_hud", "atmosphere"]
    assert auto_added == []


def test_validate_known_rejects_unknown_key() -> None:
    with pytest.raises(UnknownToolError) as raised:
        validate_known(["rule_checks", "teleporter"])

    assert "teleporter" in raised.value.message


def test_validate_known_accepts_empty_list() -> None:
    validate_known([])


def test_dependents_of_lists_enabled_tools_that_require_the_key() -> None:
    assert dependents_of("status_hud", ["status_hud", "atmosphere"]) == ["atmosphere"]


def test_dependents_of_is_empty_when_dependent_is_not_enabled() -> None:
    assert dependents_of("status_hud", ["status_hud", "composure"]) == []
