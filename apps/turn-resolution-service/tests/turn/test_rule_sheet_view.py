"""The clipboard view case table. apps/core-api/tests/services/
test_rule_sheet_view.py holds the identical table; keep them in step."""

import pytest
from app.turn.rule_sheet_view import rule_sheet_view


def _rule(key: str, number: int, **overrides) -> dict[str, object]:
    base = {
        "key": key,
        "number": number,
        "text": f"Rule {number} text",
        "corrupted_text": None,
        "initial_status": "intact",
        "source_style": "typed",
        "display_order": number,
    }
    base.update(overrides)
    return base


def test_unrevealed_rules_are_omitted() -> None:
    rules = [_rule("r1", 1), _rule("r2", 2)]

    view = rule_sheet_view(rules, {"r1": "intact", "r2": "unrevealed"})

    assert [item["key"] for item in view] == ["r1"]


def test_corrupted_rule_shows_its_corrupted_text() -> None:
    rules = [_rule("r1", 1, corrupted_text="Rule 1 text, scratched")]

    view = rule_sheet_view(rules, {"r1": "corrupted"})

    assert view[0]["text"] == "Rule 1 text, scratched"
    assert view[0]["status"] == "corrupted"


def test_corrupted_rule_without_corrupted_text_keeps_the_original() -> None:
    view = rule_sheet_view([_rule("r1", 1)], {"r1": "corrupted"})

    assert view[0]["text"] == "Rule 1 text"


def test_corrupted_text_is_ignored_for_other_statuses() -> None:
    rules = [_rule("r1", 1, corrupted_text="scratched")]

    view = rule_sheet_view(rules, {"r1": "violated"})

    assert view[0]["text"] == "Rule 1 text"


def test_order_follows_display_order_then_number() -> None:
    rules = [
        _rule("c", 3, display_order=0),
        _rule("a", 1, display_order=1),
        _rule("b", 2, display_order=1),
    ]

    view = rule_sheet_view(rules, {})

    assert [item["key"] for item in view] == ["c", "a", "b"]


def test_a_rule_with_no_recorded_status_uses_its_initial_status() -> None:
    rules = [_rule("r1", 1), _rule("r2", 2, initial_status="unrevealed")]

    view = rule_sheet_view(rules, {})

    assert [item["key"] for item in view] == ["r1"]
    assert view[0]["status"] == "intact"


@pytest.mark.parametrize("status", ["intact", "active_threat", "violated"])
def test_item_carries_only_the_public_fields(status: str) -> None:
    view = rule_sheet_view([_rule("r1", 1)], {"r1": status})

    assert set(view[0]) == {"key", "number", "text", "status", "source_style"}
    assert view[0]["status"] == status


def test_no_rules_gives_an_empty_view() -> None:
    assert rule_sheet_view([], {"r1": "intact"}) == []
