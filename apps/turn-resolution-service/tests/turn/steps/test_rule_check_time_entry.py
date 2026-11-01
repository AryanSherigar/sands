"""The time_entry check: judging the typed time and resolving its outcome."""

import pytest
from app.exceptions.turn_exceptions import CheckReportInvalidError
from app.models.check_event import CheckReportInput
from app.turn import rule_check_payload
from app.turn.steps import rule_check_resolver

ISSUED_AT = 1_760_000_000_000
TOLD_MINUTE = 23 * 60 + 52
WALL_MINUTE = 23 * 60 + 40

DEFINITION = {
    "check_id": "def-visitor",
    "label": "Visitor log 1",
    "kind": "time_entry",
    "result_path": "visit.result",
    "params": {
        "prompt": "The visitor waits.",
        "told_minute_of_day": TOLD_MINUTE,
        "clock_path": "shift_minutes",
        "clock_start_minute_of_day": 23 * 60,
        "window_ms": 45_000,
        "timeout_result": "none",
        "told": {
            "result": "told",
            "mutations": [{"path": "obedience", "op": "increment", "value": 1}],
        },
        "wall": {
            "result": "wall",
            "mutations": [{"path": "sanity", "op": "decrement", "value": 10}],
        },
        "other": {
            "result": "other",
            "mutations": [{"path": "sanity", "op": "decrement", "value": 10}],
        },
        "reject": {
            "result": "rejected",
            "mutations": [{"path": "defiance", "op": "increment", "value": 1}],
        },
    },
    "narrator_instruction_template": "Outcome '{result}'.",
}
SNAPSHOT = {
    "enabled_tools": ["rule_checks"],
    "state_schema": {
        "sanity": {"type": "number", "min": 0, "max": 100},
        "obedience": {"type": "number", "min": 0, "max": 100},
        "defiance": {"type": "number", "min": 0, "max": 100},
        "visit": {
            "type": "object",
            "fields": {
                "result": {
                    "type": "enum",
                    "options": ["", "told", "wall", "other", "rejected", "none"],
                }
            },
        },
    },
    "entities": [],
    "rule_invariants": [],
    "rule_checks": [DEFINITION],
}


def _pending(**overrides) -> dict:
    base = {
        "check_id": "chk-1",
        "kind": "time_entry",
        "check_def_id": "def-visitor",
        "prompt": "The visitor waits.",
        "options": [
            {"id": "enter", "label": "Write it in the Log"},
            {"id": "reject", "label": "Reject the visitor"},
        ],
        "window_ms": 45_000,
        "issued_at": ISSUED_AT,
        "wall_minute_of_day": WALL_MINUTE,
        "resolved": None,
    }
    base.update(overrides)
    return base


def _state(pending: dict) -> dict:
    return {
        "sanity": 80,
        "obedience": 0,
        "defiance": 0,
        "visit": {"result": ""},
        "_pending_check": pending,
    }


def _report(**fields) -> CheckReportInput:
    return CheckReportInput(check_id="chk-1", **fields)


def _resolve(resolved: dict) -> rule_check_resolver.RuleCheckResolution:
    state = _state(_pending(resolved=resolved))
    return rule_check_resolver.resolve_report(state, SNAPSHOT)


def _entered(text: str) -> dict:
    return {
        "option_id": "enter",
        "is_timeout": False,
        "is_hidden": False,
        "entry_text": text,
    }


def test_the_told_time_scores_as_told() -> None:
    resolution = _resolve(_entered("11:52 pm"))

    assert resolution.state["visit"]["result"] == "told"
    assert resolution.state["obedience"] == 1
    assert resolution.state["sanity"] == 80
    assert resolution.instruction == "Outcome 'told'."


def test_the_wall_time_scores_as_wall() -> None:
    resolution = _resolve(_entered("11:40 PM"))

    assert resolution.state["visit"]["result"] == "wall"
    assert resolution.state["sanity"] == 70


@pytest.mark.parametrize("text", ["3:33 am", "eleven fifty-two", "11:5"])
def test_any_other_text_scores_as_other(text: str) -> None:
    resolution = _resolve(_entered(text))

    assert resolution.state["visit"]["result"] == "other"
    assert resolution.state["sanity"] == 70


def test_a_rejection_costs_only_defiance() -> None:
    resolved = {"option_id": "reject", "is_timeout": False, "is_hidden": False}

    resolution = _resolve(resolved)

    assert resolution.state["visit"]["result"] == "rejected"
    assert resolution.state["defiance"] == 1
    assert resolution.state["sanity"] == 80


def test_a_timeout_writes_the_timeout_result() -> None:
    resolution = _resolve({"option_id": None, "is_timeout": True, "is_hidden": False})

    assert resolution.state["visit"]["result"] == "none"
    assert resolution.state["sanity"] == 80


def test_a_told_time_equal_to_the_wall_time_still_scores_as_told() -> None:
    pending = _pending(wall_minute_of_day=TOLD_MINUTE, resolved=_entered("11:52 PM"))

    resolution = rule_check_resolver.resolve_report(_state(pending), SNAPSHOT)

    assert resolution.state["visit"]["result"] == "told"


def test_judging_stores_the_trimmed_entry_text() -> None:
    judgment = rule_check_resolver.judge_report(
        _pending(),
        _report(choice_id="enter", entry_text="  11:52 PM "),
        now_ms=ISSUED_AT + 1_000,
    )

    assert judgment.option_id == "enter"
    assert judgment.entry_text == "11:52 PM"


@pytest.mark.parametrize("entry_text", [None, "", "   "])
def test_entering_with_no_text_is_rejected(entry_text: str | None) -> None:
    with pytest.raises(CheckReportInvalidError):
        rule_check_resolver.judge_report(
            _pending(),
            _report(choice_id="enter", entry_text=entry_text),
            now_ms=ISSUED_AT + 1_000,
        )


def test_an_option_named_enter_on_another_kind_is_a_plain_choice() -> None:
    pending = _pending(
        kind="timed_choice",
        options=[{"id": "enter", "label": "Odd"}, {"id": "ignore", "label": "Ignore"}],
    )

    judgment = rule_check_resolver.judge_report(
        pending,
        _report(choice_id="enter", entry_text="1"),
        now_ms=ISSUED_AT + 1_000,
    )

    assert judgment.option_id == "enter"
    assert judgment.entry_text is None


@pytest.mark.parametrize("entry_text", ["x" * 17, "11:52\x00", "11:52\n"])
def test_oversized_or_unprintable_text_never_reaches_judging(entry_text: str) -> None:
    with pytest.raises(ValueError):
        _report(choice_id="enter", entry_text=entry_text)


def test_the_public_payload_shows_both_times_and_hides_the_outcomes() -> None:
    payload = rule_check_payload.build_event_payload(
        DEFINITION,
        check_id="chk-1",
        now_ms=ISSUED_AT,
        reopen_count=0,
        state={"shift_minutes": 40},
    )

    assert payload.told_label == "11:52 PM"
    assert payload.wall_label == "11:40 PM"
    assert payload.wall_minute_of_day == WALL_MINUTE
    assert [option.id for option in payload.options] == ["enter", "reject"]
    dumped = payload.model_dump_json()
    assert "told_minute_of_day" not in dumped
    assert "rejected" not in dumped
