"""Unit tests for facts_block.py."""

from app.config import settings
from app.turn import facts_block

LOBBY_ID = "loc-lobby"
EVA_ID = "ent-eva"


def _snapshot() -> dict[str, object]:
    return {
        "entities": [
            {"entity_id": LOBBY_ID, "canonical_name": "Elevator lobby"},
            {
                "entity_id": EVA_ID,
                "canonical_name": "Eva Venn",
                "attributes_schema": {
                    "mood": {"type": "string", "is_narrator_visible": True},
                    "secret": {"type": "string"},
                },
            },
        ],
        "state_schema": {
            "shift_minutes": {
                "type": "number",
                "display": {"kind": "clock", "start": "23:00", "format": "12h"},
            },
            "cabin": {
                "type": "object",
                "hidden": True,
                "fields": {
                    "lamp": {"type": "string", "narrator_fact": "Cabin 14 lamp"}
                },
            },
        },
        "sheet_rules": [
            {
                "key": "r1",
                "number": 1,
                "text": "Log visitors.",
                "initial_status": "intact",
            },
            {
                "key": "r5",
                "number": 5,
                "text": "Hidden.",
                "initial_status": "unrevealed",
            },
        ],
        "scenario_conditions": [
            {
                "condition_id": "n1",
                "condition_expression": {
                    "field": "shift_minutes",
                    "op": ">=",
                    "value": 0,
                },
                "narrator_instruction": "Never describe the inside of Cabin 14.",
                "metadata": {"placement": "facts"},
            },
            {
                "condition_id": "n2",
                "condition_expression": {
                    "field": "flags.cabin_entered",
                    "op": "==",
                    "value": False,
                },
                "narrator_instruction": "Never describe the lock.",
                "metadata": {"placement": "facts"},
            },
            {
                "condition_id": "d1",
                "condition_expression": {
                    "field": "shift_minutes",
                    "op": ">=",
                    "value": 0,
                },
                "narrator_instruction": "A plain directive.",
            },
        ],
    }


def _state(**overrides: object) -> dict[str, object]:
    state: dict[str, object] = {
        "current_location_id": LOBBY_ID,
        "shift_minutes": 52,
        "cabin": {"lamp": "on"},
        "rule_status": {"r1": "intact", "r5": "unrevealed"},
        "flags": {"cabin_entered": False},
        "entities": {EVA_ID: {"mood": "wary", "secret": "knows"}},
    }
    state.update(overrides)
    return state


def test_block_lists_each_fact_in_a_fixed_order() -> None:
    block = facts_block.build_facts_block(_snapshot(), _state())

    assert block.splitlines() == [
        facts_block.HEADING,
        "Location: Elevator lobby",
        "Clock: 11:52 PM",
        "Rule statuses: Rule 1 intact",
        "Cabin 14 lamp: on",
        "Eva Venn mood: wary",
        "Never describe the inside of Cabin 14.",
        "Never describe the lock.",
    ]


def test_never_describe_item_is_dropped_once_its_condition_stops_holding() -> None:
    state = _state(flags={"cabin_entered": True})

    block = facts_block.build_facts_block(_snapshot(), state)

    assert "Never describe the lock." not in block
    assert "Never describe the inside of Cabin 14." in block


def test_unflagged_attributes_and_plain_directives_stay_out() -> None:
    block = facts_block.build_facts_block(_snapshot(), _state())

    assert "secret" not in block
    assert "A plain directive." not in block


def test_clock_wraps_past_midnight() -> None:
    block = facts_block.build_facts_block(_snapshot(), _state(shift_minutes=75))

    assert "Clock: 12:15 AM" in block


def test_scenario_without_facts_has_no_block() -> None:
    assert facts_block.build_facts_block({"entities": []}, {}) == ""


def test_budget_drops_attributes_first_and_never_the_anchor(monkeypatch) -> None:
    monkeypatch.setattr(settings, "facts_block_tokens", 1)

    block = facts_block.build_facts_block(_snapshot(), _state())

    assert block.splitlines() == [
        facts_block.HEADING,
        "Location: Elevator lobby",
        "Clock: 11:52 PM",
    ]


def test_budget_keeps_never_describe_after_other_lines_are_gone(monkeypatch) -> None:
    full = facts_block.build_facts_block(_snapshot(), _state())
    anchor_and_never = sum(
        facts_block._estimate_tokens(line)
        for line in full.splitlines()
        if line.startswith(("Location", "Clock", "Never"))
    )
    monkeypatch.setattr(settings, "facts_block_tokens", anchor_and_never)

    block = facts_block.build_facts_block(_snapshot(), _state())

    assert "Never describe the lock." in block
    assert "Rule statuses" not in block
    assert "Cabin 14 lamp" not in block


def test_fact_conditions_are_recognised_by_placement() -> None:
    conditions = _snapshot()["scenario_conditions"]

    assert [facts_block.is_fact_condition(c) for c in conditions] == [True, True, False]
